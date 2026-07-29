def format_examples(rows) -> str:
    if not rows:
        return "Example:\nUser: My support was great.\nAgent: Thanks for the kind words—happy to help!"
    return "\n\n".join(
        f"Example:\nUser: {r['prompt']}\nAgent: {r['ideal_response']}"
        for r in rows
    )
