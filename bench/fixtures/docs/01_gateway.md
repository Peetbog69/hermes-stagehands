# Atlas API gateway

Atlas terminates TLS and routes `/v2/transactions` to ledger-api and
`/v2/settlements` to settlement-api. Health checks use `/healthz` and bypass
authentication, but application endpoints always pass through the auth filter.
The public hostname in examples is api.atlas.example.test.

## Request pipeline

The order is request ID assignment, header size validation, bearer-token
verification, tenant binding, rate limiting, and upstream dispatch. Request IDs
are opaque UUIDs and are returned as `X-Request-ID`. Never accept a tenant ID
from a query parameter as authorization evidence. Trusted tenant identity comes
from the verified token claim.

## Timeouts and routing

Connection establishment has a 300 ms budget. The overall upstream deadline
is 2 seconds. Read-only requests may retry once on a connect failure within
that deadline. Write requests require the idempotency rules in 04_operations.md.
An upstream timeout returns HTTP 504, while an unavailable upstream returns 503.
The gateway does not silently reroute writes to a different region.

## Deployment

Configuration rolls out to a canary for ten minutes before promotion. A route
change must preserve both the public path and the identity policy. Metrics are
grouped by route template, never by a raw URL containing customer identifiers.
