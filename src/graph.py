from langgraph.graph import StateGraph, END

from src.state import ReviewState
from src.agents.style import style_reviewer
from src.agents.logic import logic_reviewer
from src.agents.security import security_reviewer
from src.agents.triage import triage_agent


def coordinator(state:ReviewState)->dict:
    return {}

def build_graph():
    graph = StateGraph(ReviewState)

    graph.add_node("coordinator", coordinator)
    graph.add_node("security", security_reviewer)
    graph.add_node("style", style_reviewer)
    graph.add_node("logic", logic_reviewer)
    graph.add_node("triage", triage_agent)

    graph.set_entry_point("coordinator")
    
    # fan-out: coordinator triggers all three reviewers in parallel
    graph.add_edge("coordinator", "security")
    graph.add_edge("coordinator", "style")
    graph.add_edge("coordinator", "logic")
    
    # fan-in: triage only runs once ALL three reviewers have finished
    graph.add_edge("security", "triage")
    graph.add_edge("style", "triage")
    graph.add_edge("logic", "triage")
    
    graph.add_edge("triage", END)

    return graph.compile()