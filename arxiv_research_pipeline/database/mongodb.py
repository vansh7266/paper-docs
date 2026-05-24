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

# ============================================================
# NEW CODE - Clean connection, single "papers" collection
# ============================================================

# client     = None
# collection = None
# 
# 
# try:
#     client = MongoClient(
#         MONGO_URI,
#         tls=True,
#         tlsAllowInvalidCertificates=True,
#         serverSelectionTimeoutMS=30000
#     )
# 
#     # Test connection
#     client.admin.command("ping")
# 
#     print("MongoDB Atlas Connected Successfully!")
# 
#     db         = client["research_papers"]
#     collection = db["papers"]
# 
# except PyMongoError as e:
#     print("MongoDB Atlas Connection Failed!")
#     print(e)
#     collection = None
# 
# 
# def save_paper(paper):
#     """
#     Save a paper to the 'papers' collection.
#     Stores only: doi (arXiv short ID) and rating.
#     Deduplicates on doi.
#     Returns True if saved, False if duplicate or error.
#     """
#     if collection is None:
#         print("MongoDB unavailable. Paper not saved.")
#         return False
# 
#     try:
#         doi = paper.get("doi")
# 
#         if collection.find_one({"doi": doi}):
#             print(f"Duplicate skipped: {doi}")
#             return False
# 
#         result = collection.insert_one({"doi": doi, "rating": None})
#         print(f"Saved: {doi} | ID: {result.inserted_id}")
#         return True
# 
#     except PyMongoError as e:
#         print(f"MongoDB Error: {e}")
#         return False
# 
# 
# def get_all_papers():
#     """
#     Retrieve all papers from the collection.
#     Returns a list of paper dicts (MongoDB _id converted to string).
#     """
#     if collection is None:
#         print("MongoDB unavailable.")
#         return []
# 
#     try:
#         papers = list(collection.find())
#         for paper in papers:
#             paper["_id"] = str(paper["_id"])
#         return papers
# 
#     except PyMongoError as e:
#         print(f"MongoDB Error: {e}")
#         return []

# ============================================================
# UPGRADED CODE - Robust Multi-User Collaborative Operations
# ============================================================

from datetime import datetime

client     = None
collection = None
notifications_col = None
crawls_col = None

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

    db                = client["research_papers"]
    collection        = db["papers"]
    notifications_col = db["notifications"]
    crawls_col        = db["crawls"]

except PyMongoError as e:
    print("MongoDB Atlas Connection Failed!")
    print(e)
    collection = None
    notifications_col = None
    crawls_col = None


def save_paper_metadata(paper):
    """
    Saves the complete paper metadata to MongoDB Atlas.
    Deduplicates based on DOI (arXiv short ID).
    Default structure:
      doi, title, abstract, link, published, deleted=False, starred=False, ratings=[]
    Returns True if successfully inserted, False if already exists or on error.
    """
    if collection is None:
        print("MongoDB unavailable. Paper metadata not saved.")
        return False

    try:
        doi = paper.get("doi")
        if not doi:
            print("Missing DOI field in paper metadata.")
            return False

        if collection.find_one({"doi": doi}):
            print(f"Paper duplicate skipped: {doi}")
            return False

        full_doc = {
            "doi":       doi,
            "title":     paper.get("title", ""),
            "link":      paper.get("link", ""),
            "published": paper.get("published", ""),
            "deleted":   paper.get("deleted", False),
            "starred":   paper.get("starred", False),
            "ratings":   paper.get("ratings", []),
            "manual":    paper.get("manual", False),
            "comments":  paper.get("comments", [])
        }

        result = collection.insert_one(full_doc)
        print(f"Successfully saved paper {doi} | DB ID: {result.inserted_id}")
        return True

    except PyMongoError as e:
        print(f"MongoDB Error in save_paper_metadata: {e}")
        return False


