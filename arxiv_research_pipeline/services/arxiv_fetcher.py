import requests
import feedparser
import time  # used in fetch_with_retry backoff
from datetime import datetime, timedelta


# ============================================================
# OLD CODE (Batch-based fetcher with keyword filter) - KEPT FOR REFERENCE
# ============================================================

# import requests
# import feedparser
#
#
# def fetch_arxiv_papers(start=0, max_results=100):
#
#     url = (
#         "http://export.arxiv.org/api/query?"
#         "search_query=cat:cs.LG&"
#         f"start={start}&max_results={max_results}&"
#         "sortBy=submittedDate&sortOrder=descending"
#     )
#
#     print("\nFetching from URL:")
#     print(url)
#
#     response = requests.get(url)
#
#     print("\nResponse Status Code:")
#     print(response.status_code)
#
#     feed = feedparser.parse(response.text)
#
#     print("\nTotal Entries Fetched:")
#     print(len(feed.entries))
#
#     papers = []
#
#     for entry in feed.entries:
#
#         print("\nPaper Title:")
#         print(entry.title)
#
#         paper = {
#             "title": entry.title,
#             "abstract": entry.summary,
#             "published": entry.published,
#             "doi": entry.get("arxiv_doi", "Not Available"),
#             "link": entry.link
#         }
#
#         papers.append(paper)
#
#     return papers

# ============================================================
# NEW CODE - Fetch ALL of yesterday's papers (no category filter)
# with Retry & Exponential Backoff to handle arXiv rate limits
# ============================================================

# ============================================================
# NEW CODE - Fetch ALL of yesterday's papers (no category filter)
# with Retry & Exponential Backoff to handle arXiv rate limits
# ============================================================

# def fetch_with_retry(url, retries=5, backoff_factor=3, timeout=120):
#     """
#     Perform a GET request with retries and exponential backoff to handle
#     transient network errors, timeouts, or 429 Rate Limits from arXiv.
#     Timeout is 120s to accommodate large single-request responses.
#     """
#     for i in range(retries):
#         try:
#             print(f"Sending request (attempt {i+1}/{retries})...")
#             response = requests.get(url, timeout=timeout)
# 
#             if response.status_code == 200:
#                 return response
# 
#             print(f"Received status code {response.status_code} from arXiv API.")
# 
#         except requests.exceptions.RequestException as e:
#             print(f"Request failed: {e}")
# 
#         delay = backoff_factor * (2 ** i)
#         print(f"Waiting {delay}s before retrying...")
#         time.sleep(delay)
# 
#     return None
# 
# 
# def _fetch_for_date(target_date):
#     date_str  = target_date.strftime("%Y%m%d")
#     date_from = f"{date_str}0000"
#     date_to   = f"{date_str}2359"
# 
#     print(f"Trying date: {target_date.strftime('%Y-%m-%d')} ...")
# 
#     url = (
#         "https://export.arxiv.org/api/query?"
#         f"search_query=submittedDate:[{date_from}+TO+{date_to}]&"
#         "start=0&"
#         "max_results=10000&"
#         "sortBy=submittedDate&sortOrder=descending"
#     )
# 
#     response = fetch_with_retry(url)
#     if response is None:
#         return []
# 
#     feed   = feedparser.parse(response.text)
#     papers = []
# 
#     for entry in feed.entries:
#         papers.append({
#             "doi":    entry.link.split('/abs/')[-1],  # e.g. 2605.22821v1
#             "rating": None
#         })
# 
#     return papers
# 
# 
# def fetch_yesterdays_papers():
#     """
#     Fetch ALL papers submitted to arXiv in a single request (max_results=10000).
#     Tries yesterday first; falls back to 2 days ago if arXiv's index hasn't
#     caught up yet (the search index typically lags by ~1 day).
#     """
#     print("\nFetching ALL arXiv papers — single request, no pagination, no category filter.\n")
# 
#     for days_back in [1, 2]:
#         target = datetime.utcnow() - timedelta(days=days_back)
#         papers = _fetch_for_date(target)
#         if papers:
#             print(f"Total papers fetched for {target.strftime('%Y-%m-%d')}: {len(papers)}")
#             return papers
#         print(f"No papers indexed yet for {target.strftime('%Y-%m-%d')}, trying one day earlier...")
# 
#     print("No papers found for the last 2 days.")
#     return []
# 
# 
# def stream_yesterdays_papers_batched():
#     """
#     Fetches all of yesterday's papers in one request and yields them as a
#     single batch so the frontend receives everything at once via SSE.
#     """
#     papers = fetch_yesterdays_papers()
#     if papers:
#         yield papers

