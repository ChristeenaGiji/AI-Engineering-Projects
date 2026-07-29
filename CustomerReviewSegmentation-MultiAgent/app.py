## Customer Service AI — LangGraph + Groq + Supabase + Streamlit

An end-to-end, customer-support assistant built with LangGraph (for control flow), Groq LLMs (for classification + response), Supabase/Postgres (for few-shot examples & logging), and Streamlit (for a simple UI).

* The LangGraph pipeline classifies each message (sentiment, frustration, churn risk, topic), optionally pulls few-shot         examples from Postgres, decides to recommend or escalate, logs, and produces a final reply. 

* Postgres helper functions fetch examples by topic or topic+sentiment to drive style and grounding.

## Quick start

# 1) Python 3.11 recommended
python -m venv .venv311
# Windows PowerShell
. .venv311/Scripts/Activate.ps1
# macOS/Linux
source .venv311/bin/activate

# 2) Install deps
pip install -r requirements.txt

# 3) Add a .env at the repo root (see below)

# 4) (Optional) Seed Supabase/Postgres with demo data
python bootstrap_supabase_reviews.py
python run_eval.py
python make_dummy_review.py

# 5) Run the Streamlit app
streamlit run app.py

## .env template

# Groq
GROQ_API_KEY=sk-...
# Postgres / Supabase (optional for DB-backed few-shots)
+ PGHOST=aws-...pooler.supabase.com
+ PGPORT=5432
+ PGDATABASE=postgres
+ PGUSER=postgres.XXXXXXXXXXXX
+ PGPASSWORD=XXXXXXXXXXXX
+ PGSSLMODE=require


Tip — virtual env: If you have multiple venvs, activate the 3.11 one explicitly
Windows: . .venv311/Scripts/Activate.ps1 • macOS/Linux: source .venv311/bin/activate

## What’s inside
1) LangGraph pipeline

# Nodes (in order):

* sentiment – calls Groq to classify sentiment, frustration_level, churn_risk, topic and stores them on state. Robust JSON extraction avoids parse failures. 
* churn_ml – a tiny heuristic “model” that adds a churn score. 
* aggregate – combines LLM & heuristic into a final churn label. Routes to… 
* recommend or escalate – simple business rules (e.g., negative streaks, high churn). 
* sql_log – a hook to log telemetry/output. 
* response – pulls few-shots from DB by topic and composes the final reply via Groq. 

# You can change Groq model/temperature programmatically (a helper is provided to reset the global LLM used by graph nodes). 

2) Few-shot retrieval (Postgres)

Two helpers are provided:

+ get_examples_by_topic_pg(topic: str, n: int = 3)
+ get_examples_by_topic_sentiment_pg(topic: str, sentiment: str, n: int = 3)

Both use RealDictCursor and parameterized SQL to return prompt, ideal_response rows for the UI/graph. 

# Running the app

The Streamlit UI (in app.py) lets you:

* Filter a sample from the reviews table.
* Select a row (it supplies the dataset prompt, topic, sentiment to the graph).
* Choose variants and temperature.
* Generate 1–N response variants.
* Optionally save the model reply back to Postgres.

## Data model

Minimum columns expected in public.reviews:

review_id (uuid/text) | topic | sentiment | rating | author_name | prompt | ideal_response | created_at

The bootstrap script seeds this table with demo rows so you can test the end-to-end flow quickly.

# Configuration notes

# Groq model
The default LLM in the graph is set in customer_service_langgraph.py. If you see an error like “model decommissioned”, switch to a current model (e.g., llama-3.1-8b-instant) in the file (and/or use the provided setter to change it at runtime). 

# SSL & Supabase
Supabase’s pooled Postgres requires SSL. Keep PGSSLMODE=require in your .env. The Postgres helpers already pass through that value. 

# How it works (high-level)
+ User message arrives.
+ Classify → produce a state with fields like sentiment, topic, churn_risk, etc.
+ Run churn_ml and aggregate features/signals.
+ Route based on the state:
++ If high churn risk / severe issue → Escalate.
++ Otherwise → Recommend a direct reply.
+ Retrieve few-shots from Postgres (filtered by topic).

+ Generate response using the few-shots + tone rules.

+ Return the final concise reply to the user.

+ Log the run to SQL (e.g., public.model_outputs) for evaluation & traceability.

+ Classification prompt is strict JSON; a robust extractor cleans up common model quirks (quotes, trailing commas, etc.). 
+ Final response prepends few-shots fetched by topic so the tone and content stay on-brand per channel. 
 
# Troubleshooting

* “model decommissioned / invalid_request_error”: Update model_name in customer_service_langgraph.py to a currently supported Groq model and restart the app. 
* psycopg2.OperationalError: server does not support SSL: ensure PGSSLMODE=require and that you’re using the pooled host from Supabase (the ...pooler.supabase.com endpoint). 
* tuple index out of range in DB layer: usually means query parameter placeholders don’t match the tuple provided. The helpers here use correct parameterization ((topic, int(n)) and (topic, sentiment, int(n))). 
* Streamlit shows only one variant: ensure you pass n_variants/temperature into the graph (the app supports both).
* JSON parse errors: the project includes a defensive JSON extractor—use the built-in one from customer_service_langgraph.py to wrap any new classification prompts. 

# Extending

* Replace the churn heuristic with a real model (lightweight scikit or remote API).
* Add Row Level Security (RLS) policies if you expose model_outputs or reviews via PostgREST.
* Log to a model_outputs table in sql_log and build a Streamlit page to review & A/B test replies. 

# Repo map
+ app.py                        # Streamlit UI (sliders, variants, save-to-DB)
+ customer_service_langgraph.py # All LangGraph nodes + robust JSON extractor + LLM config :contentReference[oaicite:20]{index=20}
+ db_utils_pg.py                # Postgres helpers: few-shot retrieval by topic/sentiment :contentReference[oaicite:21]{index=21}
+ bootstrap_supabase_reviews.py # Seed script for demo data (reviews)
+ requirements.txt              # Python dependencies
