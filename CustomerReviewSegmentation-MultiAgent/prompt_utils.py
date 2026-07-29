# make_dummy_reviews.py
# Generates a customer-reviews style dataset with topic + sentiment
# and a sentiment-aware "prompt" for your chat model.

import os
import random
import uuid
from datetime import datetime, timedelta

import pandas as pd

# ---------- Tunables ----------
# total rows (can also set via env: DATASET_N=2000)
N = int(os.getenv("DATASET_N", "1000"))
# optional reproducibility
SEED = os.getenv("DATASET_SEED")
if SEED is not None:
    random.seed(int(SEED))

topics = ["support", "delivery", "billing", "product", "app"]
sentiments = ["positive", "neutral", "negative"]
states = ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT"]
devices = ["Android", "iOS", "Web", "Desktop"]

# Tone-specific customer prompts by topic & sentiment
PROMPT_TEMPLATES = {
    "support": {
        "positive": "Customer: thanks for the quick help—one last question about my support case.",
        "neutral":  "Customer: support issue details…",
        "negative": "Customer: I'm frustrated—my ticket has been open for days with no update.",
    },
    "app": {
        "positive": "Customer: loving the app overall—just confirming how to use a feature.",
        "neutral":  "Customer: app issue details…",
        "negative": "Customer: the app keeps crashing and I'm losing work.",
    },
    "delivery": {
        "positive": "Customer: delivery arrived early—just checking the status page accuracy.",
        "neutral":  "Customer: delivery issue details…",
        "negative": "Customer: delivery is delayed again and I need this urgently.",
    },
    "billing": {
        "positive": "Customer: billing looks correct—could you clarify one line item?",
        "neutral":  "Customer: billing issue details…",
        "negative": "Customer: I was charged twice and need a refund ASAP.",
    },
    "product": {
        "positive": "Customer: product works great—question about an accessory.",
        "neutral":  "Customer: product issue details…",
        "negative": "Customer: product arrived damaged and I'm very unhappy.",
    },
}

# Optional: vary "ideal_response" tone by sentiment
IDEAL_RESPONSE = {
    "positive": "Agent: Appreciate the kind words! Here’s a quick next step and where to find more help…",
    "neutral":  "Agent: Thanks for reaching out—here’s what we’ll do next…",
    "negative": "Agent: I’m sorry for the trouble. Here’s what I’ll do immediately and when to expect an update…",
}

# ---------- Generate ----------
rows = []
for i in range(N):
    s = random.choice(sentiments)
    t = random.choice(topics)

    # simple rating derived from sentiment
    if s == "positive":
        rating = random.choice([4, 5])
    elif s == "neutral":
        rating = 3
    else:
        rating = random.choice([1, 2])

    rows.append(
        {
            "review_id": str(uuid.uuid4()),
            "platform": "synthetic",
            "store": "Demo Store",
            "author_name": f"User{i+1}",
            "author_location": random.choice(states),
            "device": random.choice(devices),
            "rating": rating,
            "review_text": f"This is a {s} review about {t}.",
            "topic": t,
            "sentiment": s,
            "frustration_level": "low" if s == "positive" else random.choice(["medium", "high"]),
            "churn_risk": "unlikely" if s == "positive" else ("possible" if s == "neutral" else "likely"),
            "thumbs_up_count": random.randint(0, 50),
            "created_at": (datetime.utcnow() - timedelta(days=random.randint(0, 365))).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "prompt": PROMPT_TEMPLATES[t][s],
            "ideal_response": IDEAL_RESPONSE[s],
            "source_disclaimer": "synthetic dataset for testing",
        }
    )

df = pd.DataFrame(rows)

out = "google_reviews_dummy_mixed_chat_dataset.csv"
df.to_csv(out, index=False)
print(f"Wrote: {out} | rows: {len(df)}")
print("Preview:")
print(df.head(3)[["topic", "sentiment", "prompt", "ideal_response"]])
