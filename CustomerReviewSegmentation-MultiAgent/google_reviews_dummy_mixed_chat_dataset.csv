# eval_mixed_responses.py
import os, psycopg2, random
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from customer_service_langgraph import EXECUTOR, ChatState  # uses your compiled graph

load_dotenv(".env", override=True)

TOPICS = ["support", "billing", "delivery", "product", "app"]  # adjust to your dataset

def _conn():
    return psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        sslmode=os.getenv("PGSSLMODE", "require"),
    )

def fetch_k_per_topic(k: int = 2):
    rows = []
    with _conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        for t in TOPICS:
            cur.execute(
                """
                select review_id, topic, sentiment, prompt, ideal_response
                from public.reviews
                where topic = %s
                order by random()
                limit %s
                """,
                (t, k),
            )
            rows.extend(cur.fetchall())
    random.shuffle(rows)
    return rows

def run_eval(k_per_topic: int = 2):
    tests = fetch_k_per_topic(k_per_topic)
    results = []
    for i, row in enumerate(tests, 1):
        state = ChatState(messages=[row["prompt"]], topic=row["topic"])
        out = EXECUTOR.invoke(state)
        reply = out.get("final_reply") or ""
        results.append((row, reply))
        print(f"\n#{i} [{row['topic']}/{row['sentiment']}] review_id={row['review_id']}")
        print("Prompt: ", row["prompt"])
        print("Ideal : ", row["ideal_response"])
        print("Model : ", reply)
    return results

if __name__ == "__main__":
    run_eval(k_per_topic=2)  # 2 × each topic = 10 total