def rate_paper_db(doi, username, rating):
    """
    Submits or updates a team member's rating for a specific paper.
    If the user has already rated, the rating is updated. Otherwise, it is pushed.
    Returns dict indicating success.
    """
    if collection is None:
        return {"success": False, "message": "Database unavailable."}

    try:
        # Validate rating
        if not isinstance(rating, (int, float)) or not (1 <= rating <= 5):
            return {"success": False, "message": "Rating must be a number between 1 and 5."}

        # Check if user has already rated this paper
        exists = collection.find_one({"doi": doi, "ratings.username": username})

        if exists:
            # Update existing rating
            result = collection.update_one(
                {"doi": doi, "ratings.username": username},
                {"$set": {"ratings.$.rating": rating}}
            )
            print(f"Updated rating for {username} on {doi} to {rating}")
        else:
            # Push new rating entry
            result = collection.update_one(
                {"doi": doi},
                {"$push": {"ratings": {"username": username, "rating": rating}}}
            )
            print(f"Added new rating for {username} on {doi} with value {rating}")

        if result.matched_count == 0:
            return {"success": False, "message": f"No paper found in DB with DOI: {doi}"}

        return {"success": True, "message": f"Rating {rating}/5 submitted successfully by {username}."}

    except PyMongoError as e:
        print(f"MongoDB Error in rate_paper_db: {e}")
        return {"success": False, "message": f"Database error: {str(e)}"}


def soft_delete_paper_db(doi, username):
    """
    Performs a soft delete of a paper, moving it to Temporary Memory (Trash).
    """
    if collection is None:
        return False

    try:
        result = collection.update_one(
            {"doi": doi},
            {
                "$set": {
                    "deleted": True,
                    "deleted_by": username,
                    "deleted_at": datetime.utcnow().isoformat()
                }
            }
        )
        return result.modified_count > 0

    except PyMongoError as e:
        print(f"MongoDB Error in soft_delete_paper_db: {e}")
        return False


def restore_paper_db(doi, username):
    """
    Restores a paper from Temporary Memory back to the Active feed.
    """
    if collection is None:
        return False

    try:
        result = collection.update_one(
            {"doi": doi},
            {
                "$set": {"deleted": False},
                "$unset": {"deleted_by": "", "deleted_at": ""}
            }
        )
        return result.modified_count > 0

    except PyMongoError as e:
        print(f"MongoDB Error in restore_paper_db: {e}")
        return False


def permanent_delete_paper_db(doi):
    """
    Permanently deletes a paper document from the MongoDB collection.
    """
    if collection is None:
        return False

    try:
        result = collection.delete_one({"doi": doi})
        return result.deleted_count > 0

    except PyMongoError as e:
        print(f"MongoDB Error in permanent_delete_paper_db: {e}")
        return False


def permanent_delete_all_trash_db():
    """
    Permanently deletes all soft-deleted papers from the database.
    """
    if collection is None:
        return False

    try:
        result = collection.delete_many({"deleted": True})
        print(f"Permanently wiped all soft-deleted papers. Total deleted: {result.deleted_count}")
        return True

    except PyMongoError as e:
        print(f"MongoDB Error in permanent_delete_all_trash_db: {e}")
        return False


def toggle_star_paper_db(doi, starred):
    """
    Toggles the shared star/favorite status globally for all users.
    """
    if collection is None:
        return False

    try:
        result = collection.update_one(
            {"doi": doi},
            {"$set": {"starred": starred}}
        )
        return result.matched_count > 0

    except PyMongoError as e:
        print(f"MongoDB Error in toggle_star_paper_db: {e}")
        return False


def get_papers_by_status(status="active"):
    """
    Fetches papers by their filter category.
    - active: deleted is False or does not exist
    - deleted: deleted is True (Temporary Memory)
    - starred: starred is True and deleted is not True (Curated starred feed)
    """
    if collection is None:
        return []

    try:
        if status == "deleted":
            query = {"deleted": True}
        elif status == "starred":
            query = {"starred": True, "deleted": {"$ne": True}}
        elif status == "manual":
            query = {"manual": True, "deleted": {"$ne": True}}
        else:  # active feed
            query = {"deleted": {"$ne": True}, "manual": {"$ne": True}}

        # Sort by published date descending (newest first)
        papers = list(collection.find(query).sort("published", -1))

        # Convert ObjectIDs to strings for JSON serialization
        for paper in papers:
            paper["_id"] = str(paper["_id"])

        return papers

    except PyMongoError as e:
        print(f"MongoDB Error in get_papers_by_status: {e}")
        return []


