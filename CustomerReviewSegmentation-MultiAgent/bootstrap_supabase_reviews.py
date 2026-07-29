# app.py
import os
from datetime import datetime
from pathlib import Path
import pandas as pd
import altair as alt
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# ---- Load env
load_dotenv(".env", override=True)

# ---- Import your LangGraph executor
try:
    # NOTE: requires set_llm_temperature helper in your graph file (see note above)
    from customer_service_langgraph import EXECUTOR, ChatState, set_llm_temperature
except Exception as e:
    EXECUTOR, ChatState, set_llm_temperature = None, None, lambda *_: None
    st.warning(
        "Could not import customer_service_langgraph.EXECUTOR. "
        "Generation will be disabled until this is importable."
    )
    st.exception(e)

# ---- DB helpers
def _conn():
    return psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        sslmode=os.getenv("PGSSLMODE", "require"),
    )

@st.cache_data(ttl=60)
def fetch_overview():
    sql = """
      with base as (
        select topic, sentiment from public.reviews
      )
      select topic, sentiment, count(*) as n
      from base
      group by 1,2
      order by 1,2;
    """
    with _conn() as c:
        df = pd.read_sql_query(sql, c)
    return df

@st.cache_data(ttl=60)
def fetch_sample(topic=None, sentiment=None, limit=50):
    where = []
    params = []
    if topic:
        where.append("topic = %s")
        params.append(topic)
    if sentiment:
        where.append("sentiment = %s")
        params.append(sentiment)
    where_sql = f"where {' and '.join(where)}" if where else ""

    sql = f"""
      select review_id, topic, sentiment, rating, author_name,
             prompt, ideal_response, created_at
      from public.reviews
      {where_sql}
      order by random()
      limit %s
    """
    params.append(limit)
    with _conn() as c:
        df = pd.read_sql_query(sql, c, params=params)
    return df

@st.cache_data(ttl=60)
def fetch_latest_outputs(limit=200):
    sql = """
      select mo.review_id, mo.topic, mo.sentiment,
             left(mo.prompt, 120) as prompt_preview,
             left(mo.model_reply, 200) as model_reply_preview,
             mo.created_at
      from public.model_outputs mo
      order by mo.created_at desc
      limit %s
    """
    with _conn() as c:
        df = pd.read_sql_query(sql, c, params=(limit,))
    return df

def insert_model_output(row, reply):
    sql = """
      create table if not exists public.model_outputs (
        id bigserial primary key,
        review_id uuid,
        topic text,
        sentiment text,
        prompt text,
        ideal_response text,
        model_reply text,
        created_at timestamptz default now()
      );
      insert into public.model_outputs
        (review_id, topic, sentiment, prompt, ideal_response, model_reply)
      values (%s, %s, %s, %s, %s, %s);
    """
    with _conn() as c, c.cursor() as cur:
        cur.execute(sql, (
            row["review_id"], row["topic"], row["sentiment"],
            row["prompt"], row["ideal_response"], reply
        ))
        c.commit()

# ---- UI
st.set_page_config(page_title="Customer Service – Model Dashboard", layout="wide")
st.title("📊 Customer Service – Model Dashboard")

with st.sidebar:
    st.header("Filters")
    topic = st.selectbox("Topic", options=[None, "support", "billing", "delivery", "product", "app"], index=0)
    sentiment = st.selectbox("Sentiment", options=[None, "positive", "neutral", "negative"], index=0)
    sample_n = st.slider("Sample size", 10, 200, 50, 10)
    st.caption("Tip: Set filters to focus the sample, then pick a row to generate a reply.")

# ---- KPIs & overview
ov = fetch_overview()
kpi_total = int(ov["n"].sum()) if not ov.empty else 0
kpi_topics = ov["topic"].nunique() if not ov.empty else 0
kpi_pos = int(ov.loc[ov["sentiment"]=="positive", "n"].sum()) if not ov.empty else 0
kpi_neg = int(ov.loc[ov["sentiment"]=="negative", "n"].sum()) if not ov.empty else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total reviews", f"{kpi_total:,}")
k2.metric("Topics", kpi_topics)
k3.metric("Positive", f"{kpi_pos:,}")
k4.metric("Negative", f"{kpi_neg:,}")

# stacked bar by topic/sentiment
if not ov.empty:
    chart = alt.Chart(ov).mark_bar().encode(
        x=alt.X("topic:N", title="Topic"),
        y=alt.Y("sum(n):Q", title="Count"),
        color=alt.Color("sentiment:N", sort=["negative","neutral","positive"]),
        tooltip=["topic","sentiment","n"]
    )
    st.altair_chart(chart, use_container_width=True)
else:
    st.info("No data found in public.reviews")

st.divider()

# ---- Sample table
st.subheader("Sample from dataset")
sample_df = fetch_sample(topic, sentiment, sample_n)
st.dataframe(sample_df, use_container_width=True, height=280)

# choose a row to generate on
if not sample_df.empty:
    ids = sample_df["review_id"].astype(str).tolist()
    chosen_id = st.selectbox("Choose a review_id to generate a reply", ids)
    row = sample_df.loc[sample_df["review_id"].astype(str) == chosen_id].iloc[0]

    st.markdown("**Prompt (customer message)**")
    st.write(row["prompt"])

    colA, colB = st.columns(2)
    with colA:
        st.markdown("**Ideal (from dataset)**")
        st.write(row["ideal_response"])
    
    with colB:
        st.markdown("**Model reply**")

        # controls for diversity
        n_variants = st.slider("Variants", 1, 5, 3)
        temp = st.slider("Temperature", 0.20, 1.50, 0.70, 0.05)

        gen_btn = st.button("Generate with LangGraph", type="primary", disabled=EXECUTOR is None)

        if gen_btn and EXECUTOR:
            st.info("Generating…")

            # Prefer the richer, more varied review text; fall back to prompt if missing
            text = (row.get("review_text") or row.get("prompt") or "").strip()

            # Let the graph sample with the UI temperature
            try:
                set_llm_temperature(temp)
            except Exception:
                # If helper isn't present in your graph, you can optionally pass via meta
                pass

            replies = []
            for _ in range(n_variants):
                state = ChatState(
                    messages=[text],
                    topic=row.get("topic"),
                    sentiment=row.get("sentiment"),
                    meta={"temperature": temp, "structured": {"rating": row.get("rating")}},
                )
                out = EXECUTOR.invoke(state)
                replies.append((out.get("final_reply") or "").strip())

            st.success("Done")

            # display them
            for i, r in enumerate(replies, 1):
                with st.expander(f"Variant {i}", expanded=(i == 1)):
                    st.write(r)

            save = st.checkbox("Save this model reply to Supabase")
            if save and replies:
                insert_model_output(row, replies[0])
                st.toast("Saved to public.model_outputs ✅")

st.divider()

# ---- Recent model outputs
st.subheader("Latest saved model outputs")
out_df = fetch_latest_outputs(200)
st.dataframe(out_df, use_container_width=True, height=260)
