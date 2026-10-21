"""Contract tests: every ObjectCountRepo implementation must behave the same way.

The PostgreSQL variant needs a running server (`docker compose up -d postgres`)
and is skipped automatically when none is reachable. It uses its own database
(`counter_test`) so your real data is never touched.
"""
import psycopg
import pytest

from counter.adapters.count_repo import CountInMemoryRepo
from counter.adapters.postgres_count_repo import CountPostgresRepo
from counter.domain.models import ObjectCount
from tests.postgres_support import postgres_params, create_database_if_missing

TEST_DATABASE = 'counter_test'


@pytest.fixture
def postgres_repo():
    try:
        create_database_if_missing(TEST_DATABASE)
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL is not reachable (run `docker compose up -d postgres`)")
    params = postgres_params(TEST_DATABASE)
    repo = CountPostgresRepo(host=params['host'], port=params['port'], database=TEST_DATABASE,
                             user=params['user'], password=params['password'])
    with psycopg.connect(**params) as connection:
        connection.execute("TRUNCATE object_counts")
    return repo


@pytest.fixture(params=['in_memory', 'postgres'])
def repo(request):
    if request.param == 'in_memory':
        return CountInMemoryRepo()
    return request.getfixturevalue('postgres_repo')


def sorted_by_class(object_counts):
    return sorted(object_counts, key=lambda object_count: object_count.object_class)


def test_new_repo_is_empty(repo):
    assert repo.read_values() == []


def test_stores_new_values(repo):
    repo.update_values([ObjectCount('cat', 2), ObjectCount('dog', 1)])

    assert sorted_by_class(repo.read_values()) == [ObjectCount('cat', 2), ObjectCount('dog', 1)]


def test_adds_to_existing_values(repo):
    repo.update_values([ObjectCount('cat', 2)])
    repo.update_values([ObjectCount('cat', 3), ObjectCount('dog', 1)])

    assert sorted_by_class(repo.read_values()) == [ObjectCount('cat', 5), ObjectCount('dog', 1)]


def test_reads_only_requested_classes(repo):
    repo.update_values([ObjectCount('cat', 2), ObjectCount('dog', 1), ObjectCount('cup', 4)])

    assert sorted_by_class(repo.read_values(['cat', 'cup'])) == [ObjectCount('cat', 2), ObjectCount('cup', 4)]


def test_updating_with_nothing_changes_nothing(repo):
    repo.update_values([ObjectCount('cat', 2)])
    repo.update_values([])

    assert repo.read_values() == [ObjectCount('cat', 2)]