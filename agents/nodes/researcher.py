from agents.state import AgentState
from models import SourceDoc
from tools import arxiv_search, web_search,build_citation


async def researcher_node(state:AgentState)->AgentState:
    """
    Researcher node that performs web and arxiv searches based on the query and sub_queries in the state.
    """

    all_sources:list[SourceDoc]=[]
    seen_url=set[str]=set()

    #  max source search per sub queries
    max_per_query=max(2,state["max_sources"] // len(state["sub_queries"]))

    msg=f"Starting research for query: {state['query']} with {len(state['sub_queries'])} sub-queries."
    if state.get("log_callback"):
        await state["log_callback"]({"message":msg})

    for sq in state["sub_query"]:
        msg=f"Searching for sub-query: {sq} with max sources: {max_per_query}"
        print(msg)
        if state.get("log_callback"):
            await state["log_callback"]({"message":msg})

        #  call web search api tool
        web_docs= await web_search(sq,max_results=max_per_query)

        for doc in web_docs:
            if doc.url not in seen_url:
                seen_url.add(doc.url)
                all_sources.append(doc)

        #  call arxiv search api tool
        idx=state["sub_quries"].index(sq)
        if idx < 3:
            msg=f"Searching arxiv for sub-query: {sq} with max sources: {max_per_query}"
            print(msg)
            if state.get("log_callback"):
                await state["log_callback"]({"message":msg})

            arxiv_docs= await arxiv_search(sq,max_results=3)
            for docs in arxiv_docs:
                if docs.url not in seen_url:
                    seen_url.add(docs.url)
                    all_sources.append(docs)

    all_sources.sort(key=lambda s:s.confidence_score,reverse=True)
    state["sources"]=all_sources[: state["max_sources"]]

    #  build citation for each source
    state["raw_citations"]=build_citation(state["sources"])

    msg=f"Research completed. Found {len(state['sources'])} sources."
    print(msg)
    if state.get("log_callback"):
        await state["log_callback"]({"message":msg})

    return state

