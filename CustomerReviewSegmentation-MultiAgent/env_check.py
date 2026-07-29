# db_utils_pg.py
from psycopg2.extras import RealDictCursor
import psycopg2, os

def _connect():
    return psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT"),
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        sslmode=os.getenv("PGSSLMODE", "require"),
    )

def get_examples_by_topic_pg(topic: str, n: int = 3):
    with _connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            select prompt, ideal_response
            from public.reviews
            where topic = %s
            order by random()
            limit %s
            """,
            (topic, int(n)),          # <-- tuple, length 2
        )
        return cur.fetchall()

def get_examples_by_topic_sentiment_pg(topic: str, sentiment: str, n: int = 3):
    with _connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            select prompt, ideal_response
            from public.reviews
            where topic = %s and sentiment = %s
            order by random()
            limit %s
            """,
            (topic, sentiment, int(n)),  # <-- tuple, length 3
        )
        return cur.fetchall()
