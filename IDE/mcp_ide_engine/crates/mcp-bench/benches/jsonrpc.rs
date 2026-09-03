//! JSON-RPC 2.0 and MCP Tool Invocation Criterion Benchmarks

use criterion::{black_box, criterion_group, criterion_main, Criterion};
use mcp_bench::helpers::setup_benchmark_environment;
use serde_json::json;

fn bench_jsonrpc_tool_call(c: &mut Criterion) {
    let rt = tokio::runtime::Builder::new_multi_thread()
        .worker_threads(4)
        .enable_all()
        .build()
        .unwrap();

    let (_, server) = setup_benchmark_environment();

    c.bench_function("mcp_tool_invocation", |b| {
        b.to_async(&rt).iter(|| async {
            let res = server
                .tools()
                .call("echo_tool", Some(json!({ "msg": "benchmarking-mcp" })))
                .await
                .unwrap();
            black_box(res);
        });
    });
}

criterion_group!(benches, bench_jsonrpc_tool_call);
criterion_main!(benches);
