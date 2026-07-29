import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
ENV = HERE / ".env"

print("CWD:", Path.cwd())
print(".env path:", ENV)

if not ENV.exists():
    raise FileNotFoundError(f".env not found at {ENV}")

# Load .env sitting next to this file
load_dotenv(ENV, override=True)

from urllib.parse import urlparse
print("DB_URL:", os.getenv("DATABASE_URL"))
if os.getenv("DATABASE_URL"):
    print("DB_HOST:", urlparse(os.getenv("DATABASE_URL")).hostname)


# Option A: single DATABASE_URL (if you prefer one var)
db_url = os.getenv("DATABASE_URL")
if db_url:
    print("Using DATABASE_URL")
    conn = psycopg2.connect(db_url)

else:
    # Option B: separate PG* vars
    required = ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD", "PGSSLMODE"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing env vars: {missing}")

    print("Connecting to:",
          os.getenv("PGHOST"), os.getenv("PGPORT"),
          "db=", os.getenv("PGDATABASE"),
          "user=", os.getenv("PGUSER"),
          "sslmode=", os.getenv("PGSSLMODE"))

    conn = psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT"),
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        sslmode=os.getenv("PGSSLMODE"),
    )

with conn, conn.cursor() as cur:
    cur.execute("select version(), current_database(), current_user, inet_server_addr(), now()")
    v, db, user, host, now = cur.fetchone()
    print("✔ Connected")
    print(" version:", v)
    print(" database:", db)
    print(" user:", user)
    print(" server_ip:", host)
    print(" now:", now)

print("Connection closed.")
