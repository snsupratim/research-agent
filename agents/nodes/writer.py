import json
from agents.state import AgentState
from agents.llm import _llm
from models import ReportStatus,ReportSection


async def writer_node(state:AgentState)->AgentState:
    """ 
        Writer node that generates a research report based on the sources and claims in the state.
    """

    state["status"]=ReportStatus.WRITING

    msg=f"Starting report writing for report_id: {state['report_id']} with {len(state['claims'])} claims."
    print(msg)
    if state.get("log_callback"):
        await state["log_callback"]({"message":msg})

    source_context="\n\n".join(
        f"SOURCE {c['id']} - {c['title']} ({c['source_type']},"
        f"CONFIDENCE: {c['confidence_score']:.2f})\nURL:{c['url']}\n"
        + next (
            (s.snippent for s in state["sources"] if s.url==c["url"]),
            "No snippet available."
        )
        for c in state["raw_citations"]
    )

    conflict_context=(
        "\n".join(
            f"CONFLICT:{f.claim}-{f.source_a} vs {f.source_b}\nDESCRIPTION:{f.description}"
            for f in state["conflicts_flag"]
        )
        or "No conflicts found."
    )

    system = (    
    "You are an expert research writer. Write a comprehensive, well-structured "    
    "intelligence report. Use inline citations like [1], [2] referencing the "    
    "source IDs provided. Be analytical, not just descriptive. "    
    "Flag conflicts inline where relevant.\n\n"    
    "Output ONLY valid JSON with this structure:\n"    
    '{"summary": "2-3 sentence executive summary", '    
    '"sections": ['    
    '{"heading": "Section Title", "content": "detailed content with [1] citations", '    
    '"citations": ["[1]", "[2]"]}]}'    
    "\n\nAim for 4-6 sections, ~800-1200 words total content."    
)    

    user = (    
    f"Research question: {state['query']}\n\n"    
    f"SOURCES:\n{source_context[:6000]}\n\n" # We limit to 6000 chars to save tokens    
    f"CONFLICT FLAGS:\n{conflict_context}"    
)

    raw=await _llm(
        system,
        user,max_tokens=3000)

    try:

        parsed=json.loads(raw.strip())
        state["summary"]=parsed.get("summary","No summary provided.")

        sections_raw=parsed.get("sections",[])
        state["sections"]=[
            ReportSection(
                heading=s.get("heading","No heading"),
                content=s.get("content","No content"),
                citations=s.get("citations",[])
            )
            for s in sections_raw
        ]
    except Exception as e:
        state["summary"]="Research report generation failed."
        state["sections"]=[
            ReportSection(
                heading="Error",content=f"Report generation failed due to error: {e}",citations=[]
            )
        ]

    state["status"]=ReportStatus.DONE
    return state