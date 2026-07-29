# import os
# import json
# from langchain.schema import Document
# from langchain_community.vectorstores import Chroma
# from langchain_huggingface import HuggingFaceEmbeddings


# class ComplianceCheckerAgent:
#     def __init__(self, base_path="./vectorstore"):
#         self.base_path = base_path
#         self.embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en")

#     def load_extracted_clauses(self) -> dict:
#         """
#         Load clause dictionary JSON from vectorstore and parse it.
#         """
#         clause_db_path = os.path.join(self.base_path, "clauses_db")
#         vectorstore = Chroma(
#             persist_directory=clause_db_path,
#             embedding_function=self.embeddings
#         )
#         docs = vectorstore.similarity_search("all extracted clauses", k=1)

#         if not docs:
#             print("❌ No clause document found in vectorstore.")
#             return {}

#         content = docs[0].page_content
#         try:
#             clause_dict = json.loads(content)
#             return clause_dict
#         except json.JSONDecodeError:
#             print("❌ Failed to parse clause document as JSON.")
#             return {}

#     def check_clause_compliance(self, clause_dict: dict) -> dict:
#         """
#         Check if each clause is present or marked as 'Not specified'.
#         """
#         results = {}
#         for clause, value in clause_dict.items():
#             if not value or value.strip().lower() == "not specified":
#                 results[clause] = "❌ Missing"
#             else:
#                 results[clause] = "✅ Present"
#         return results

#     def run(self) -> dict:
#         """
#         Main function to load, check, and return clause compliance.
#         """
#         print("🧾 Running Compliance Checker Agent...")
#         clause_dict = self.load_extracted_clauses()
#         if not clause_dict:
#             return {"status": "error", "message": "No clause data found."}

#         compliance_results = self.check_clause_compliance(clause_dict)

#         print("\n--- Compliance Report ---")
#         for clause, status in compliance_results.items():
#             print(f"{clause}: {status}")

#         return compliance_results

# # import os
# # import json
# # from langchain.schema import Document
# # from langchain_community.vectorstores import Chroma
# # from langchain_huggingface import HuggingFaceEmbeddings

# # class ComplianceCheckerAgent:
# #     # Updated: accept clauses dict optionally in constructor
# #     def __init__(self, base_path="./vectorstore", clauses: dict = None):  # <<< UPDATED
# #         self.base_path = base_path
# #         self.embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en")
# #         self.clauses = clauses  # <<< NEW: store clauses passed in

# #     # Removed: load_extracted_clauses method is no longer needed if clauses are passed directly
# #     # You can keep it if you want backward compatibility

# #     def check_clause_compliance(self, clause_dict: dict) -> dict:
# #         """
# #         Check if each clause is present or marked as 'Not specified'.
# #         """
# #         results = {}
# #         for clause, value in clause_dict.items():
# #             if not value or value.strip().lower() == "not specified":
# #                 results[clause] = "❌ Missing"
# #             else:
# #                 results[clause] = "✅ Present"
# #         return results

# #     # Updated run method to use passed clauses or fallback to loading (optional)
# #     def run(self) -> dict:
# #         """
# #         Main function to check and return clause compliance.
# #         """
# #         print("🧾 Running Compliance Checker Agent...")

# #         if self.clauses is None:
# #             # Optional fallback - load clauses if not passed (can remove if always passing)
# #             clause_dict = self.load_extracted_clauses()
# #         else:
# #             clause_dict = self.clauses  # <<< UPDATED: use passed clauses

# #         if not clause_dict:
# #             return {"status": "error", "message": "No clause data found."}

# #         compliance_results = self.check_clause_compliance(clause_dict)

# #         print("\n--- Compliance Report ---")
# #         for clause, status in compliance_results.items():
# #             print(f"{clause}: {status}")

# #         return compliance_results

import os
import json
from langchain.schema import Document
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

class ComplianceCheckerAgent:
    def __init__(self, base_path="./vectorstore", clauses: dict = None):  # <-- Added optional clauses param
        self.base_path = base_path
        self.embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en")
        self.clauses = clauses  # <-- Store passed clauses dict

    def load_extracted_clauses(self) -> dict:
        """
        Load clause dictionary JSON from vectorstore and parse it.
        """
        clause_db_path = os.path.join(self.base_path, "clauses_db")
        vectorstore = Chroma(
            persist_directory=clause_db_path,
            embedding_function=self.embeddings
        )
        docs = vectorstore.similarity_search("all extracted clauses", k=1)

        if not docs:
            print(" No clause document found in vectorstore.")
            return {}

        content = docs[0].page_content
        try:
            clause_dict = json.loads(content)
            return clause_dict
        except json.JSONDecodeError:
            print(" Failed to parse clause document as JSON.")
            return {}

    def check_clause_compliance(self, clause_dict: dict) -> dict:
        """
        Check if each clause is present or marked as 'Not specified'.
        """
        results = {}
        for clause, value in clause_dict.items():
            if not value or value.strip().lower() == "not specified":
                results[clause] = " Missing"
            else:
                results[clause] = " Present"
        return results

    def run(self) -> dict:
        """
        Main function to check and return clause compliance.
        """
        print(" Running Compliance Checker Agent...")

        # Use passed clauses if available, else load from vectorstore
        clause_dict = self.clauses if self.clauses is not None else self.load_extracted_clauses()

        if not clause_dict:
            return {"status": "error", "message": "No clause data found."}

        compliance_results = self.check_clause_compliance(clause_dict)

        print("\n--- Compliance Report ---")
        for clause, status in compliance_results.items():
            print(f"{clause}: {status}")

        return compliance_results
