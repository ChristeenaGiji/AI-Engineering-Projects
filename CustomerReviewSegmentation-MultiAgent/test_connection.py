# run_three_messages.py
from customer_service_langgraph import EXECUTOR, ChatState

tests = [
    ("negative", "I’m really upset—my last ticket sat for days with no update."),
    ("neutral",  "Can you check the status of my order? Not urgent."),
    ("positive", "Thanks for the help earlier—everything works perfectly now!"),
]

for label, text in tests:
    state = ChatState(messages=[text])
    out = EXECUTOR.invoke(state)
    print(f"\n== {label.upper()} ==")
    print("User:", text)
    print("Bot :", out.get("final_reply", ""))
