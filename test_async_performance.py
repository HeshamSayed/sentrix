#!/usr/bin/env python3
"""
Performance test for Async SENTRIX Edge
Tests concurrent request handling and measures throughput
"""

import asyncio
import httpx
import time
from typing import List, Tuple
import statistics

# Configuration
EDGE_URL = "http://localhost:8001"
HEALTH_URL = f"{EDGE_URL}/health"
METRICS_URL = f"{EDGE_URL}/metrics"

# Test parameters
CONCURRENT_REQUESTS = [10, 50, 100, 500, 1000]
REQUESTS_PER_BATCH = 100


async def make_request(client: httpx.AsyncClient, url: str) -> Tuple[int, float]:
    """Make a single async request and return status code and latency"""
    start = time.time()
    try:
        response = await client.get(url, timeout=10.0)
        latency = (time.time() - start) * 1000  # milliseconds
        return response.status_code, latency
    except Exception as e:
        latency = (time.time() - start) * 1000
        return 0, latency


async def run_concurrent_test(url: str, num_concurrent: int, total_requests: int):
    """Run concurrent requests and measure performance"""
    print(f"\n{'='*70}")
    print(f"Testing with {num_concurrent} concurrent connections")
    print(f"Total requests: {total_requests}")
    print(f"{'='*70}")
    
    results = []
    start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        # Create batches of concurrent requests
        for batch_start in range(0, total_requests, num_concurrent):
            batch_size = min(num_concurrent, total_requests - batch_start)
            tasks = [make_request(client, url) for _ in range(batch_size)]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            
            # Show progress
            if (batch_start + batch_size) % 100 == 0 or (batch_start + batch_size) == total_requests:
                elapsed = time.time() - start_time
                rps = (batch_start + batch_size) / elapsed
                print(f"  Progress: {batch_start + batch_size}/{total_requests} | {rps:.1f} req/s")
    
    total_time = time.time() - start_time
    
    # Analyze results
    status_codes = [r[0] for r in results]
    latencies = [r[1] for r in results]
    
    successful = sum(1 for s in status_codes if 200 <= s < 300)
    failed = len(results) - successful
    
    print(f"\n📊 Results:")
    print(f"  ✅ Successful: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
    print(f"  ❌ Failed: {failed}")
    print(f"  ⏱️  Total time: {total_time:.2f}s")
    print(f"  🚀 Throughput: {len(results)/total_time:.1f} requests/second")
    print(f"\n📈 Latency:")
    print(f"  Min: {min(latencies):.1f}ms")
    print(f"  Max: {max(latencies):.1f}ms")
    print(f"  Mean: {statistics.mean(latencies):.1f}ms")
    print(f"  Median: {statistics.median(latencies):.1f}ms")
    if len(latencies) > 10:
        print(f"  P95: {statistics.quantiles(latencies, n=20)[18]:.1f}ms")
        print(f"  P99: {statistics.quantiles(latencies, n=100)[98]:.1f}ms")
    
    return {
        "concurrent": num_concurrent,
        "total_requests": len(results),
        "successful": successful,
        "failed": failed,
        "total_time": total_time,
        "throughput": len(results)/total_time,
        "latency_mean": statistics.mean(latencies),
        "latency_p95": statistics.quantiles(latencies, n=20)[18] if len(latencies) > 10 else 0,
        "latency_p99": statistics.quantiles(latencies, n=100)[98] if len(latencies) > 10 else 0,
    }


async def main():
    """Main test runner"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║         SENTRIX ASYNC EDGE PERFORMANCE TEST                  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

Configuration:
  • Edge URL: {EDGE_URL}
  • Test endpoint: /health (no auth required)
  • Workers: 8 (async with uvloop)
  • Concurrent levels: {concurrent_levels}

Starting tests...
""".format(EDGE_URL=EDGE_URL, concurrent_levels=CONCURRENT_REQUESTS))
    
    # Warm-up
    print("🔥 Warming up...")
    async with httpx.AsyncClient() as client:
        for _ in range(10):
            await client.get(HEALTH_URL)
    
    print("✅ Warm-up complete\n")
    
    # Run tests at different concurrency levels
    all_results = []
    for concurrent in CONCURRENT_REQUESTS:
        result = await run_concurrent_test(HEALTH_URL, concurrent, REQUESTS_PER_BATCH)
        all_results.append(result)
        await asyncio.sleep(1)  # Cool down between tests
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 SUMMARY - Throughput by Concurrency Level")
    print(f"{'='*70}")
    print(f"{'Concurrent':<12} {'Throughput':<18} {'Mean Latency':<15} {'P99 Latency'}")
    print(f"{'-'*70}")
    for r in all_results:
        print(f"{r['concurrent']:<12} {r['throughput']:>8.1f} req/s     {r['latency_mean']:>8.1f}ms      {r['latency_p99']:>8.1f}ms")
    
    # Best throughput
    best = max(all_results, key=lambda x: x['throughput'])
    print(f"\n🏆 Best Performance:")
    print(f"   {best['throughput']:.1f} req/s at {best['concurrent']} concurrent connections")
    print(f"   Mean latency: {best['latency_mean']:.1f}ms")
    
    # Get final metrics
    print(f"\n📈 Fetching Prometheus metrics...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(METRICS_URL)
            metrics_lines = resp.text.split('\n')
            for line in metrics_lines:
                if 'sentrix_requests_total' in line and 'GET' in line and '200' in line:
                    print(f"   {line}")
                elif 'sentrix_request_latency' in line and 'sum' in line:
                    print(f"   {line}")
        except:
            print("   (Metrics unavailable)")
    
    print(f"\n{'='*70}")
    print("✅ Test complete!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())

