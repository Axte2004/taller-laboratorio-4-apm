"""Run the versioned k6 scenario and record evidence by load step.

Run from the repository root in a Codespace after `docker compose up --build -d`.
Only Python's standard library is needed on the host.
"""

import csv
import json
import math
import re
import subprocess
import threading
import time
import urllib.request
from pathlib import Path


OUT = Path("resultados")
OUT.mkdir(exist_ok=True)
STEPS = [10, 25, 50, 100, 200, 400]
WARMUP = 60
DURATION = 180
SAMPLE_EVERY = 5


def command(*args, timeout=20):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=True).stdout.strip()


def metrics():
    with urllib.request.urlopen("http://127.0.0.1:8000/metrics", timeout=3) as response:
        content = response.read().decode("utf-8")
    requests = {}
    buckets = {}
    for line in content.splitlines():
        if line.startswith("crud_requests_total{"):
            labels, value = line.split("} ", 1)
            status = re.search(r'status="([^"]+)"', labels).group(1)
            operation = re.search(r'operation="([^"]+)"', labels).group(1)
            requests[(operation, status)] = float(value)
        elif line.startswith("crud_request_duration_seconds_bucket{"):
            labels, value = line.split("} ", 1)
            boundary = re.search(r'le="([^"]+)"', labels).group(1)
            operation = re.search(r'operation="([^"]+)"', labels).group(1)
            buckets[(operation, float(boundary))] = float(value)
    return requests, buckets


def memory_mb(text):
    first = text.split("/")[0].strip()
    match = re.match(r"([0-9.]+)\s*([KMGTP]?i?B)", first)
    if not match:
        return None
    size, unit = float(match.group(1)), match.group(2)
    factor = {"B": 1e-6, "kB": 1e-3, "KB": 1e-3, "KiB": 2**10 / 1e6,
              "MB": 1, "MiB": 2**20 / 1e6, "GB": 1e3, "GiB": 2**30 / 1e6}
    return size * factor.get(unit, 0)


def resources():
    lines = command("docker", "stats", "--no-stream", "--format", "{{json .}}", timeout=25).splitlines()
    output = {}
    for line in lines:
        item = json.loads(line)
        name = item.get("Name", "")
        for service in ("app", "db", "k6"):
            if f"-{service}-" in name:
                output[service] = {
                    "cpu": float(item["CPUPerc"].replace("%", "")),
                    "mem_mb": memory_mb(item["MemUsage"]),
                }
    return output


def connections():
    active = command("docker", "compose", "exec", "-T", "db", "psql", "-U", "taller", "-d", "crud", "-Atc",
                     "select greatest(count(*)-1,0) from pg_stat_activity where state = 'active';", timeout=10)
    return int(active)


def quantile(buckets, total, probability):
    if total <= 0:
        return None
    for boundary, count in sorted(buckets.items()):
        if count >= total * probability and math.isfinite(boundary):
            return round(boundary * 1000, 1)
    return None


