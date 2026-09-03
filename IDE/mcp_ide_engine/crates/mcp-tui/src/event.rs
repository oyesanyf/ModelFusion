//! Event handling and asynchronous stream aggregation for TUI

use crossterm::event::{self, Event as CrosstermEvent, KeyEvent, MouseEvent};
use futures::StreamExt;
use mcp_core::telemetry::EngineEvent;
use mcp_resource::telemetry::SystemSnapshot;
use std::time::Duration;
use tokio::sync::mpsc;

/// TUI Event envelope
#[derive(Debug, Clone)]
pub enum AppEvent {
    /// Terminal key press
    Key(KeyEvent),
    /// Terminal mouse event
    Mouse(MouseEvent),
    /// Terminal resize (width, height)
    Resize(u16, u16),
    /// Periodic UI tick (e.g. 60 FPS or 100ms)
    Tick,
    /// Real-time engine event (task state changes, dispatch latency)
    Engine(EngineEvent),
    /// Real-time resource snapshot update
    Resource(SystemSnapshot),
    /// User log entry
    Log(String),
}

/// Asynchronous event loop dispatcher
pub struct EventHandler {
    receiver: mpsc::UnboundedReceiver<AppEvent>,
    _tick_handle: tokio::task::JoinHandle<()>,
}

impl EventHandler {
    /// Initialize event stream with specified tick rate
    pub fn new(
        tick_rate: Duration,
        mut event_rx: tokio::sync::broadcast::Receiver<EngineEvent>,
        mut resource_rx: tokio::sync::watch::Receiver<SystemSnapshot>,
    ) -> Self {
        let (sender, receiver) = mpsc::unbounded_channel();
        let tx = sender.clone();

        // Background task combining crossterm events, tick, engine events, and telemetry
        let tick_handle = tokio::spawn(async move {
            let mut tick_interval = tokio::time::interval(tick_rate);
            let mut event_reader = event::EventStream::new();

            loop {
                tokio::select! {
                    _ = tick_interval.tick() => {
                        if tx.send(AppEvent::Tick).is_err() {
                            break;
                        }
                    }
                    maybe_event = event_reader.next() => {
                        match maybe_event {
                            Some(Ok(CrosstermEvent::Key(key))) => {
                                if tx.send(AppEvent::Key(key)).is_err() {
                                    break;
                                }
                            }
                            Some(Ok(CrosstermEvent::Mouse(mouse))) => {
                                let _ = tx.send(AppEvent::Mouse(mouse));
                            }
                            Some(Ok(CrosstermEvent::Resize(w, h))) => {
                                let _ = tx.send(AppEvent::Resize(w, h));
                            }
                            Some(Err(_)) | None => {}
                            _ => {}
                        }
                    }
                    Ok(engine_event) = event_rx.recv() => {
                        let _ = tx.send(AppEvent::Engine(engine_event));
                    }
                    Ok(()) = resource_rx.changed() => {
                        let snap = resource_rx.borrow_and_update().clone();
                        let _ = tx.send(AppEvent::Resource(snap));
                    }
                }
            }
        });

        Self {
            receiver,
            _tick_handle: tick_handle,
        }
    }

    /// Next event in stream
    pub async fn next(&mut self) -> Option<AppEvent> {
        self.receiver.recv().await
    }
}
