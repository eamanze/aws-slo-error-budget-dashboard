#!/usr/bin/env python3
import argparse
import concurrent.futures
import statistics
import time
import urllib.error
import urllib.request


def request_once(url: str) -> tuple[int, float]:
    started = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    except OSError:
        status = 0
    return status, time.monotonic() - started


def main():
    parser = argparse.ArgumentParser(description="Dependency-free HTTP load generator")
    parser.add_argument("--url", default="http://localhost:8080/")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()
    with concurrent.futures.ThreadPoolExecutor(args.concurrency) as pool:
        results = list(pool.map(request_once, [args.url] * args.requests))
    durations = sorted(duration for _, duration in results)
    successes = sum(200 <= status < 300 for status, _ in results)
    p95 = durations[max(0, int(len(durations) * 0.95) - 1)]
    print(f"requests={len(results)} success_ratio={successes/len(results):.3f} "
          f"mean_seconds={statistics.mean(durations):.3f} p95_seconds={p95:.3f}")
    raise SystemExit(0 if successes == len(results) else 1)


if __name__ == "__main__":
    main()

