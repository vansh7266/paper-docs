import requests
import feedparser
import time
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

MAX_RESULTS_PER_REQUEST = 100  # arXiv recommends <= 100 per request


def fetch_with_retry(url, retries=5, backoff_factor=3, timeout=30):
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


def fetch_yesterdays_papers():
    """
    Fetch ALL papers submitted to arXiv yesterday — across all fields/categories.
    No category filtering applied. Paginates through all results.
    Returns a list of dicts: title, abstract, published, doi, link, rating.
    """
    yesterday  = datetime.utcnow() - timedelta(days=1)
    date_str   = yesterday.strftime("%Y%m%d")
    date_from  = f"{date_str}0000"
    date_to    = f"{date_str}2359"

    all_papers = []
    start      = 0

    print(f"\nFetching ALL arXiv papers submitted on: {yesterday.strftime('%Y-%m-%d')}")
    print("No category filter — fetching from all fields.\n")

    while True:
        # Date-only query with no category restriction
        url = (
            "https://export.arxiv.org/api/query?"
            f"search_query=submittedDate:[{date_from}+TO+{date_to}]&"
            f"start={start}&"
            f"max_results={MAX_RESULTS_PER_REQUEST}&"
            "sortBy=submittedDate&sortOrder=descending"
        )

        print(f"Fetching batch starting at index {start}...")
        response = fetch_with_retry(url)

        if response is None:
            print("Failed to fetch from arXiv after all retries. Stopping.")
            break

        feed    = feedparser.parse(response.text)
        entries = feed.entries

        print(f"Entries returned: {len(entries)}")

        if not entries:
            print("No more entries. Fetch complete.")
            break

        for entry in entries:
            paper = {
                "title":     entry.title,
                "abstract":  entry.summary,
                "published": entry.published,
                "doi":       entry.get("arxiv_doi", "Not Available"),
                "link":      entry.link,
                "rating":    None   # Set by team via the rating API
            }
            all_papers.append(paper)

        # If fewer entries than requested, we've reached the last page
        if len(entries) < MAX_RESULTS_PER_REQUEST:
            print("Last page reached. All papers retrieved.")
            break

        start += MAX_RESULTS_PER_REQUEST

        # arXiv recommends 3 seconds between requests
        print("Waiting 3s before next batch (arXiv rate limit policy)...")
        time.sleep(3)

    print(f"\nTotal papers fetched for {yesterday.strftime('%Y-%m-%d')}: {len(all_papers)}")
    return all_papers


def stream_yesterdays_papers_batched():
    """
    Batch generator version of the fetcher.
    Yields one LIST of papers per arXiv API call (e.g. 100 papers at a time).
    The entire batch is sent to the frontend at once so papers appear in groups,
    not one by one. This is faster and less noisy in the UI.
    """
    yesterday  = datetime.utcnow() - timedelta(days=1)
    date_str   = yesterday.strftime("%Y%m%d")
    date_from  = f"{date_str}0000"
    date_to    = f"{date_str}2359"
    start      = 0

    print(f"\n[STREAM] Fetching all arXiv papers for {yesterday.strftime('%Y-%m-%d')} (all fields)...")

    while True:
        url = (
            "https://export.arxiv.org/api/query?"
            f"search_query=submittedDate:[{date_from}+TO+{date_to}]&"
            f"start={start}&"
            f"max_results={MAX_RESULTS_PER_REQUEST}&"
            "sortBy=submittedDate&sortOrder=descending"
        )

        print(f"[STREAM] Fetching batch at index {start}...")
        response = fetch_with_retry(url)

        if response is None:
            print("[STREAM] Failed after all retries. Stopping.")
            return

        feed    = feedparser.parse(response.text)
        entries = feed.entries

        print(f"[STREAM] Got {len(entries)} entries in this batch.")

        if not entries:
            print("[STREAM] No entries. Done.")
            return

        # Build the full batch list and yield it all at once
        batch = []
        for entry in entries:
            batch.append({
                "title":     entry.title,
                "abstract":  entry.summary,
                "published": entry.published,
                "doi":       entry.get("arxiv_doi", "Not Available"),
                "link":      entry.link,
                "rating":    None
            })

        yield batch   # <-- entire batch of 100 papers at once

        if len(entries) < MAX_RESULTS_PER_REQUEST:
            print("[STREAM] Last page reached.")
            return

        start += MAX_RESULTS_PER_REQUEST
        time.sleep(3)  # arXiv rate limit policy