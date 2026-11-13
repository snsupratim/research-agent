
import json

from agents.llm import _llm
from agents.state import AgentState
from models import ReportStatus


async def planner_node(state:AgentState)->AgentState:
    """
    The planner node is responsible for generating sub-queries based on the main query.
    It uses the LLM to generate sub-queries that are relevant to the main query."""

    state["status"]=ReportStatus.RESEARCHING

    msg=f"Generating sub-queries based on the main query : {state['query']}"
    if state.get("log_callback"):
        await state["log_callback"]({"message":msg})

    system=("You are a research planner. Your task is to generate 4 to 6 sub-queries based on the main query provided by the user. Output the sub-queries in a JSON array format. Each sub-query should be concise and focused on a specific aspect of the main query. Do not include any additional text or explanations in your response.")

    raw=await _llm(system,f"Research Query: {state['query']}",max_tokens=500)

    sub_queries=json.loads(raw.strip())

    try:
        state["sub_queries"]=sub_queries[:6]
        if not isinstance(sub_queries,list):
            raise ValueError("Sub-queries should be a list.")
    except Exception as e:
        state["error"]=f"Error parsing sub-queries: {str(e)}"
        state["sub_queries"]=[state["query"],state["query"]+"research",state["query"]+" study",state["query"]+" analysis"]
        if state.get("log_callback"):
            await state["log_callback"]({"message":state["error"]})


    return state
