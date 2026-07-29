# bootstrap_supabase_reviews.py
# ------------------------------------------------------------
# Creates the 'public.reviews' table in Supabase Postgres and
# loads your CSV dataset. Robust .env loading + clear debug.
# ------------------------------------------------------------

import os
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv, dotenv_values


# ---------- .env loading (fail fast) ----------
SCRIPT_DIR = Path(__file__).resolve().parent
ENV_PATH = SCRIPT_DIR / ".env"

print("CWD:", Path.cwd())
print(".env path:", ENV_PATH)

if not ENV_PATH.exists():
    raise FileNotFoundError(f".env not found at {ENV_PATH}. Put your Supabase creds here.")

# Peek keys (no secrets)
vals = dotenv_values(ENV_PATH)
print("Found keys in .env:", sorted(vals.keys()))

load_dotenv(dotenv_path=ENV_PATH, override=True)

REQUIRED = ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD", "PGSSLMODE"]
missing = [k for k in REQUIRED if not os.getenv(k)]
if missing:
    raise RuntimeError(f"Missing required env vars in .env: {missing}")

# Minimal debug (no secrets)
print("PGHOST:", os.getenv("PGHOST"))
print("PGUSER:", os.getenv("PGUSER"))

# CSV path (default file name if not set)
CSV_PATH = os.getenv("CSV_PATH", "google_reviews_dummy_mixed_chat_dataset.csv")


# ---------- DB DDL ----------
DDL = """
create table if not exists public.reviews (
  review_id uuid primary key,
  platform text,
  store text,
  author_name text,
  author_location text,
  device text,
  rating int,
  review_text text,
  topic text,
  sentiment text,
  frustration_level text,
  churn_risk text,
  thumbs_up_count int,
  created_at timestamp,
  prompt text,
  ideal_response text,
  source_disclaimer text
);

create index if not exists idx_reviews_topic on public.reviews(topic);
create index if not exists idx_reviews_created on public.reviews(created_at);
"""

COLS = [
    "review_id", "platform", "store", "author_name", "author_location", "device",
    "rating", "review_text", "topic", "sentiment", "frustration_level", "churn_risk",
    "thumbs_up_count", "created_at", "prompt", "ideal_response", "source_disclaimer"
]


# ---------- DB connect ----------
def connect():
    PGHOST = os.getenv("PGHOST")
    PGPORT = os.getenv("PGPORT", "5432")
    PGDATABASE = os.getenv("PGDATABASE", "postgres")
    PGUSER = os.getenv("PGUSER")
    PGPASSWORD = os.getenv("PGPASSWORD")
    PGSSLMODE = os.getenv("PGSSLMODE", "require")

    print(f"Connecting to {PGHOST}:{PGPORT} db={PGDATABASE} user={PGUSER} sslmode={PGSSLMODE}")
    return psycopg2.connect(
        host=PGHOST,
        port=PGPORT,
        dbname=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
        sslmode=PGSSLMODE,
    )


# ---------- main ----------
def main():
    print("\n# Connecting to Supabase Postgres…")
    with connect() as conn, conn.cursor() as cur:
        print("🛠  Creating table & indexes if needed…")
        cur.execute(DDL)
        conn.commit()

    csv_path = (Path(CSV_PATH) if Path(CSV_PATH).is_absolute() else SCRIPT_DIR / CSV_PATH)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found at {csv_path}")

    print(f"📥 Loading CSV: {csv_path}")
    df = pd.read_csv(csv_path)

    # Ensure required columns exist
    missing_cols = [c for c in COLS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"CSV is missing columns: {missing_cols}")

    # Convert created_at to string (ISO) if needed
    if pd.api.types.is_datetime64_any_dtype(df["created_at"]):
        df["created_at"] = df["created_at"].dt.strftime("%Y-%m-%d %H:%M:%S")

    records = [tuple(row[c] for c in COLS) for _, row in df.iterrows()]

    with connect() as conn, conn.cursor() as cur:
        print(f"⬆️ Inserting {len(records)} rows (duplicates by review_id skipped)…")
        execute_values(
            cur,
            f"""
            insert into public.reviews ({",".join(COLS)}) values %s
            on conflict (review_id) do nothing
            """,
            records,
            page_size=1000
        )
        conn.commit()

    print("\n✅ Done. Verify in Supabase SQL editor:")
    print("   select count(*) from public.reviews;")
    print("   select topic, count(*) from public.reviews group by 1 order by 2 desc;")


if __name__ == "__main__":
    main()
