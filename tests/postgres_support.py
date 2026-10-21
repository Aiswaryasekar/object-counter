"""Helpers for tests that talk to a real PostgreSQL server (see docker-compose.yml)."""
import os

import psycopg


def postgres_params(database: str) -> dict:
    return dict(host=os.environ.get('POSTGRES_HOST', 'localhost'),
                port=int(os.environ.get('POSTGRES_PORT', 5432)),
                dbname=database,
                user=os.environ.get('POSTGRES_USER', 'counter'),
                password=os.environ.get('POSTGRES_PASSWORD', 'counter'))


def create_database_if_missing(database: str):
    """Raises psycopg.OperationalError when the server is not reachable."""
    with psycopg.connect(**postgres_params('postgres'), autocommit=True, connect_timeout=3) as connection:
        exists = connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,)).fetchone()
        if not exists:
            connection.execute(f'CREATE DATABASE "{database}"')