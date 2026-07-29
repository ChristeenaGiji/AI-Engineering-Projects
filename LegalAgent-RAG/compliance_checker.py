from db.supabase_client import get_supabase_client
import re
supabase = get_supabase_client()

def save_contract_data(file_name, topic, dates, clauses, parties):
    # === 1. Check if contract already exists ===
    existing = supabase.table("contracts").select("id").eq("file_name", file_name).execute()

    if existing.data:
        contract_id = existing.data[0]["id"]
        print(f"🔁 Existing contract found with ID {contract_id}. Deleting old records...")

        # Delete related data first (child tables)
        supabase.table("contract_clauses").delete().eq("contract_id", contract_id).execute()
        supabase.table("contract_dates").delete().eq("contract_id", contract_id).execute()
        supabase.table("contract_parties").delete().eq("contract_id", contract_id).execute()
        supabase.table("contracts").delete().eq("id", contract_id).execute()

        print("🗑️ Old records deleted.")

    # === 2. Insert into contracts table ===
    contract_resp = supabase.table("contracts").insert({
        "file_name": file_name,
        "topic": topic
    }).execute()

    contract_id = contract_resp.data[0]['id']

    # === 3. Insert dates ===
    if dates:
        supabase.table("contract_dates").insert({
            "contract_id": contract_id,
            "start_date": dates.get("start_date"),
            "end_date": dates.get("end_date"),
            "renewal_terms": dates.get("renewal_terms")
        }).execute()

    # === 4. Insert clauses ===
    for title, summary in clauses.items():
        supabase.table("contract_clauses").insert({
            "contract_id": contract_id,
            "clause_title": title,
            "clause_summary": summary
        }).execute()

    # === 5. Insert parties (supports: • Role: Name - Description format) ===
    for line in parties.split("\n"):
        line = line.strip()
        if re.match(r"^[\*\-•]\s+\*?\*?.+?:", line):

            try:
                print(f"🔎 Raw party line: '{line}'")

                # Remove the bullet point and trim
                line = line.lstrip("•").strip()

                # Split into role and the remaining part
                if ":" not in line:
                    print(f"⚠️ Skipping line without ':' -> {line}")
                    continue

                role, rest = line.split(":", 1)
                role = role.strip()

                # Split into name and optional description
                if " - " in rest:
                    name, description = rest.split(" - ", 1)
                else:
                    name = rest.strip()
                    description = "Not specified"

                name = name.strip()
                description = description.strip()

                print(f"👉 Parsed party line → role: {role}, name: {name}, description: {description}")

                # Insert into Supabase
                response = supabase.table("contract_parties").insert({
                    "contract_id": contract_id,
                    "party_role": role,
                    "party_name": name,
                    "party_description": description
                }).execute()

                if hasattr(response, "error") and response.error:
                    print(f"❌ Insert error: {response.error}")

            except Exception as e:
                print(f"❌ Error parsing/inserting party line: '{line}' → {e}")
                continue


    print("✅ Contract data saved to Supabase.")
