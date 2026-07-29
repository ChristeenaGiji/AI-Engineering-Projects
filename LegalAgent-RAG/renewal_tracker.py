# agents/chatbot_agent.py

import os
from dotenv import load_dotenv
load_dotenv()

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA
from langchain.docstore.document import Document

class ChatbotAgent:
    def __init__(self, db_path: str = "vectorstore/full_contract_db", k: int = 5):
        self.k = k

        # Load embedding model
        self.embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

        # Load Chroma vector DB
        if not os.path.exists(db_path) or not os.listdir(db_path):
            raise ValueError(f"❌ Vectorstore at '{db_path}' is empty or missing. Please run PolicyExtractorAgent first.")

        self.vector_db = Chroma(
            persist_directory=db_path,
            embedding_function=self.embedding_model
        )

        # Set up retriever
        self.retriever = self.vector_db.as_retriever(
            search_type="similarity",
            search_kwargs={"k": self.k}
        )

        # Load LLM
        self.llm = ChatGroq(model="llama3-70b-8192")

        # Setup QA chain
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            retriever=self.retriever,
            chain_type="stuff",
            return_source_documents=True
        )

    def run(self, question: str) -> dict:
        result = self.qa_chain(question)

        sources = [
            doc.page_content[:300] for doc in result.get("source_documents", [])
            if isinstance(doc, Document)
        ]

        return {
            "answer": result.get("result", "Sorry, I couldn't find an answer."),
            "sources": sources if sources else ["No relevant sources found."]
        }