def add_notification_db(action_type, username, doi, title, rating=None):
    """
    Logs an action to the shared notifications audit log.
    Action types: delete, restore, add, rate
    """
    if notifications_col is None:
        return False

    try:
        doc = {
            "type":      action_type,
            "username":  username,
            "doi":       doi,
            "title":     title,
            "rating":    rating,
            "timestamp": datetime.utcnow().isoformat()
        }
        notifications_col.insert_one(doc)
        return True

    except PyMongoError as e:
        print(f"MongoDB Error in add_notification_db: {e}")
        return False


def get_notifications_db():
    """
    Retrieves the 50 most recent global team notifications.
    """
    if notifications_col is None:
        return []

    try:
        logs = list(notifications_col.find().sort("timestamp", -1).limit(50))
        for log in logs:
            log["_id"] = str(log["_id"])
        return logs

    except PyMongoError as e:
        print(f"MongoDB Error in get_notifications_db: {e}")
        return []


def clear_all_data_db():
    """
    Wipes all records from the papers and notifications collections completely.
    """
    if collection is None or notifications_col is None:
        return False

    try:
        collection.drop()
        notifications_col.drop()
        if crawls_col is not None:
            crawls_col.drop()
        print("MongoDB Collections successfully dropped.")
        return True
    except PyMongoError as e:
        print(f"MongoDB error in clear_all_data_db: {e}")
        return False


def check_crawl_exists(date_str):
    """
    Checks if a crawl for a specific date (YYYY-MM-DD) already exists globally.
    """
    if crawls_col is None:
        print("MongoDB crawls collection unavailable.")
        return False
    try:
        record = crawls_col.find_one({"date": date_str})
        return record is not None
    except PyMongoError as e:
        print(f"MongoDB Error in check_crawl_exists: {e}")
        return False


def log_successful_crawl(date_str):
    """
    Logs a successful crawl date to the crawls collection to prevent double-fetching.
    """
    if crawls_col is None:
        print("MongoDB crawls collection unavailable.")
        return False
    try:
        # Check if already logged first
        if crawls_col.find_one({"date": date_str}):
            return True
        crawls_col.insert_one({
            "date": date_str,
            "timestamp": datetime.utcnow().isoformat()
        })
        print(f"Logged successful crawl globally for date: {date_str}")
        return True
    except PyMongoError as e:
        print(f"MongoDB Error in log_successful_crawl: {e}")
        return False


def add_comment_to_paper(doi, username, text):
    """
    Atomically appends a comment subdocument to a specific paper's comments array.
    """
    if collection is None:
        return {"success": False, "message": "Database unavailable."}

    try:
        comment = {
            "username":  username,
            "text":      text,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Atomically push the comment into the array
        result = collection.update_one(
            {"doi": doi},
            {"$push": {"comments": comment}}
        )

        if result.matched_count == 0:
            return {"success": False, "message": f"No paper found in DB with DOI: {doi}"}

        return {"success": True, "message": "Comment added successfully.", "comment": comment}

    except PyMongoError as e:
        print(f"MongoDB Error in add_comment_to_paper: {e}")
        return {"success": False, "message": f"Database error: {str(e)}"}


def get_paper_comments(doi):
    """
    Retrieves the comments array for a specific paper.
    """
    if collection is None:
        return []

    try:
        paper = collection.find_one({"doi": doi}, {"comments": 1, "_id": 0})
        if paper and "comments" in paper:
            return paper["comments"]
        return []
    except PyMongoError as e:
        print(f"MongoDB Error in get_paper_comments: {e}")
        return []