# browse_dataset.py
import os, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv(".env", override=True)

def _conn():
    return psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        sslmode=os.getenv("PGSSLMODE", "require"),
    )

def sample_reviews(topic: str | None = None, n: int = 10):
    sql = """
      select review_id, topic, sentiment, prompt, ideal_response
      from public.reviews
      {where}
      order by random()
      limit %s
    """
    where = "where topic = %s" if topic else ""
    params = (n,) if not topic else (topic, n)
    with _conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql.format(where=where), params)
        return cur.fetchall()

if __name__ == "__main__":
    # Example: 10 random rows overall
    for r in sample_reviews(None, 10):
        print(f"[{r['topic']}/{r['sentiment']}] {r['prompt']}\n→ ideal: {r['ideal_response']}\n")
