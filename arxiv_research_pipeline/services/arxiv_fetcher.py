# import requests
# import feedparser
# from datetime import datetime, timedelta

# def fetch_arxiv_papers():
#     yesterday = datetime.utcnow() - timedelta(days=1)

#     query = (
#         "http://export.arxiv.org/api/query?"
#         "search_query=cat:cs."
#         "start=0&max_results=20&"
#         "sortBy=submittedDate&sortOrder=descending"
#     )

#     response = requests.get(query)

#     feed = feedparser.parse(response.text)

#     papers = []

#     for entry in feed.entries:
#         paper = {
#             "title": entry.title,
#             "abstract": entry.summary,
#             "published": entry.published,
#             "doi": entry.get("arxiv_doi", "Not Available"),
#             "link": entry.link
#         }

#         papers.append(paper)

#     return papers

import requests
import feedparser


def fetch_arxiv_papers(start=0, max_results=100):

    url = (
        "http://export.arxiv.org/api/query?"
        "search_query=cat:cs.LG&"
        f"start={start}&max_results={max_results}&"
        "sortBy=submittedDate&sortOrder=descending"
    )

    print("\nFetching from URL:")
    print(url)

    response = requests.get(url)

    print("\nResponse Status Code:")
    print(response.status_code)

    feed = feedparser.parse(response.text)

    print("\nTotal Entries Fetched:")
    print(len(feed.entries))

    papers = []

    for entry in feed.entries:

        print("\nPaper Title:")
        print(entry.title)

        paper = {
            "title": entry.title,
            "abstract": entry.summary,
            "published": entry.published,
            "doi": entry.get("arxiv_doi", "Not Available"),
            "link": entry.link
        }

        papers.append(paper)

    return papers