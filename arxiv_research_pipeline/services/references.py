import requests
import time
import urllib.parse

SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"
HEADERS = {"User-Agent": "arxiv-research-pipeline/1.0"}


def fetch_references(paper, max_references=20):
    """Fetch reference titles and abstracts for a paper using Semantic Scholar.

    Strategy:
    - Prefer DOI if available, else use the paper title to search.
    - Use the search endpoint to obtain a Semantic Scholar paperId, then
      fetch the paper's `references` field.
    - Return a list of dicts: {"title": ..., "abstract": ...}
    """
    query_value = None
    doi = paper.get("doi")
    if doi and doi != "Not Available":
        # Semantic Scholar recognizes DOI when passed as-is or prefixed
        query_value = f"DOI:{doi}"
    else:
        query_value = paper.get("title", "")

    try:
        q = urllib.parse.quote(query_value)
        search_url = f"{SEMANTIC_SCHOLAR_BASE}/paper/search?query={q}&limit=1&fields=title,abstract"
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"Semantic Scholar search failed: {resp.status_code}")
            return []

        search_data = resp.json()
        hits = search_data.get("data") or []
        if not hits:
            return []

        paper_id = hits[0].get("paperId")
        if not paper_id:
            return []

        # Fetch references for the found paper
        refs_url = f"{SEMANTIC_SCHOLAR_BASE}/paper/{paper_id}?fields=references.title,references.abstract"
        resp2 = requests.get(refs_url, headers=HEADERS, timeout=15)
        if resp2.status_code != 200:
            print(f"Semantic Scholar paper fetch failed: {resp2.status_code}")
            return []

        paper_data = resp2.json()
        refs = paper_data.get("references", []) or []

        out = []
        for r in refs[:max_references]:
            out.append({
                "title": r.get("title"),
                "abstract": r.get("abstract") or "Not Available"
            })

        # small delay to be polite with the API
        time.sleep(0.2)
        return out

    except Exception as e:
        print("Reference fetch error:", e)
        return []