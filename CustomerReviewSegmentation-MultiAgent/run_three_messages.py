# run_eval.py
import os
import random
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Use your compiled graph + state dataclass
from customer_service_langgraph import EXECUTOR, ChatState

load_dotenv(".env", override=True)

TOPICS = ["support", "billing", "delivery", "product", "app"]  # adjust to match your data

def _conn():
    return psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        sslmode=os.getenv("PGSSLMODE", "require"),
    )

def _ensure_table(cur):
    cur.execute("""
        create table if not exists public.model_outputs (
            id bigserial primary key,
            review_id uuid,
            topic text,
            sentiment text,
            prompt text,
            ideal_response text,
            model_reply text,
            created_at timestamptz default now()
        )
    """)

def _fetch_k_per_topic(cur, k_per_topic: int = 2):
    rows = []
    for t in TOPICS:
        cur.execute("""
            select review_id, topic, sentiment, prompt, ideal_response
            from public.reviews
            where topic = %s
            order by random()
            limit %s
        """, (t, k_per_topic))
        rows.extend(cur.fetchall())
    random.shuffle(rows)
    return rows

def run_eval(k_per_topic: int = 2):
    with _conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        _ensure_table(cur)

        tests = _fetch_k_per_topic(cur, k_per_topic)
        print(f"Running eval on {len(tests)} rows…")

        for i, row in enumerate(tests, 1):
            # Run your graph
            state = ChatState(messages=[row["prompt"]], topic=row["topic"])
            out = EXECUTOR.invoke(state)
            reply = out.get("final_reply") or ""

            # Pretty print
            print(f"\n#{i} [{row['topic']}/{row['sentiment']}] review_id={row['review_id']}")
            print("Prompt:", row["prompt"])
            print("Ideal :", row["ideal_response"])
            print("Model :", reply)

            # INSERT happens **here**, inside the loop, where `row` exists
            cur.execute("""
                insert into public.model_outputs
                  (review_id, topic, sentiment, prompt, ideal_response, model_reply)
                values (%s, %s, %s, %s, %s, %s)
            """, (
                row["review_id"], row["topic"], row["sentiment"],
                row["prompt"], row["ideal_response"], reply
            ))

if __name__ == "__main__":
    run_eval(k_per_topic=2)
