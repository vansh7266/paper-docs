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


client = None
collection = None


# =========================
# MongoDB Atlas Connection
# =========================

try:

    client = MongoClient(
    MONGO_URI,
    tls=True,
    tlsAllowInvalidCertificates=True,
    serverSelectionTimeoutMS=30000
    )

    # Test Connection
    client.admin.command("ping")

    print("MongoDB Atlas Connected Successfully!")

    # Database & Collection
    db = client["research_papers"]

    collection = db["papers"]

except PyMongoError as e:

    print("MongoDB Atlas Connection Failed!")

    print(e)

    collection = None


# =========================
# Local JSON Backup Methods
# =========================

def _load_local_papers():

    try:

        if os.path.exists(LOCAL_PAPERS_FILE):

            with open(
                LOCAL_PAPERS_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                return json.load(f)

    except Exception:

        pass

    return []


def _save_local_papers(papers):

    os.makedirs(
        os.path.dirname(LOCAL_PAPERS_FILE),
        exist_ok=True
    )

    with open(
        LOCAL_PAPERS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            papers,
            f,
            indent=2,
            ensure_ascii=False
        )


# =========================
# Save Paper Function
# =========================

def save_paper(paper):

    # If MongoDB Atlas unavailable
    if collection is None:

        print(
            "MongoDB unavailable. Saving locally..."
        )

        papers = _load_local_papers()

        # Duplicate check
        if any(
            existing.get("title") == paper.get("title")
            for existing in papers
        ):

            print("Paper already exists locally.")

            return False

        papers.append(paper)

        _save_local_papers(papers)

        print(f"Saved locally: {paper['title']}")

        return True

    # MongoDB Atlas Save
    try:

        existing = collection.find_one({
            "title": paper["title"]
        })

        if not existing:

            result = collection.insert_one(paper)

            print(f"Saved to Atlas: {paper['title']}")

            print(f"Inserted ID: {result.inserted_id}")

            return True

        else:

            print("Paper already exists in Atlas.")

            return False

    except PyMongoError as e:

        print("MongoDB Error:")

        print(e)

        return False