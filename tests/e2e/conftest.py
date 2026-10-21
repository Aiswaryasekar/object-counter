"""Starts the real application and checks that its dependencies are up.

Needs TF Serving and PostgreSQL running, e.g. via `make up`.
The app is started on a free port and writes to its own database (`counter_e2e`),
so nothing you stored while developing is touched.
"""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import psycopg
import pytest

from tests.postgres_support import postgres_params, create_database_if_missing

PROJECT_ROOT = Path(__file__).resolve().parents[2]
E2E_DATABASE = 'counter_e2e'
STARTUP_TIMEOUT_SECONDS = 30


def is_reachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def start_app(port: int, env: dict, log_file) -> subprocess.Popen:
    code = f"from counter.entrypoints.webapp import create_app; create_app().run('127.0.0.1', {port})"
    return subprocess.Popen([sys.executable, '-c', code], cwd=PROJECT_ROOT, env=env,
                            stdout=log_file, stderr=subprocess.STDOUT)


def wait_until_listening(app: subprocess.Popen, port: int, log_path: Path):
    deadline = time.time() + STARTUP_TIMEOUT_SECONDS
    while time.time() < deadline:
        if app.poll() is not None:
            pytest.fail(f"The app exited during startup:\n{log_path.read_text()}")
        if is_reachable('127.0.0.1', port):
            return
        time.sleep(0.3)
    pytest.fail(f"The app did not start within {STARTUP_TIMEOUT_SECONDS}s:\n{log_path.read_text()}")


@pytest.fixture(scope='session')
def api_url(tmp_path_factory):
    tfs_host = os.environ.get('TFS_HOST', 'localhost')
    tfs_port = int(os.environ.get('TFS_PORT', 8501))
    if not is_reachable(tfs_host, tfs_port):
        pytest.skip(f"TF Serving is not reachable at {tfs_host}:{tfs_port} (run `make up`)")
    try:
        create_database_if_missing(E2E_DATABASE)
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL is not reachable (run `make up`)")

    port = free_port()
    env = dict(os.environ, ENV='prod', DB_BACKEND='postgres', POSTGRES_DB=E2E_DATABASE)
    log_path = tmp_path_factory.mktemp('e2e') / 'app.log'
    with open(log_path, 'w') as log_file:
        app = start_app(port, env, log_file)
        try:
            wait_until_listening(app, port, log_path)
            yield f'http://127.0.0.1:{port}'
        finally:
            app.terminate()
            app.wait(timeout=10)


@pytest.fixture(autouse=True)
def empty_counts(api_url):
    """Every test starts with nothing counted."""
    with psycopg.connect(**postgres_params(E2E_DATABASE)) as connection:
        connection.execute("TRUNCATE object_counts")