"""Measure case-generation latency and first-pass validation against a running server.

Usage: python scripts/bench_generate.py [N]   (default N=20)

Notes:
- Industry is varied per call so the server's 10s idempotency guard does not
  dedupe the requests.
- First-try validation is only counted for responses that actually include a
  `refinements_used` field. A missing field is reported as missing, not as a pass.
"""
import json
import statistics
import sys
import time
import urllib.request

URL = "http://localhost:8000/api/v1/cases/generate"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
DELAY = float(sys.argv[2]) if len(sys.argv) > 2 else 0
INDUSTRIES = ["FinTech", "Healthcare", "Retail", "Logistics", "EdTech"]


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]


wall, server = [], []
first_pass = measured = fails = 0

for i in range(N):
    body = {
        "user_id": 1,
        "industry": INDUSTRIES[i % len(INDUSTRIES)],
        "complexity": "beginner",
        "focus_area": "Product Strategy",
        "time_limit": 60,
    }
    req = urllib.request.Request(
        URL, json.dumps(body).encode(), {"Content-Type": "application/json"}
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
    except Exception as exc:
        fails += 1
        print(f"run {i + 1}: FAILED ({exc})")
        continue

    wall.append(time.time() - t0)
    if "generation_time_ms" in data:
        server.append(data["generation_time_ms"] / 1000)
    if "refinements_used" in data:
        measured += 1
        first_pass += data["refinements_used"] == 0
    time.sleep(DELAY)
    print(
        f"run {i + 1}: {wall[-1]:.2f}s "
        f"refinements={data.get('refinements_used', 'not returned')}"
    )

ok = len(wall)
print(f"\nruns: {N}, succeeded: {ok}, failed: {fails}")
if ok:
    print(f"wall time  p50={statistics.median(wall):.2f}s p95={pct(wall, .95):.2f}s")
if server:
    time.sleep(DELAY)
    print(
        f"server-reported  p50={statistics.median(server):.2f}s "
        f"p95={pct(server, .95):.2f}s"
    )
if ok:
    time.sleep(DELAY)
    print(
        f"first-try validation: {first_pass}/{measured} "
        f"(refinements_used present in {measured}/{ok} responses)"
    )