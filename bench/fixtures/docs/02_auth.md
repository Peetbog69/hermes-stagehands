# Authentication and tenant binding

Clients obtain short-lived access tokens through OAuth 2.0 client credentials.
The gateway validates the signature, issuer, audience, expiry, and tenant claim
before dispatch. The expected audience is `atlas-api`. A token signed by a known
key but issued for another audience is still rejected with HTTP 401.

## Key rotation

JWKS cache TTL is 300 seconds. An unknown key ID triggers one refresh, with a
shared single-flight guard to prevent a request stampede. If the refresh fails,
known unexpired keys may continue to serve until their cache entry expires;
unknown keys fail closed. Clock skew tolerance is 30 seconds, not five minutes.

## Authorization

The `transactions:read` scope allows reads. Writes need `transactions:write`.
Missing or invalid credentials yield 401; an authenticated principal lacking
the required scope receives 403. Service tokens are tenant-scoped: the tenant
in the route must match the signed claim. Administrative access uses a separate
audited route and is not implied by the write scope.

## Observability

Record the issuer, key ID, result code, and request ID. Do not log access tokens,
client secrets, or Authorization headers. Alert on a sustained increase in
unknown key IDs separately from ordinary expired-token failures.
