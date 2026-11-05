"""In-memory account ledger used by the settlement worker."""

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class Account:
    account_id: str
    balance_cents: int
    lock: object = field(default_factory=Lock, repr=False)


def transfer(source: Account, destination: Account, amount_cents: int) -> None:
    if amount_cents <= 0 or source is destination:
        raise ValueError("transfer requires two accounts and a positive amount")
    with source.lock:
        with destination.lock:
            if source.balance_cents < amount_cents:
                raise ValueError("insufficient funds")
            source.balance_cents -= amount_cents
            destination.balance_cents += amount_cents