# ============================================================
# UPGRADED CODE - Fetch papers with FULL METADATA preserved
# and support for single paper fetching by URL or ID.
# ============================================================

import re

def fetch_with_retry(url, retries=5, backoff_factor=3, timeout=120):
    """
    Perform a GET request with retries and exponential backoff to handle
    transient network errors, timeouts, or 429 Rate Limits from arXiv.
    """
    for i in range(retries):
        try:
            print(f"Sending request (attempt {i+1}/{retries})...")
            response = requests.get(url, timeout=timeout)

            if response.status_code == 200:
                return response

            print(f"Received status code {response.status_code} from arXiv API.")

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")

        delay = backoff_factor * (2 ** i)
        print(f"Waiting {delay}s before retrying...")
        time.sleep(delay)

    return None


def extract_arxiv_id(identifier):
    """
    Extract arXiv ID from a string which could be a full URL, partial URL, or plain ID.
    Supports formats:
      - https://arxiv.org/abs/2405.12345v1
      - https://arxiv.org/pdf/2405.12345.pdf
      - arXiv:2405.12345
      - 2405.12345v1
    """
    # Look for standard pattern: e.g. 2405.12345 or 2405.12345v1 or 2405.12345v2
    # Standard format: YYMM.NNNNN
    match = re.search(r'(?:arxiv\.org/(?:abs|pdf|html|src)/|arxiv:)?([0-9]+\.[0-9]+(?:v[0-9]+)?)', identifier, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Fallback to general pattern search
    match_direct = re.search(r'([0-9]+\.[0-9]+(?:v[0-9]+)?)', identifier)
    if match_direct:
        return match_direct.group(1)
        
    return identifier.strip()


def clean_text(text):
    """Clean newlines and duplicate spaces from title/summary."""
    if not text:
        return ""
    return " ".join(text.split())


# ============================================================
# PAGINATED FETCH GENERATOR REFERENCE (COMMENTED OUT)
# ============================================================
# def _fetch_for_date_generator(target_date, batch_size=200):
#     """
#     Queries arXiv using pagination to fetch all papers for a specific date in batches.
#     Yields each batch of papers to keep downstream streaming connections active and prevent timeouts.
#     """
#     date_str  = target_date.strftime("%Y%m%d")
#     date_from = f"{date_str}0000"
#     date_to   = f"{date_str}2359"
# 
#     print(f"Initiating paginated crawl for date: {target_date.strftime('%Y-%m-%d')} ...")
# 
#     start = 0
#     while True:
#         url = (
#             "https://export.arxiv.org/api/query?"
#             f"search_query=submittedDate:[{date_from}+TO+{date_to}]&"
#             f"start={start}&"
#             f"max_results={batch_size}&"
#             "sortBy=submittedDate&sortOrder=descending"
#         )
# 
#         print(f"Fetching start={start}, max_results={batch_size} from arXiv...")
#         response = fetch_with_retry(url)
#         if response is None:
#             print("Failed to fetch batch from arXiv. Terminating paginated crawl.")
#             break
# 
#         feed = feedparser.parse(response.text)
#         if not feed.entries:
#             print("No entries returned in this batch. Crawl finished.")
#             break
# 
#         papers = []
#         for entry in feed.entries:
#             doi_val = entry.link.split('/abs/')[-1]
#             papers.append({
#                 "doi":       doi_val,
#                 "title":     clean_text(entry.title),
#                 "link":      entry.link,
#                 "published": entry.published,
#                 "deleted":   False,
#                 "starred":   False,
#                 "ratings":   []
#             })
# 
#         yield papers
# 
#         # If we got fewer results than requested, we have reached the end of the day's submissions
#         if len(feed.entries) < batch_size:
#             print(f"Reached final page (fetched {len(feed.entries)} papers, which is less than batch size {batch_size}).")
#             break
# 
#         start += batch_size
#         print("Sleeping 3 seconds to respect arXiv's rate-limiting policy...")
#         time.sleep(3)


def _fetch_for_date(target_date):
    """
    Fetch all papers for a specific date in a single request (max_results=10000).
    Extremely fast and efficient for standard deployments.
    """
    date_str  = target_date.strftime("%Y%m%d")
    date_from = f"{date_str}0000"
    date_to   = f"{date_str}2359"

    print(f"Fetching all arXiv papers for date: {target_date.strftime('%Y-%m-%d')} ...")

    url = (
        "https://export.arxiv.org/api/query?"
        f"search_query=submittedDate:[{date_from}+TO+{date_to}]&"
        "start=0&"
        "max_results=10000&"
        "sortBy=submittedDate&sortOrder=descending"
    )

    response = fetch_with_retry(url)
    if response is None:
        return []

    feed   = feedparser.parse(response.text)
    papers = []

    for entry in feed.entries:
        doi_val = entry.link.split('/abs/')[-1]
        papers.append({
            "doi":       doi_val,
            "title":     clean_text(entry.title),
            "link":      entry.link,
            "published": entry.published,
            "deleted":   False,
            "starred":   False,
            "ratings":   []
        })

    return papers


def fetch_yesterdays_papers():
    """
    Fetch ALL papers submitted to arXiv in a single request (max_results=10000).
    Tries yesterday first; falls back to 2 days ago if arXiv's index hasn't caught up.
    Integrates check_crawl_exists and log_successful_crawl to prevent double fetching globally.
    """
    from database.mongodb import check_crawl_exists, log_successful_crawl

    print("\nFetching ALL arXiv papers in a single request with full metadata.\n")

    all_already_crawled = True

    # for days_back in [1, 2]:
    for days_back in [1, 2, 3, 4]:
        target = datetime.utcnow() - timedelta(days=days_back)
        target_str = target.strftime("%Y-%m-%d")

        if check_crawl_exists(target_str):
            print(f"Crawl for {target_str} already exists globally in MongoDB. Skipping.")
            continue

        all_already_crawled = False
        papers = _fetch_for_date(target)
        if papers:
            print(f"Total papers fetched for {target.strftime('%Y-%m-%d')}: {len(papers)}")
            log_successful_crawl(target_str)
            return papers
        print(f"No papers indexed yet for {target.strftime('%Y-%m-%d')}, trying one day earlier...")

    if all_already_crawled:
        print("All potential dates have already been successfully crawled globally.")
        return "ALREADY_CRAWLED"

    # print("No papers found for the last 2 days.")
    print("No papers found for the last 4 days.")
    return []


def stream_yesterdays_papers_batched(date_str=None):
    """
    Yields all fetched papers as a single batch for frontend SSE consumption.
    If date_str (YYYY-MM-DD) is provided, crawls that specific date only.
    Handles the 'ALREADY_CRAWLED' lock globally.
    """
    from database.mongodb import check_crawl_exists

    if date_str:
        if check_crawl_exists(date_str):
            yield "ALREADY_CRAWLED"
            return
        try:
            target = datetime.strptime(date_str, "%Y-%m-%d")
            papers = _fetch_for_date(target)
            if papers:
                yield papers
            else:
                yield []
        except Exception as e:
            print(f"Error fetching for date {date_str}: {e}")
            yield []
    else:
        all_already_crawled = True
        # for days_back in [1, 2]:
        for days_back in [1, 2, 3, 4]:
            target = datetime.utcnow() - timedelta(days=days_back)
            target_str = target.strftime("%Y-%m-%d")

            if check_crawl_exists(target_str):
                continue

            all_already_crawled = False
            papers = _fetch_for_date(target)
            if papers:
                yield papers
                return
            
        if all_already_crawled:
            yield "ALREADY_CRAWLED"


def fetch_single_arxiv_paper(identifier):
    """
    Fetches full metadata for a single arXiv paper by ID, URL, or DOI.
    Returns the parsed paper dict or None if not found/error.
    """
    arxiv_id = extract_arxiv_id(identifier)
    print(f"Fetching single arXiv paper. Input: '{identifier}' | Extracted ID: '{arxiv_id}'")

    url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    response = fetch_with_retry(url)
    if response is None:
        print("Failed to fetch from arXiv API.")
        return None

    feed = feedparser.parse(response.text)
    if not feed.entries:
        print(f"No papers found on arXiv matching ID: {arxiv_id}")
        return None

    entry = feed.entries[0]
    return {
        "doi":       entry.link.split('/abs/')[-1],
        "title":     clean_text(entry.title),
        "link":      entry.link,
        "published": entry.published,
        "deleted":   False,
        "starred":   False,
        "ratings":   []
    }