def summarize(samples):
    rows = []
    for index, users in enumerate(STEPS):
        start = WARMUP + index * DURATION + 15
        end = WARMUP + (index + 1) * DURATION - 10
        selected = [s for s in samples if start <= s["elapsed"] <= end and "requests" in s]
        if len(selected) < 2:
            rows.append({"usuarios": users, "observacion": "sin muestras suficientes"})
            continue
        first, last = selected[0], selected[-1]
        duration = last["elapsed"] - first["elapsed"]
        request_delta = {key: last["requests"].get(key, 0) - first["requests"].get(key, 0)
                         for key in set(first["requests"]) | set(last["requests"])}
        total = sum(request_delta.values())
        errors = sum(value for (operation, status), value in request_delta.items() if not status.startswith("2"))
        all_boundaries = {boundary for _, boundary in last["buckets"]}
        bucket_delta = {
            boundary: sum(last["buckets"].get((operation, boundary), 0) -
                          first["buckets"].get((operation, boundary), 0)
                          for operation in ("list", "read", "create", "update", "delete"))
            for boundary in all_boundaries
        }
        cpu_app = [s.get("resources", {}).get("app", {}).get("cpu") for s in selected]
        cpu_db = [s.get("resources", {}).get("db", {}).get("cpu") for s in selected]
        cpu_k6 = [s.get("resources", {}).get("k6", {}).get("cpu") for s in selected]
        mem_app = [s.get("resources", {}).get("app", {}).get("mem_mb") for s in selected]
        mem_db = [s.get("resources", {}).get("db", {}).get("mem_mb") for s in selected]
        nonnull = lambda values: [x for x in values if x is not None]
        avg = lambda values: round(sum(nonnull(values)) / len(nonnull(values)), 1) if nonnull(values) else None
        maximum = lambda values: round(max(nonnull(values)), 1) if nonnull(values) else None
        rows.append({
            "usuarios": users, "peticiones_por_segundo": round(total / duration, 2),
            "p50_ms": quantile(bucket_delta, total, .50),
            "p95_ms": quantile(bucket_delta, total, .95),
            "p99_ms": quantile(bucket_delta, total, .99),
            "error_porcentaje": round(errors / total * 100, 2) if total else None,
            "cpu_app_pct_promedio": avg(cpu_app), "cpu_bd_pct_promedio": avg(cpu_db),
            "cpu_k6_pct_promedio": avg(cpu_k6),
            "mem_app_mb_max": maximum(mem_app), "mem_bd_mb_max": maximum(mem_db),
            "conexiones_bd_activas_max": maximum([s.get("connections") for s in selected]),
            "muestras": len(selected), "ventana_s": round(duration, 1), "peticiones": int(total),
        })
    return rows


def main():
    command("docker", "compose", "ps", timeout=10)
    with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=3) as response:
        assert response.status == 200
    max_connections = int(command("docker", "compose", "exec", "-T", "db", "psql", "-U", "taller", "-d", "crud", "-Atc", "show max_connections;"))
    print("PostgreSQL max_connections:", max_connections, flush=True)
    print("Máquina:", command("uname", "-a"), flush=True)
    print("CPU:", command("nproc"), "núcleos", flush=True)
    print("Memoria:", command("free", "-h").splitlines()[1], flush=True)
    started = time.monotonic()
    run = subprocess.Popen(["docker", "compose", "run", "--rm", "k6", "run", "/scripts/stress.js"],
                           stdout=(OUT / "k6.log").open("w", encoding="utf-8"),
                           stderr=subprocess.STDOUT)
    samples = []
    try:
        while run.poll() is None:
            now = time.monotonic()
            sample = {"elapsed": round(now - started, 3), "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
            try:
                req, bucket = metrics()
                sample["requests"] = {"|".join(key): value for key, value in req.items()}
                sample["buckets"] = {"|".join(map(str, key)): value for key, value in bucket.items()}
                sample["resources"] = resources()
                sample["connections"] = connections()
            except Exception as exc:
                sample["error"] = repr(exc)
            samples.append(sample)
            with (OUT / "muestras.jsonl").open("a", encoding="utf-8") as file:
                file.write(json.dumps(sample, ensure_ascii=False) + "\n")
            if len(samples) % 12 == 0:
                print("Transcurridos", round(sample["elapsed"]), "s; muestras", len(samples), flush=True)
            time.sleep(max(0, SAMPLE_EVERY - (time.monotonic() - now)))
    finally:
        run.wait()
    parsed = []
    for sample in samples:
        if "requests" in sample:
            sample["requests"] = {tuple(key.split("|")): value for key, value in sample["requests"].items()}
            sample["buckets"] = {(operation, float(boundary)): value for key, value in sample["buckets"].items()
                                 for operation, boundary in [key.split("|")]}
            parsed.append(sample)
    rows = summarize(parsed)
    with (OUT / "mediciones_completas.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (OUT / "mediciones.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["usuarios", "peticiones_por_segundo", "p95_ms", "error_porcentaje"])
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in writer.fieldnames})
    (OUT / "perfil.json").write_text(json.dumps({"max_connections": max_connections,
        "nproc": command("nproc"), "free": command("free", "-h"), "uname": command("uname", "-a"),
        "k6_exit_code": run.returncode}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(rows, ensure_ascii=False, indent=2), flush=True)
    print("k6 exit code:", run.returncode, flush=True)


if __name__ == "__main__":
    main()

