# main.py
import json
import os



from langgraph.graph import StateGraph, END, START
from typing import TypedDict, Optional, Dict, Union

from my_agents.policy_extractor_agent import PolicyExtractorAgent
from my_agents.renewal_tracker import RenewalTrackerAgent
from my_agents.compliance_checker import ComplianceCheckerAgent
from my_agents.risk_scorer import RiskScorerAgent 
from my_agents.summarizer_agent import SummarizerAgent 
from utils import clear_local_vectorstores

# Clear these local DBs on each run
vectorstore_dirs = [
    "vectorstore/full_contract_db",
    "vectorstore/parties_db",
    "vectorstore/dates_db",
    "vectorstore/clauses_db"
]

clear_local_vectorstores(vectorstore_dirs)


from db.supabase_writer import save_contract_data

from my_agents.chatbot_agent import ChatbotAgent  

# === Define the shared state schema ===
class ContractState(TypedDict, total=False):
    file_path: str
    dates_extracted: Union[str, Dict[str, str]]
    # clauses_extracted: Optional[str]
    clauses_extracted: Optional[Dict[str, str]]
    parties_extracted: Optional[str]
    renewal_status: Optional[Dict[str, Union[str, bool, int]]]
    
    compliance_report: Optional[Dict[str, str]]  # compliance_report is a dict now
    risk_score: Optional[Dict[str, Union[int, float]]]  # New field for risk scoring results
    summary: Optional[str]
    topic: Optional[str] 

    user_question: Optional[str]           # 🔹 Added for chatbot input
    chatbot_answer: Optional[str]          # 🔹 Added for chatbot output



# === Node Function: Policy Extractor ===
def run_policy_extraction(state: ContractState) -> ContractState:
    print(" Running Policy Extractor Agent...")

    extractor = PolicyExtractorAgent(file_path=state["file_path"])
    extracted_results = extractor.run_full_pipeline()

    print("\n--- Extracted Dates ---")
    print(json.dumps(extracted_results.get("dates", {}), indent=2))

    print("\n--- Extracted Clauses ---")
    print(extracted_results.get("clauses", ""))

    print("\n--- Extracted Parties ---")
    print(extracted_results.get("parties", ""))

    # Save the clauses retriever for compliance check later
    clauses_retriever = extractor.get_clauses_retriever()
    print("\n--- Detected Topic ---")                
    print(extracted_results.get("topic", "Unknown"))

    save_contract_data(
    file_name=os.path.basename(state["file_path"]),
    topic=extracted_results.get("topic", "Unknown"),
    dates=extracted_results.get("dates", {}),
    clauses=extracted_results.get("clauses", {}),
    parties=extracted_results.get("parties", "")
    )

    return {
        **state,
        "dates_extracted": extracted_results.get("dates"),
        "clauses_extracted": extracted_results.get("clauses"),
        "parties_extracted": extracted_results.get("parties"),
        "topic": extracted_results.get("topic"),
        "user_clauses_retriever": clauses_retriever
        

    }

# === Node Function: Renewal Tracker ===
def run_renewal_tracker(state: ContractState) -> ContractState:
    print(" Running Renewal Tracker Agent...")

    structured_dates = state.get("dates_extracted", {})
    if not structured_dates:
        print(" No dates found, skipping renewal check.")
        return {
            **state,
            "renewal_status": {
                "expiry_date": "Not specified",
                "days_remaining": -1,
                "renewal_terms": "Not specified",
                "expiring_soon": False
            }
        }

    tracker = RenewalTrackerAgent()
    result = tracker.process_dates(structured_dates)

    print("\n Renewal Status:")
    print(json.dumps(result, indent=2))

    return {
        **state,
        "renewal_status": result
    }

# === Node Function: Compliance Checker ===
# def run_compliance_check(state: ContractState) -> ContractState:
#     print(" Running Compliance Checker Agent...")

#     checker = ComplianceCheckerAgent()
#     result = checker.run()

#     print("\n Compliance Report:")
#     for clause, status in result.items():
#         print(f"{clause}: {status}")

#     return {
#         **state,
#         "compliance_report": result
#     }


def run_compliance_check(state: ContractState) -> ContractState:
    print(" Running Compliance Checker Agent...")

    clauses = state.get("clauses_extracted", None)
    checker = ComplianceCheckerAgent(clauses=clauses)
    result = checker.run()

    print("\n Compliance Report:")
    for clause, status in result.items():
        print(f"{clause}: {status}")

    return {
        **state,
        "compliance_report": result
    }


    # checker = ComplianceCheckerAgent(clauses=clauses)
    # result = checker.run()

    # print("\n Compliance Report:")
    # for clause, status in result.items():
    #     print(f"{clause}: {status}")

    # return {
    #     **state,
    #     "compliance_report": result
    # }


# === Node Function: Risk Scorer ===
def run_risk_scoring(state: ContractState) -> ContractState:
    print(" Running Risk Scorer Agent...")

    compliance_report = state.get("compliance_report")
    if not compliance_report:
        print(" No compliance report found, skipping risk scoring.")
        return state

    scorer = RiskScorerAgent(compliance_report)
    risk_results = scorer.calculate_score()

    print("\n Risk Score Results:")
    print(risk_results)

    return {
        **state,
        "risk_score": risk_results
    }

# === Node: Summarizer Agent ===
def run_summary(state: ContractState) -> ContractState:
    print(" Running Summarizer Agent...")
    summarizer = SummarizerAgent()
    summary = summarizer.run()

    print("\n Contract Summary:")
    print(summary)

    return {
        **state,
        "summary": summary
    }






# === LangGraph Setup ===
workflow = StateGraph(ContractState)
workflow.add_node("extract_policy", run_policy_extraction)
workflow.add_node("track_renewal", run_renewal_tracker)
workflow.add_node("check_compliance", run_compliance_check)
workflow.add_node("score_risk", run_risk_scoring) 
workflow.add_node("summarize_contract", run_summary)


workflow.set_entry_point("extract_policy")
workflow.add_edge("extract_policy", "track_renewal")
workflow.add_edge("track_renewal", "check_compliance")
workflow.add_edge("check_compliance", "score_risk")  
workflow.add_edge("score_risk", "summarize_contract")
workflow.set_finish_point("summarize_contract")



app = workflow.compile()



# === Run with Input File ===
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise ValueError("Please provide a file path as an argument.")
    
    file_path = sys.argv[1]

    inputs = {
        "file_path": file_path
    }

    final_state = app.invoke(inputs)

   


    # print("\n Final State:")
    # for k, v in final_state.items():
    #     print(f"{k}: {v}")
