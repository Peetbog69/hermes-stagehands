"""Concurrent settlement consumer; upstream owns message acknowledgement."""

from concurrent.futures import ThreadPoolExecutor

from accounts import transfer
from gateway import TransientGatewayError, settle


def process(job, accounts, client):
    source = accounts[job["source"]]
    destination = accounts[job["destination"]]
    transfer(source, destination, job["amount_cents"])
    try:
        return settle(client, job)
    except TransientGatewayError:
        return {"status": "deferred", "job_id": job["id"]}


def run_batch(jobs, accounts, client):
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(lambda job: process(job, accounts, client), jobs))
