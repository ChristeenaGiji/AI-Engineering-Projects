# summarizer_agent.py

import os
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

class SummarizerAgent:
    def __init__(self, base_dir: str = "./vectorstore"):
        self.base_dir = base_dir
        self.embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en")
        self.llm = ChatGroq(model="llama3-70b-8192")

    def _load_text_from_db(self, db_name: str) -> str:
        path = os.path.join(self.base_dir, db_name)
        if not os.path.exists(path):
            print(f" Vector DB not found: {db_name}")
            return ""

        retriever = Chroma(persist_directory=path, embedding_function=self.embeddings).as_retriever(search_kwargs={"k": 5})
        docs = retriever.get_relevant_documents("summary")
        return "\n".join([doc.page_content for doc in docs])

    def run(self) -> str:
        print(" Running Summarizer Agent...")

        dates_text = self._load_text_from_db("dates_db")
        clauses_text = self._load_text_from_db("clauses_db")
        parties_text = self._load_text_from_db("parties_db")

        combined_text = f"""
        Key Dates:\n{dates_text}

        Key Clauses:\n{clauses_text}

        Involved Parties:\n{parties_text}
        """

        prompt = PromptTemplate.from_template("""
        You are a legal assistant. Provide a clear and concise executive summary of this contract based on the extracted information.

        Include:
        - Duration (start and end dates)
        - Key obligations
        - Parties involved
        - Any critical missing clauses or risks

        {summary_input}

        Return a paragraph summary.
        """)

        chain = prompt | self.llm
        response = chain.invoke({"summary_input": combined_text})

        print("\n Generated Summary:\n")
        print(response.content)

        return response.content
