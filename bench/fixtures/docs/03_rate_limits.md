# Tenant rate limits

The default authenticated tenant budget is 120 requests per minute with a
burst capacity of 30 requests. A token bucket is keyed by verified tenant ID,
not by source IP. All application routes share that tenant budget; health
checks and the internal metrics endpoint are excluded.

## Rejection contract

An exhausted bucket returns HTTP 429 and a Retry-After header in whole seconds.
The response includes a request ID and the stable error code `rate_limited`.
Clients should wait for Retry-After and add jitter before retrying. Immediate
retries count as further attempts and do not replenish the bucket.

## Distributed operation

The regional counter store provides atomic bucket updates. If it is unavailable,
writes fail closed with 503. Reads may use a local emergency cap of 10 requests
per minute per tenant for at most 60 seconds. This fallback must emit a metric
and must not be mistaken for the normal 120 requests per minute contract.

## Overrides

Enterprise overrides require an owner, expiry date, and approval record. A
per-route emergency cap can only lower the effective limit. Operators should
inspect the resolved tenant policy before treating a 429 as a gateway defect.
