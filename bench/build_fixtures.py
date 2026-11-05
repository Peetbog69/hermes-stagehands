"""Rebuild deterministic synthetic data and its integrity manifest (stdlib only)."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
INCIDENTS = {
    417: "authd[1842]: ERROR jwks_refresh_failed issuer=https://id.atlas.example.test kid=rot-2026-11 reason=upstream_timeout rejected_requests=37",
    1193: "kernel: Out of memory: Killed process 2317 (ledger-worker) total-vm:7340032kB anon-rss:6291456kB oom_score_adj:200",
    1781: 'nginx[908]: ERROR upstream timed out (110: Connection timed out) request="POST /v2/transactions HTTP/1.1" upstream="http://10.42.0.18:8080" status=504 request_id=req-1781',
}


def checked(path):
    """Reject paths/symlinks escaping the benchmark directory."""
    path.resolve().relative_to(ROOT)
    return path


def json_text(value):
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def build():
    checked(FIXTURES).mkdir(exist_ok=True)
    start = datetime(2026, 11, 1, tzinfo=timezone.utc)
    lines = []
    for number in range(1, 2001):
        stamp = (start + timedelta(seconds=number * 3)).isoformat()
        normal = (
            f"authd[1842]: INFO token_verified tenant=tenant-{number % 12:02d} subject=svc-{number % 7} audience=atlas-api latency_ms={4 + number % 9}",
            f"kernel: INFO eth0: rx_packets={900000 + number * 13} tx_packets={800000 + number * 11} dropped=0 link=up",
            f'nginx[908]: INFO 192.0.2.{1 + number % 200} "GET /v2/transactions/txn-{number:06d} HTTP/1.1" status=200 bytes={400 + number % 512} duration_ms={12 + number % 60} request_id=req-{number:04d}',
        )
        lines.append(f"{stamp} atlas-edge-01 {INCIDENTS.get(number, normal[number % 3])}")
    checked(FIXTURES / "logs_2000_lines.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    transactions = []
    for index in range(1, 61):
        status = "failed" if index in (17, 44) else "pending" if index in (23, 51) else "settled"
        transactions.append({
            "id": f"txn-{index:06d}", "tenant_id": f"tenant-{index % 12:02d}",
            "money": {"amount_cents": 1000 + index * 137, "currency": "USD"},
            "status": status,
            "merchant": {"id": f"merchant-{index % 9:03d}", "region": "us-east-1"},
            "payment": {"method": "synthetic_card", "last_four": f"{1000 + index:04d}"},
            "attempts": [{"number": 1, "result": "timeout" if status == "failed" else "accepted",
                          "gateway": {"request_id": f"pay-{index:06d}", "latency_ms": 30 + index}}],
            "metadata": {"order_id": f"order-{index:06d}", "environment": "sandbox", "synthetic": True},
        })
    payload = {"schema_version": "2.0", "export": {"id": "export-synthetic-001",
               "created_at": "2026-11-01T02:00:00Z", "transactions": transactions},
               "annotations": {"purpose": "Synthetic settlement reconciliation export", "padding": ""}}
    # Exactly 50 KiB (51,200 bytes), including the terminating newline.
    padding_size = 50 * 1024 - len(json_text(payload).encode("utf-8"))
    if padding_size < 0:
        raise ValueError("transaction data exceeded the 50 KiB fixture budget")
    payload["annotations"]["padding"] = ("sandbox-export " * (padding_size // 15 + 1))[:padding_size]
    checked(FIXTURES / "dump_50kb.json").write_text(json_text(payload), encoding="utf-8")

    names = ["logs_2000_lines.txt", "dump_50kb.json"]
    names += [f"codebase/{name}.py" for name in ("accounts", "gateway", "worker")]
    names += [f"docs/{name}.md" for name in (
        "01_gateway", "02_auth", "03_rate_limits", "04_operations", "05_api_contract")]
    files = {}
    for name in sorted(names):
        data = checked(FIXTURES / name).read_bytes()
        files[name] = {"bytes": len(data), "lines": len(data.splitlines()),
                       "sha256": hashlib.sha256(data).hexdigest()}
    manifest = {
        "schema_version": 1, "synthetic": True, "files": files,
        "ground_truth": {
            "log_incidents": [{"line": line, "evidence": evidence} for line, evidence in INCIDENTS.items()],
            "code_findings": ["opposite-direction transfers acquire the same locks in reverse order",
                              "RetryExhausted is not caught by the TransientGatewayError handler"],
            "transactions": {"count": 60, "failed_ids": ["txn-000017", "txn-000044"],
                             "pending_ids": ["txn-000023", "txn-000051"],
                             "total_amount_cents": sum(t["money"]["amount_cents"] for t in transactions)},
        },
    }
    checked(FIXTURES / "manifest.json").write_text(json_text(manifest), encoding="utf-8")
    print(f"Generated {len(files)} fixture files; dump = {files['dump_50kb.json']['bytes']} bytes")


if __name__ == "__main__":
    build()
