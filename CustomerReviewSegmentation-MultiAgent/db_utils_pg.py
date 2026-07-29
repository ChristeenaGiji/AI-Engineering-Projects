
"""
customer_service_langgraph.py

What this does
--------------
- Classifies each incoming message (sentiment, frustration, churn_risk, topic)
  using Groq LLM and a robust JSON extractor (no more JSON parse crashes).
- Optionally pulls few-shot examples from Postgres/Supabase (if db_utils_pg.py exists).
- Aggregates churn risk with a simple ML heuristic.
- Routes to escalation or recommendation, logs, then produces a final reply.

Env you need
------------
- GROQ_API_KEY=...
- (Optional for examples) PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD, PGSSLMODE=require
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph

# ---------- Config ----------
DEBUG = True

def dbg(*a, **k):
    if DEBUG:
        print(*a, **k)

# Load .env
load_dotenv()

# ---------- LLM ----------
llm = ChatGroq(
    model_name="llama3-8b-8192",
    temperature=0.7,
    api_key=os.getenv("GROQ_API_KEY"),
)

def set_llm_temperature(t: float):
    """Called by the Streamlit app to change sampling temperature."""
    import os
    from langchain_groq import ChatGroq
    t = max(0.0, min(float(t), 1.5))  # clamp for safety
    # Reassign the global LLM used by the graph’s nodes
    globals()["llm"] = ChatGroq(
        model_name="llama-3.1-8b-instant",
        temperature=t,
        api_key=os.getenv("GROQ_API_KEY"),
    )


# ---------- Optional few-shot examples from DB ----------
try:
    # Provide get_examples_by_topic_pg(topic: str, n: int) and (optional) format_examples(rows)
    from db_utils_pg import get_examples_by_topic_pg  # type: ignore
    def format_examples(rows) -> str:
        if not rows:
            return (
                "Example:\n"
                "User: I had a billing issue but support helped.\n"
                "Agent: Thanks for letting us know—glad it’s sorted. If anything else pops up, "
                "reply here and we’ll jump on it."
            )
        return "\n\n".join(
            f"Example:\nUser: {r['prompt']}\nAgent: {r['ideal_response']}" for r in rows
        )
except Exception:
    dbg("db_utils_pg not found — running without DB few-shots.")
    def get_examples_by_topic_pg(_topic: str, n: int = 3):
        return []
    def format_examples(rows) -> str:
        return (
            "Example:\n"
            "User: My delivery was late.\n"
            "Agent: I’m sorry for the delay—that’s not the experience we want. I’ve checked your order "
            "and prioritised a replacement. You’ll get an update within 24 hours."
        )

# ---------- State ----------
@dataclass
class ChatState:
    messages: List[str]
    sentiment: Optional[str] = None
    frustration_level: Optional[str] = None
    churn_intention: Optional[str] = None
    churn_risk_llm: Optional[str] = None
    churn_score_ml: Optional[float] = None
    churn_label: Optional[str] = None
    product_recs: List[str] = field(default_factory=list)
    escalate: bool = False
    negative_streak: int = 0
    final_reply: Optional[str] = None
    meta: Dict[str, Dict] = field(default_factory=dict)
    session_id: Optional[str] = None
    chat_timestamp: Optional[str] = None
    topic: Optional[str] = None  # normalized topic used for examples

# ---------- Robust JSON extractor ----------
JSON_LIKE = re.compile(r"\{.*\}", re.S)

def extract_json(text: str) -> Dict:
    """
    Extract the first JSON object from text and parse it robustly.
    Handles:
      - leading/trailing commentary
      - single quotes -> double quotes
      - stray trailing commas
    """
    if not isinstance(text, str):
        raise ValueError("LLM returned non-string content")

    # 1) Find the first {...} block
    m = JSON_LIKE.search(text)
    candidate = m.group(0) if m else text

    # 2) Try strict JSON first
    try:
        return json.loads(candidate)
    except Exception:
        pass

    # 3) Normalise common pitfalls
    cleaned = candidate.strip()

    # Replace smart quotes
    cleaned = cleaned.replace("“", '"').replace("”", '"').replace("’", "'")

    # Single -> double quotes (naive but effective for simple dicts)
    if cleaned.count('"') == 0 and cleaned.count("'") >= 2:
        cleaned = cleaned.replace("'", '"')

    # Remove trailing commas before } or ]
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)

    # Lowercase booleans/null variants if present (rare)
    cleaned = cleaned.replace("None", "null").replace("True", "true").replace("False", "false")

    try:
        return json.loads(cleaned)
    except Exception as e:
        raise ValueError(f"Could not parse JSON from LLM output:\n{text[:600]}") from e

# ---------- Nodes ----------
def detect_sentiment(state: ChatState) -> ChatState:
    latest = (state.messages or [""])[-1]

    system = (
        "You are a strict classification agent. "
        "Return ONLY valid JSON, no prose. "
        'Schema: {"sentiment":"positive|neutral|negative",'
        '"frustration_level":"low|medium|high",'
        '"churn_risk":"likely|unlikely",'
        '"topic":"support|billing|delivery|product|app|other"}'
    )
    prompt = f"{system}\nCustomer: {latest}"

    dbg("🔍 Classification prompt:\n", prompt)
    resp = llm.invoke(prompt)
    raw = getattr(resp, "content", "") or ""
    dbg("📩 Raw LLM response:", repr(raw))

    parsed = extract_json(raw)
    dbg("✅ Parsed JSON:", parsed)

    state.sentiment = parsed.get("sentiment")
    state.frustration_level = parsed.get("frustration_level")
    state.churn_risk_llm = parsed.get("churn_risk")
    state.topic = (parsed.get("topic") or "support").strip().lower()
    if state.sentiment == "negative":
        state.negative_streak += 1
    return state

def ml_churn_predict(state: ChatState) -> ChatState:
    s = state.meta.get("structured", {})
    tenure = float(s.get("tenure", 0) or 0)
    monthly = float(s.get("monthly_charges", 0) or 0)

    # simple heuristic you can swap out for a real model
    score = (
        0.9 if (tenure < 3 and monthly > 100)
        else 0.7 if tenure < 6
        else 0.3
    )
    state.churn_score_ml = score
    return state

def aggregate_risk(state: ChatState) -> ChatState:
    if state.churn_risk_llm == "likely" or (state.churn_score_ml or 0) > 0.7:
        state.churn_label = "High Risk"
    else:
        state.churn_label = "Low/Medium"
    return state

def recommend_products(state: ChatState) -> ChatState:
    state.product_recs = ["iPhone 16 Pro", "Galaxy S25+", "Google Pixel 9 Pro"]
    return state

def escalate_if_needed(state: ChatState) -> ChatState:
    state.escalate = state.negative_streak >= 3 or state.churn_label == "High Risk"
    return state

def log_to_sql(state: ChatState) -> ChatState:
    # TODO: insert into your telemetry table
    return state

def final_response(state: ChatState) -> ChatState:
    # Pull a few-shot block (optional DB), to guide style/tone
    examples = get_examples_by_topic_pg(state.topic or "support", n=3)
    fewshot = format_examples(examples)

    # 👇 add this debug print (safe to keep behind a flag if you want)
    print(f"[few-shot topic={state.topic or 'support'}] {len(examples)} example(s) from Supabase")
    for i, e in enumerate(examples, 1):
        print(f"  {i}. prompt={e.get('prompt')!r}")
        print(f"     ideal_response={e.get('ideal_response')!r}")

    fewshot = format_examples(examples)
    ...


    sys = (
        "You are a concise, empathetic customer support agent. "
        "Reply in 60–120 words. If the customer is upset, acknowledge, apologise briefly, "
        "and give ONE concrete next step. Avoid bullets unless asked."
    )

    # Add dynamic hints based on route
    route_hint = (
        "Escalate to a senior specialist and set expectation for response time."
        if state.escalate else
        f"Optionally offer a helpful suggestion or relevant product: {', '.join(state.product_recs)}"
    )

    latest = (state.messages or [''])[ -1 ]
    user_block = (
        f"{fewshot}\n\n"
        f"Context:\n"
        f"- sentiment: {state.sentiment}, frustration: {state.frustration_level}, churn_label: {state.churn_label}\n"
        f"- guidance: {route_hint}\n\n"
        f"Customer said: {latest}\n"
        f"Write ONLY the reply."
    )

    resp = llm.invoke([{"role": "system", "content": sys}, {"role": "user", "content": user_block}])
    state.final_reply = (getattr(resp, "content", "") or "").strip() or "Thanks for contacting us!"
    return state

# ---------- Graph ----------
g = StateGraph(ChatState)
g.add_node("sentiment", detect_sentiment)
g.add_node("churn_ml", ml_churn_predict)
g.add_node("aggregate", aggregate_risk)
g.add_node("recommend", recommend_products)
g.add_node("escalate", escalate_if_needed)
g.add_node("sql_log", log_to_sql)
g.add_node("response", final_response)

g.add_edge("sentiment", "churn_ml")
g.add_edge("churn_ml", "aggregate")

def route_after_aggregate(state: ChatState) -> str:
    return "escalate" if (state.churn_label == "High Risk" or state.negative_streak >= 3) else "recommend"

g.add_conditional_edges("aggregate", route_after_aggregate, {"escalate": "escalate", "recommend": "recommend"})
g.add_edge("escalate", "sql_log")
g.add_edge("recommend", "sql_log")
g.add_edge("sql_log", "response")

g.set_entry_point("sentiment")
EXECUTOR = g.compile()

# ---------- Example run ----------
if __name__ == "__main__":
    sample = ChatState(
        messages=["I’m frustrated the last ticket sat for days with no update."],
        meta={"structured": {"tenure": 2, "monthly_charges": 120.0}},
    )
    out = EXECUTOR.invoke(sample)
    result = ChatState(**out)
    print("\n🤖 Chatbot reply:\n", result.final_reply)




