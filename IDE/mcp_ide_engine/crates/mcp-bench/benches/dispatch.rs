//! Task Dispatch Latency Criterion Benchmarks (<5ms target)

use criterion::{black_box, criterion_group, criterion_main, Criterion};
use mcp_bench::helpers::setup_benchmark_environment;
use mcp_core::registry::TaskPriority;
use serde_json::json;

fn bench_task_dispatch_latency(c: &mut Criterion) {
    let rt = tokio::runtime::Builder::new_multi_thread()
        .worker_threads(4)
        .enable_all()
        .build()
        .unwrap();

    let (dispatcher, _) = setup_benchmark_environment();

    c.bench_function("task_dispatch_noop", |b| {
        b.to_async(&rt).iter(|| async {
            let handle = dispatcher
                .dispatch("noop", json!({ "k": "v" }), Some(TaskPriority::High))
                .unwrap();
            let output = handle.wait().await.unwrap();
            black_box(output);
        });
    });

    c.bench_function("task_dispatch_compute_bridge", |b| {
        b.to_async(&rt).iter(|| async {
            let handle = dispatcher
                .dispatch(
                    "compute_hash",
                    json!({ "iterations": 500 }),
                    Some(TaskPriority::Normal),
                )
                .unwrap();
            let output = handle.wait().await.unwrap();
            black_box(output);
        });
    });
}

criterion_group!(benches, bench_task_dispatch_latency);
criterion_main!(benches);
