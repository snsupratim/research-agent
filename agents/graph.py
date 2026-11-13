from langgraph.graph import END, StateGraph
from agents.state import AgentState
from agents.nodes.researcher import researcher_node
from agents.nodes.critic import critic_node
from agents.nodes.writer import writer_node
from agents.nodes.planner import planner_node
from models import ReportStatus
from typing import Callable, Awaitable,Any

def build_graph():
    g=StateGraph(AgentState)

    g.add_node("planner", planner_node)
    g.add_node("researcher", researcher_node)
    g.add_node("critic", critic_node)
    g.add_node("writer", writer_node)

    g.set_entry_point("planner")
    g.add_edge("planner","researcher")
    g.add_edge("researcher","critic")
    g.add_edge("critic","writer")
    g.add_edge("writer",END)

    return g.compile()

research_graph=build_graph()

async def run_research_graph(
        query:str,
        max_sources:int=15,
        report_id: str |None=None,
        update_callback:Callable[[dict],Awaitable[None]] | None = None
)->AgentState:
    """ Execute the full research pipeline and return final state , streaming updates"""

    initial_state:AgentState={
        "query":query,
        "max_sources":max_sources,
        "sub_quries":[],
        "sources":[],
        "raw_citations":[],
        "conflicts_flag":[],
        "sections":[],
        "summary":[],
        "status":ReportStatus.PENDING,
        "error":None,
        "report_id":report_id,
        "log_callback":update_callback,
    }

    try:
        final_state=initial_state
        print(f"Starting the research run for every query:{query}")

        # astream() pauses after every mnode and extracts states of intermidatery
        async for output in research_graph.astream(initial_state):
            for node_name,state in output.items():
                print(f"Finsihed node: {node_name}")
                final_state=state

                if update_callback and "status" in state:
                    status_val=state["status"].value if hasattr(state["status","value"]) else str(state["status"])
                    await update_callback({"status":status_val})

        print(f"Research run completed successfully!")
        return final_state
    except Exception as e:
        import traceback
        print(f"Error during research run : {e}")
        initial_state["status"]=ReportStatus.FAILED
        initial_state["error"]=f"{type(e).__name__}:{e}\n{traceback.format_exc()}"

        if update_callback:
            await update_callback({"status":ReportStatus.FAILED.value})
        return initial_state