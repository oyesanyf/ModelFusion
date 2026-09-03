use std::process::Stdio;
use std::sync::Arc;
use async_trait::async_trait;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader, Lines};
use tokio::process::{Child, Command};
use tokio::sync::{mpsc, Mutex};
use tracing::{error, warn};

use super::{Transport, TransportError};
use crate::types::JsonRpcMessage;

/// Stdio transport managing an external child process with isolated stdin/stdout and stderr log streaming.
pub struct StdioProcessTransport {
    child: Arc<Mutex<Option<Child>>>,
    stdin_tx: mpsc::Sender<JsonRpcMessage>,
    stdout_rx: Mutex<mpsc::Receiver<JsonRpcMessage>>,
    stderr_rx: Mutex<mpsc::Receiver<String>>,
}

impl StdioProcessTransport {
    /// Spawns a child process and attaches line-delimited JSON-RPC framing to stdin/stdout and isolated logging to stderr.
    pub fn spawn(
        mut command: Command,
        buffer_size: usize,
    ) -> Result<Self, TransportError> {
        command.stdin(Stdio::piped());
        command.stdout(Stdio::piped());
        command.stderr(Stdio::piped());

        let mut child = command.spawn().map_err(|e| TransportError::Io(e.to_string()))?;

        let stdin = child.stdin.take().expect("child stdin configured");
        let stdout = child.stdout.take().expect("child stdout configured");
        let stderr = child.stderr.take().expect("child stderr configured");

        let (stdin_tx, mut stdin_rx) = mpsc::channel::<JsonRpcMessage>(buffer_size);
        let (stdout_tx, stdout_rx) = mpsc::channel::<JsonRpcMessage>(buffer_size);
        let (stderr_tx, stderr_rx) = mpsc::channel::<String>(buffer_size);

        // 1. Dedicated Stdin Writer Task
        tokio::spawn(async move {
            let mut writer = stdin;
            while let Some(msg) = stdin_rx.recv().await {
                match serde_json::to_string(&msg) {
                    Ok(json_str) => {
                        let line = format!("{}\n", json_str);
                        if let Err(e) = writer.write_all(line.as_bytes()).await {
                            error!("Failed to write to child stdin: {}", e);
                            break;
                        }
                        if let Err(e) = writer.flush().await {
                            error!("Failed to flush child stdin: {}", e);
                            break;
                        }
                    }
                    Err(e) => {
                        error!("Failed to serialize JSON-RPC message: {}", e);
                    }
                }
            }
        });

        // 2. Dedicated Stdout Reader Task (JSON-RPC line framing)
        tokio::spawn(async move {
            let reader = BufReader::new(stdout);
            let mut lines = reader.lines();

            while let Ok(Some(line)) = lines.next_line().await {
                let trimmed = line.trim();
                if trimmed.is_empty() {
                    continue;
                }

                match serde_json::from_str::<JsonRpcMessage>(trimmed) {
                    Ok(msg) => {
                        if stdout_tx.send(msg).await.is_err() {
                            break;
                        }
                    }
                    Err(e) => {
                        warn!("Received invalid JSON-RPC from child stdout: '{}' ({})", trimmed, e);
                    }
                }
            }
        });

        // 3. Dedicated Stderr Reader Task (Log isolation)
        tokio::spawn(async move {
            let reader = BufReader::new(stderr);
            let mut lines = reader.lines();

            while let Ok(Some(line)) = lines.next_line().await {
                let _ = stderr_tx.send(line).await;
            }
        });

        Ok(Self {
            child: Arc::new(Mutex::new(Some(child))),
            stdin_tx,
            stdout_rx: Mutex::new(stdout_rx),
            stderr_rx: Mutex::new(stderr_rx),
        })
    }

    /// Reads the next diagnostic log line emitted by the child process on `stderr`.
    pub async fn read_stderr(&self) -> Option<String> {
        let mut rx = self.stderr_rx.lock().await;
        rx.recv().await
    }
}

#[async_trait]
impl Transport for StdioProcessTransport {
    async fn send(&self, msg: JsonRpcMessage) -> Result<(), TransportError> {
        self.stdin_tx
            .send(msg)
            .await
            .map_err(|_| TransportError::Disconnected)
    }

    async fn receive(&self) -> Result<Option<JsonRpcMessage>, TransportError> {
        let mut rx = self.stdout_rx.lock().await;
        Ok(rx.recv().await)
    }

    async fn close(&self) -> Result<(), TransportError> {
        let mut child_guard = self.child.lock().await;
        if let Some(mut child) = child_guard.take() {
            let _ = child.kill().await;
        }
        Ok(())
    }
}

impl Drop for StdioProcessTransport {
    fn drop(&mut self) {
        if let Ok(mut child_guard) = self.child.try_lock() {
            if let Some(mut child) = child_guard.take() {
                let _ = child.start_kill();
            }
        }
    }
}

/// Generic Stdio Stream transport wrapping async readers and writers.
pub struct StdioStreamTransport<R, W> {
    reader: Mutex<Lines<BufReader<R>>>,
    writer: Mutex<W>,
}

impl<R, W> StdioStreamTransport<R, W>
where
    R: tokio::io::AsyncRead + Unpin + Send + 'static,
    W: tokio::io::AsyncWrite + Unpin + Send + 'static,
{
    pub fn new(reader: R, writer: W) -> Self {
        Self {
            reader: Mutex::new(BufReader::new(reader).lines()),
            writer: Mutex::new(writer),
        }
    }
}

#[async_trait]
impl<R, W> Transport for StdioStreamTransport<R, W>
where
    R: tokio::io::AsyncRead + Unpin + Send + 'static,
    W: tokio::io::AsyncWrite + Unpin + Send + 'static,
{
    async fn send(&self, msg: JsonRpcMessage) -> Result<(), TransportError> {
        let json_str = serde_json::to_string(&msg)?;
        let line = format!("{}\n", json_str);
        let mut writer = self.writer.lock().await;
        writer.write_all(line.as_bytes()).await?;
        writer.flush().await?;
        Ok(())
    }

    async fn receive(&self) -> Result<Option<JsonRpcMessage>, TransportError> {
        let mut lines = self.reader.lock().await;
        loop {
            match lines.next_line().await {
                Ok(Some(line)) => {
                    let trimmed = line.trim();
                    if trimmed.is_empty() {
                        continue;
                    }
                    match serde_json::from_str::<JsonRpcMessage>(trimmed) {
                        Ok(msg) => return Ok(Some(msg)),
                        Err(e) => {
                            warn!("Ignored malformed JSON-RPC line on stream: '{}' ({})", trimmed, e);
                            continue;
                        }
                    }
                }
                Ok(None) => return Ok(None),
                Err(e) => return Err(TransportError::Io(e.to_string())),
            }
        }
    }

    async fn close(&self) -> Result<(), TransportError> {
        let mut writer = self.writer.lock().await;
        writer.shutdown().await?;
        Ok(())
    }
}
