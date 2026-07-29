import os
from dotenv import load_dotenv
load_dotenv(".env", override=True)
print({k: os.getenv(k) for k in ["PGHOST","PGUSER","PGPORT","PGSSLMODE"]})
