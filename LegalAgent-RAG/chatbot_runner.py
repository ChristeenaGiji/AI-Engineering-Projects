import os
import streamlit as st
import tempfile

from main import app  # Your LangGraph app
from my_agents.chatbot_agent import ChatbotAgent

st.set_page_config(page_title="📄 Legal Contract Analyzer", layout="wide")
st.title("📄 Legal Contract Analyzer")

uploaded_file = st.file_uploader("Upload your contract (PDF only)", type=["pdf"])

# Use session_state to keep chatbot agent alive during session
if "chatbot_agent" not in st.session_state:
    st.session_state.chatbot_agent = None

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    st.success("✅ Contract uploaded successfully!")

    if st.button("Run Analysis"):
        with st.spinner("Running LangGraph pipeline..."):
            try:
                result = app.invoke({"file_path": tmp_path})

                st.subheader("📆 Extracted Dates")
                st.json(result.get("dates_extracted", "Not Found"))

                st.subheader("📋 Extracted Clauses")
                st.json(result.get("clauses_extracted", "Not Found"))

                st.subheader("👥 Parties Involved")
                st.write(result.get("parties_extracted", "Not Found"))

                st.subheader("⏳ Renewal Status")
                st.json(result.get("renewal_status", "Not Found"))

                st.subheader("✅ Compliance Check Report")
                st.json(result.get("compliance_report", "Not Found"))

                st.subheader("⚠️ Risk Score")
                st.json(result.get("risk_score", "Not Found"))

                st.subheader("📝 Summary")
                st.write(result.get("summary", "Not Found"))

                # Initialize chatbot agent once analysis is done
                st.session_state.chatbot_agent = ChatbotAgent(db_path="vectorstore/full_contract_db")

                st.success("Chatbot is ready! Ask questions below.")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    # Clean up temp file
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

# Show chatbot interface only if chatbot agent is initialized
if st.session_state.chatbot_agent:
    st.markdown("---")
    st.subheader("🤖 Legal Contract Chatbot")

    question = st.text_input("Ask a question about the contract:")

    if question:
        with st.spinner("Thinking..."):
            response = st.session_state.chatbot_agent.run(question)

        st.markdown(f"**Answer:** {response['answer']}")
        st.markdown("**Sources:**")
        for i, src in enumerate(response["sources"], 1):
            st.markdown(f"{i}. {src[:300]}...")
