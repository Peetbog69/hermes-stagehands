# Transaction API contract

POST /v2/transactions accepts a JSON object containing amount_cents, currency,
merchant_id, and an optional metadata object. Amounts are integer minor units;
currency is an ISO 4217 code. The current sandbox supports USD and EUR.
Payloads larger than 64 KiB receive HTTP 413 before upstream dispatch.

## Successful responses

A newly accepted write returns 202 with a transaction ID and status `pending`.
GET /v2/transactions/{id} returns the current state. Terminal states are
`settled`, `failed`, and `reversed`; clients must not interpret `pending` as a
successful settlement. Pagination uses an opaque cursor, with 100 items per
page by default and a maximum of 250.

## Error envelope

Errors have code, message, and request_id fields. Validation errors return 400.
Tenant isolation failures do not disclose the existence of another tenant's
transaction. Retry behavior is documented in 04_operations.md and rate-limit
semantics in 03_rate_limits.md.

## Compatibility

Clients must tolerate new response fields and unknown metadata keys. A new
terminal state requires a versioned contract change. Sandbox identifiers and
sample customer data are synthetic and cannot be used against production.
