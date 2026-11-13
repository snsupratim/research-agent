"""
tool belt:
    1. throttle function to avoid spamming a site with API calls
    2. domain confidence function to assign a confidence score to a URL based on its domain
    3. web search function to search the web via Tavily API and return a list of SourceDoc objects
    4. arxiv search function to search arXiv for papers matching a query and return a list of SourceDoc objects
    5. cross reference function to cross-reference a list of claims against a list of Source Doc objects and return a dictionary mapping each claim to the URLs of sources that support it
    6. build citations function to build a list of citation dictionaries from a list of SourceDoc objects, suitable for inclusion in a report or paper

"""


import os
import time
import asyncio
import httpx
from tenacity import retry, retry_if_exception_type,stop_after_attempt,wait_exponential
from models import SourceDoc,SourceType
import arxiv
import re
from typing import Any

from urllib.parse import urlparse

# throttle function
_tool_last_call:dict[str,float]={}
_TOOL_MIN_INTERVAL=float(os.environ.get("TOOL_MIN_INTERVAL", "1.0"))
_ARXIV_MIN_INTERVAL=float(os.environ.get("ARXIV_MIN_INTERVAL", "5.0"))


async def _throttle(tool_name:str):
    last=_tool_last_call.get(tool_name, 0)
    wait=_TOOL_MIN_INTERVAL-(time.monotonic()-last)
    if wait > 0:
        await asyncio.sleep(wait)
    _tool_last_call[tool_name]=time.monotonic()


# domain confidence function
def _domain_confidence(url:str)->float:

    """
    Returns a confidence score for a given URL based on its domain.
    """

    high=[".edu",".gov",".in","arxiv.org","nature.com,science.org","acm.org","ieee.org","thelancet.com","researchgate.net","sciencedirect.com","springer.com"]
    medium=[".org",".net",".com","wikipedia.org","jstor.org",".reuters.com",".bbc.com",".cnn.com",".nytimes.com",".theguardian.com"]

    domain=urlparse(url).netloc.lower()

    for h in high:
        if h in domain:
            return 0.90
    for m in medium:
        if m in domain:
            return 0.75
    return 0.55


@retry(
        retry=retry_if_exception_type((httpx.TimeoutException,httpx.HTTPError)),
        wait=wait_exponential(multiple=1, min=2, max=10),
        stop=stop_after_attempt(3)
)
async def web_search(query:str,max_results:int=5)->list[SourceDoc]:
    """Search the web via Tavily API and return a list of SourceDoc objects."""

    # 1. we call out throttle function to make sure we don't spam a site witha API calls       
    await _throttle("web_search")

    # 2. we call the Tavily API to search the web
    api_key=os.getenv("TAVILY_API_KEY")
    if not api_key:
        print("TAVILY_API_KEY not set in environment variables")
        return []

    async with httpx.AsyncClient(timeout=20) as client:
        response=await client.post("https://api.tavily.com/search",
                                   json={"api_key":api_key,
                                       "query":query,
                                       "max_results":max_results,
                                       "search_depth":"advanced",
                                       "include_answer":False,
                                       "include_raw_content":False
                                         })
        response.raise_for_status() # if api call fails, let know tenacity
        data=response.json()

        #  map within SourceDoc model
        docs:list[SourceDoc]=[]

        for res in data.get("results",[]):
            url=res.get("url","")

            docs.append(
                SourceDoc(
                    url=url,
                    title=res.get("title",""),
                    source_type=SourceType.WEB,
                    snippent=res.get("content","")[:500],
                    confidence_score=_domain_confidence(url),
                    metadata={"score":res.get("score",0)}
                )
            )

        return docs


async def arxiv_search(query:str,max_results:int=5)->list[SourceDoc]:
    """Search arXiv for papers matching the query and return a list of SourceDoc objects."""

    last=_tool_last_call.get("arxiv_search", 0)
    wait=_ARXIV_MIN_INTERVAL-(time.monotonic()-last)
    if wait > 0:
        await asyncio.sleep(wait)
        _tool_last_call["arxiv_search"]=time.monotonic()

    #  clean the query to remove any special characters that might interfere with the search
    clean_query=re.sub(r'site:\S+', '', query).strip()  # remove site: filters


    loop=asyncio.get_event_loop()

    #  run the blocking arxiv search in a separate thread to avoid blocking the event loop
    def _sync_search():
        try:
            client=arxiv.Client(page_size=max_results,delay_seconds=3,num_retries=1)
            search=arxiv.Search(query=clean_query,max_results=max_results,sort_by=arxiv.SortCriterion.Relevance)
            return list(client.results(search))
        except Exception as e:
            print(f"Error during arXiv search: {e}")
            return []

    results=await loop.run_in_executor(None,_sync_search)

    docs: list[SourceDoc]=[]

    for paper in results:
        docs.append(
            SourceDoc(
                url=paper.entry_id,
                title=paper.title,
                source_type=SourceType.ARXIV,
                snippent=paper.summary[:500],
                confidence_score=0.95,  # arXiv papers are generally reliable
                metadata={
                    "authors":[author.name for author in paper.authors],
                    "published":paper.published.isoformat(),
                    "updated":paper.updated.isoformat(),
                    "primary_category":paper.primary_category,
                    "categories":paper.categories
                }
            )
        )

        return docs

# cross reference function for critic agent

def cross_reference_claims(claims:list[str],sources:list[SourceDoc])->dict[str,list[str]]:
    """
Cross-reference a list of claims against a list of SourceDoc objects and return a dictionary mapping each claim to the URLs of sources that support it.
    """

    results:dict[str,list[str]]={}
    for claim in claims:
        keywords=set(re.findall(r"\b\w{5,}\b",claim.lower()))  # extract keywords of length >=5
        supporting:list[str]=[]

        for source in sources:
            src_text=(source.title + " " + source.snippent).lower()
            if sum(1 for kw in keywords if kw in src_text) >=2:
                supporting.append(source.url)

        results[claim]=supporting

    return results




def build_citations(sources:list[SourceDoc])->list[dict[str,Any]]:
    """
Build a list of citation dictionaries from a list of SourceDoc objects, suitable for inclusion in a report or paper. 
    """

    seen: set[str]=set()
    citations=[]
    ids=1

    for source in sources:
        if source.url in seen:
            continue

        seen.add(source.url)

        citations.append({
            "id":f"[{ids}]",
            "title":source.title,
            "url":source.url,
            "source_type":source.source_type,
            "confidence_score":source.confidence_score,
        })
        ids +=1

    return citations
