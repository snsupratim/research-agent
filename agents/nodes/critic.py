from agents.llm import _llm
from models import ConflictFlag,ReportStatus
from tools import cross_reference_claims
from agents.state import AgentState
import json


async def critic_node(state:AgentState)->AgentState:
    """ 
        Critic node for evaluating the research report
    """

    state["report_status"]=ReportStatus.CRITIQUING

    mesg=f"Starting critique for report_id: {state['report_id']} with {len(state['claims'])} claims."
    print(mesg)
    if state.get("log_callback"):
        await state["log_callback"]({"message":mesg})


    source_summaries="\n".join(
        f"[{i+1}] ({s.source_type}) {s.title}: {s.snippet[:300]}"
        for i ,s in enumerate(state["sources"][:12])
    )

    system = (
    "You are a ruthless research critic. Your job is to find DISAGREEMENTS, "
    "CONTRADICTIONS, and CONFLICTING CLAIMS between sources. Be aggressive — "
    "even subtle differences in numbers, timelines, conclusions, or emphasis count as conflicts.\n\n"
    "Look specifically for:\n"
    "- Different performance numbers or benchmarks for the same model/product\n"
    "- One source saying X is effective, another saying it is not\n"
    "- Disagreements on timelines ('will happen in 2025' vs 'already here')\n"
    "- One source praising something another source criticises\n"
    "- Different statistics cited for the same phenomenon\n"
    "- Optimistic vs pessimistic conclusions on the same topic\n\n"
    "You MUST find at least 2-3 conflicts. If sources don't directly contradict, "
    "find the TENSION — where they emphasise opposite things or lead to opposite conclusions.\n\n"
    "Output ONLY valid JSON, no markdown:\n"
    '{"key_claims": ["claim1", "claim2", "claim3"], '
    '"conflicts": ['
    '{"claim": "specific contested claim", '
    '"source_a": "exact source title", '
    '"source_b": "exact source title", '
    '"description": "Source A says X while Source B says Y — explain the tension clearly"}'
    ']}'
    )

    raw=await _llm(
        system,
        f"Research topic : {state['query']}\n\nSources:\n{source_summaries}",
        max_tokens=800,
    )

    try:
        parsed=json.loads(raw.strip())
        key_claims=parsed.get("key_claims",[])
        raw_conflicts=parsed.get("conflicts",[])
    except Exception as e:
        key_claims=[]
        raw_conflicts=[]

    cross_ref_results=cross_reference_claims(key_claims,state["sources"])

    flags: list[ConflictFlag]=[]
    for c in raw_conflicts:
        flags.append(
            ConflictFlag(
                claim=c.get("claim",""),
                source_a=c.get("source_a",""),
                source_b=c.get("source_b",""),
                description=c.get("description","")
            )
        )

    state["conflict_flags"]=flags
    return state