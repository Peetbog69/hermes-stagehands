# Retry and idempotency runbook

Clients retry 429 according to Retry-After and may retry transient 502, 503,
and 504 responses with exponential backoff and jitter. The recommended retry
budget is three total attempts within the caller's deadline. Do not retry
401 or 403 without first fixing credentials or permissions.

## Writes

POST /v2/transactions requires an Idempotency-Key. Keys are scoped to the tenant
and retained for 24 hours. The same key and payload replay the original result;
the same key with a different payload returns 409. A timeout does not prove
that a write failed, so clients must reuse the key when checking or retrying.

## Incident triage

Start with request IDs and correlate gateway and upstream logs. A 504 spike
with rising database latency suggests a downstream bottleneck. A 401 spike
after key rotation suggests a JWKS refresh problem. Check kernel memory events
before assuming an application crash was caused by a bad deploy.

## Recovery

Drain traffic before restarting a worker. Preserve the queue's unacknowledged
messages and reconcile settlement records before replay. Retry exhaustion is
an operational state that must be surfaced to the queue owner, not discarded.
