from typing import List

import psycopg

from counter.domain.models import ObjectCount
from counter.domain.ports import ObjectCountRepo

CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS object_counts (
        object_class TEXT PRIMARY KEY,
        count        BIGINT NOT NULL DEFAULT 0
    )
"""

READ_ALL_SQL = "SELECT object_class, count FROM object_counts ORDER BY object_class"

READ_SOME_SQL = """
    SELECT object_class, count FROM object_counts
    WHERE object_class = ANY(%s)
    ORDER BY object_class
"""

# Adds to the stored count, or creates the row if the class is new.
# Done in a single statement so concurrent requests cannot lose updates.
UPSERT_SQL = """
    INSERT INTO object_counts (object_class, count) VALUES (%s, %s)
    ON CONFLICT (object_class) DO UPDATE SET count = object_counts.count + EXCLUDED.count
"""


class CountPostgresRepo(ObjectCountRepo):

    def __init__(self, host, port, database, user, password):
        self.__connection_params = dict(host=host, port=int(port), dbname=database, user=user, password=password)
        self.__create_table_if_missing()

    def read_values(self, object_classes: List[str] = None) -> List[ObjectCount]:
        with psycopg.connect(**self.__connection_params) as connection:
            if object_classes:
                rows = connection.execute(READ_SOME_SQL, (object_classes,)).fetchall()
            else:
                rows = connection.execute(READ_ALL_SQL).fetchall()
        return [ObjectCount(object_class, count) for object_class, count in rows]

    def update_values(self, new_values: List[ObjectCount]):
        if not new_values:
            return
        # Sorted so concurrent transactions always lock rows in the same order.
        rows = sorted((value.object_class, value.count) for value in new_values)
        with psycopg.connect(**self.__connection_params) as connection:
            with connection.cursor() as cursor:
                cursor.executemany(UPSERT_SQL, rows)

    def __create_table_if_missing(self):
        with psycopg.connect(**self.__connection_params) as connection:
            connection.execute(CREATE_TABLE_SQL)