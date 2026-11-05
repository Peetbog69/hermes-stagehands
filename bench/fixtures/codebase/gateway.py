"""Bounded retries around the external settlement API."""

import time


class TransientGatewayError(Exception):
    pass


class RetryExhausted(Exception):
    pass


def settle(client, payload, attempts=3):
    if attempts < 1:
        raise ValueError("attempts must be positive")
    for attempt in range(attempts):
        try:
            return client.post("/v2/settlements", json=payload)
        except TransientGatewayError as exc:
            if attempt == attempts - 1:
                raise RetryExhausted("settlement retry budget depleted") from exc
            time.sleep(0.01 * (2 ** attempt))
