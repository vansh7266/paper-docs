import certifi
import json
import os

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from config import MONGO_URI


DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data")
)

LOCAL_PAPERS_FILE = os.path.join(DATA_DIR, "papers.json")


# ============================================================
# OLD CODE (Single collection, with local JSON fallback) - KEPT FOR REFERENCE
# ============================================================

# client = None
# collection = None

# try:
#     client = MongoClient(
#         MONGO_URI,
#         tls=True,
#         tlsAllowInvalidCertificates=True,
#         serverSelectionTimeoutMS=30000
#     )
#     client.admin.command("ping")
#     print("MongoDB Atlas Connected Successfully!")
#     db = client["research_papers"]
#     collection = db["papers"]

# except PyMongoError as e:
#     print("MongoDB Atlas Connection Failed!")
#     print(e)
#     collection = None


# def _load_local_papers():
#     try:
#         if os.path.exists(LOCAL_PAPERS_FILE):
#             with open(LOCAL_PAPERS_FILE, "r", encoding="utf-8") as f:
#                 return json.load(f)
#     except Exception:
#         pass
#     return []


# def _save_local_papers(papers):
#     os.makedirs(os.path.dirname(LOCAL_PAPERS_FILE), exist_ok=True)
#     with open(LOCAL_PAPERS_FILE, "w", encoding="utf-8") as f:
#         json.dump(papers, f, indent=2, ensure_ascii=False)


# def save_paper(paper):
#     if collection is None:
#         print("MongoDB unavailable. Saving locally...")
#         papers = _load_local_papers()
#         if any(existing.get("title") == paper.get("title") for existing in papers):
#             print("Paper already exists locally.")
#             return False
#         papers.append(paper)
#         _save_local_papers(papers)
#         print(f"Saved locally: {paper['title']}")
#         return True

#     try:
#         existing = collection.find_one({"title": paper["title"]})
#         if not existing:
#             result = collection.insert_one(paper)
#             print(f"Saved to Atlas: {paper['title']}")
#             print(f"Inserted ID: {result.inserted_id}")
#             return True
#         else:
#             print("Paper already exists in Atlas.")
#             return False
#     except PyMongoError as e:
#         print("MongoDB Error:")
#         print(e)
#         return False

# ============================================================
# NEW CODE - Clean connection, single "papers" collection
# ============================================================

client     = None
collection = None


try:
    client = MongoClient(
        MONGO_URI,
        tls=True,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=30000
    )

    # Test connection
    client.admin.command("ping")

    print("MongoDB Atlas Connected Successfully!")

    db         = client["research_papers"]
    collection = db["papers"]

except PyMongoError as e:
    print("MongoDB Atlas Connection Failed!")
    print(e)
    collection = None


def save_paper(paper):
    """
    Save a paper to the 'papers' collection.
    Duplicate check is based on DOI (or title if DOI is unavailable).
    Stores: title, abstract, published, doi, link, rating (default None).
    Returns True if saved, False if duplicate or error.
    """
    if collection is None:
        print("MongoDB unavailable. Paper not saved.")
        return False

    try:
        doi = paper.get("doi")

        # Use DOI for duplicate check if available, else fall back to title
        if doi and doi != "Not Available":
            existing = collection.find_one({"doi": doi})
        else:
            existing = collection.find_one({"title": paper.get("title")})

        if existing:
            print(f"Duplicate skipped: {paper.get('title')}")
            return False

        # Only store the fields we need
        record = {
            "title":     paper.get("title"),
            "abstract":  paper.get("abstract"),
            "published": paper.get("published"),
            "doi":       doi if doi else "Not Available",
            "link":      paper.get("link"),
            "rating":    None   # Team member rates this via the API
        }

        result = collection.insert_one(record)
        print(f"Saved: {paper.get('title')} | ID: {result.inserted_id}")
        return True

    except PyMongoError as e:
        print(f"MongoDB Error: {e}")
        return False


def get_all_papers():
    """
    Retrieve all papers from the collection.
    Returns a list of paper dicts (MongoDB _id converted to string).
    """
    if collection is None:
        print("MongoDB unavailable.")
        return []

    try:
        papers = list(collection.find())
        for paper in papers:
            paper["_id"] = str(paper["_id"])
        return papers

    except PyMongoError as e:
        print(f"MongoDB Error: {e}")
        return []