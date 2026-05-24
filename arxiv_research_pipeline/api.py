# ============================================================
# OLD CODE - Flask server endpoints (KEPT FOR REFERENCE)
# ============================================================

# import json
# from flask import Flask, jsonify, request, Response, stream_with_context
# from flask_cors import CORS
# 
# from database.mongodb import collection, get_all_papers, save_paper
# from services.ratings import rate_paper
# from services.arxiv_fetcher import stream_yesterdays_papers_batched
# 
# app = Flask(__name__)
# CORS(app)  # Allow requests from the frontend (HTML/JS)
# 
# 
# # ============================================================
# # GET /papers
# # Returns all papers currently stored in the database
# # ============================================================
# 
# @app.route("/papers", methods=["GET"])
# def get_papers():
#     try:
#         papers = get_all_papers()
#         return jsonify({
#             "success": True,
#             "count":   len(papers),
#             "papers":  papers
#         }), 200
# 
#     except Exception as e:
#         return jsonify({
#             "success": False,
#             "message": str(e)
#         }), 500
# 
# 
# # ============================================================
# # GET /fetch
# # Streams yesterday's papers from arXiv live using Server-Sent Events (SSE).
# # The frontend connects once and receives papers one by one as they are
# # fetched and saved — so the UI starts populating immediately.
# # Event format: data: { ...paper fields..., "status": "new"|"duplicate" }
# # Final event:  data: { "done": true, "total": N }
# # ============================================================
# 
# @app.route("/fetch", methods=["GET"])
# def fetch_papers_stream():
#     def generate():
#         total_new        = 0
#         total_duplicates = 0
# 
#         try:
#             # Each iteration of the loop = one arXiv API call = one batch of 100 papers
#             for batch in stream_yesterdays_papers_batched():
#                 batch_new  = []
#                 batch_dup  = []
# 
#                 for paper in batch:
#                     saved = save_paper(paper)
#                     if saved:
#                         total_new += 1
#                         paper["status"] = "new"
#                         batch_new.append(paper)
#                     else:
#                         total_duplicates += 1
#                         paper["status"] = "duplicate"
#                         batch_dup.append(paper)
# 
#                 # Send the whole batch (new + duplicates) in ONE SSE event
#                 # Frontend receives all 100 at once and renders them together
#                 event_data = {
#                     "batch":      batch_new + batch_dup,
#                     "batch_new":  len(batch_new),
#                     "batch_dup":  len(batch_dup),
#                     "total_new":  total_new,
#                     "total_dup":  total_duplicates
#                 }
#                 yield f"data: {json.dumps(event_data)}\n\n"
# 
#         except Exception as e:
#             yield f"data: {json.dumps({'error': str(e)})}\n\n"
# 
#         # Final "done" signal
#         yield f"data: {json.dumps({'done': True, 'new': total_new, 'duplicates': total_duplicates})}\n\n"
# 
#     headers = {
#         "Cache-Control":    "no-cache",
#         "X-Accel-Buffering": "no",         # Disable nginx buffering if deployed
#         "Content-Type":     "text/event-stream",
#         "Access-Control-Allow-Origin": "*"
#     }
#     return Response(stream_with_context(generate()), headers=headers)
# 
# 
# # ============================================================
# # POST /rate
# # Body: { "link": "https://arxiv.org/abs/...", "rating": 4 }
# # Saves a team member's rating (1-5) for a paper.
# # Uses the arXiv link as the unique identifier since most
# # arXiv papers do not have a DOI until after journal publication.
# # ============================================================
# 
# @app.route("/rate", methods=["POST"])
# def rate():
#     data = request.get_json()
# 
#     if not data:
#         return jsonify({
#             "success": False,
#             "message": "Request body must be JSON."
#         }), 400
# 
#     link   = data.get("link")
#     rating = data.get("rating")
# 
#     if not link:
#         return jsonify({
#             "success": False,
#             "message": "Missing field: link"
#         }), 400
# 
#     if rating is None:
#         return jsonify({
#             "success": False,
#             "message": "Missing field: rating"
#         }), 400
# 
#     result = rate_paper(collection, link, rating)
# 
#     status_code = 200 if result["success"] else 400
#     return jsonify(result), status_code

# ============================================================
# UPGRADED CODE - Flask server endpoints for Collaborative Feed
# ============================================================

import json
import os
from flask import Flask, jsonify, request, Response, stream_with_context, send_from_directory
from flask_cors import CORS

from database.mongodb import (
    collection,
    save_paper_metadata,
    rate_paper_db,
    soft_delete_paper_db,
    restore_paper_db,
    permanent_delete_paper_db,
    permanent_delete_all_trash_db,
    toggle_star_paper_db,
    add_notification_db,
    get_notifications_db,
    clear_all_data_db,
    get_papers_by_status
)
from services.arxiv_fetcher import stream_yesterdays_papers_batched, fetch_single_arxiv_paper

app = Flask(__name__)
CORS(app)  # Allow requests from the frontend (HTML/JS)


# ============================================================
# GET /
# Serves the static frontend index.html page at root
# ============================================================
@app.route("/", methods=["GET"])
def serve_index():
    return send_from_directory("frontend", "index.html")


# Helper to retrieve a paper's title by DOI (short ID) from MongoDB
def _get_paper_title_by_doi(doi):
    if collection is None:
        return "Unknown Paper"
    paper = collection.find_one({"doi": doi})
    if paper:
        return paper.get("title", "Unknown Paper")
    return "Unknown Paper"


# ============================================================
# GET /papers
# Query params: ?status=active|deleted|starred
# Returns filtered list of papers sorted by publication date
# ============================================================
@app.route("/papers", methods=["GET"])
def get_papers():
    try:
        status = request.args.get("status", "active")
        papers = get_papers_by_status(status)
        return jsonify({
            "success": True,
            "count":   len(papers),
            "papers":  papers
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================================
# GET /fetch
# Streams yesterday's papers live, saving them to DB with complete metadata.
# ============================================================
@app.route("/fetch", methods=["GET"])
def fetch_papers_stream():
    date_str = request.args.get("date")  # Parse optional custom target date YYYY-MM-DD
    def generate():
        import time
        total_new        = 0
        total_duplicates = 0

        try:
            for batch in stream_yesterdays_papers_batched(date_str):
                if batch == "ALREADY_CRAWLED":
                    yield f"data: {json.dumps({'error': 'No papers left to fetch', 'already_crawled': True})}\n\n"
                    return

                # Process and stream papers in smaller sub-batches of 5 to create a beautiful live chatbot-like typewriter streaming effect
                sub_batch_size = 5
                sub_batch = []

                for paper in batch:
                    # Save complete metadata to DB
                    saved = save_paper_metadata(paper)
                    if saved:
                        total_new += 1
                        paper["status"] = "new"
                        sub_batch.append(paper)
                    else:
                        total_duplicates += 1
                        paper["status"] = "duplicate"
                        # Fetch existing document to stream full info to frontend
                        existing = collection.find_one({"doi": paper["doi"]})
                        if existing:
                            existing["_id"] = str(existing["_id"])
                            existing["status"] = "duplicate"
                            sub_batch.append(existing)
                        else:
                            paper["status"] = "duplicate"
                            sub_batch.append(paper)

                    # If sub-batch is full, yield it immediately
                    if len(sub_batch) >= sub_batch_size:
                        event_data = {
                            "batch":      sub_batch,
                            "batch_new":  len([p for p in sub_batch if p["status"] == "new"]),
                            "batch_dup":  len([p for p in sub_batch if p["status"] == "duplicate"]),
                            "total_new":  total_new,
                            "total_dup":  total_duplicates
                        }
                        yield f"data: {json.dumps(event_data)}\n\n"
                        sub_batch = []
                        # Add a tiny delay to ensure a smooth, premium chatbot-like typewriter effect
                        time.sleep(0.02)

                # Yield any remaining papers in the final sub-batch
                if sub_batch:
                    event_data = {
                        "batch":      sub_batch,
                        "batch_new":  len([p for p in sub_batch if p["status"] == "new"]),
                        "batch_dup":  len([p for p in sub_batch if p["status"] == "duplicate"]),
                        "total_new":  total_new,
                        "total_dup":  total_duplicates
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        yield f"data: {json.dumps({'done': True, 'new': total_new, 'duplicates': total_duplicates})}\n\n"

    headers = {
        "Cache-Control":    "no-cache",
        "X-Accel-Buffering": "no",
        "Content-Type":     "text/event-stream",
        "Access-Control-Allow-Origin": "*"
    }
    return Response(stream_with_context(generate()), headers=headers)


# ============================================================
# POST /rate
# Body: { "doi": "...", "username": "...", "rating": 5 }
# Rates a paper on behalf of a user and adds a global notification.
# ============================================================
@app.route("/rate", methods=["POST"])
def rate():
    data = request.get_json() or {}
    doi      = data.get("doi")
    username = data.get("username")
    rating   = data.get("rating")

    if not doi or not username or rating is None:
        return jsonify({"success": False, "message": "Missing doi, username, or rating fields."}), 400

    result = rate_paper_db(doi, username, rating)
    if result["success"]:
        # Log notification
        title = _get_paper_title_by_doi(doi)
        add_notification_db("rate", username, doi, title, rating=rating)
        return jsonify(result), 200
    else:
        return jsonify(result), 400


# ============================================================
# POST /delete-paper
# Body: { "doi": "...", "username": "..." }
# Soft-deletes a paper (moves to Temporary Memory / Trash)
# ============================================================
@app.route("/delete-paper", methods=["POST"])
def delete_paper():
    data = request.get_json() or {}
    doi      = data.get("doi")
    username = data.get("username")

    if not doi or not username:
        return jsonify({"success": False, "message": "Missing doi or username."}), 400

    title = _get_paper_title_by_doi(doi)
    success = soft_delete_paper_db(doi, username)
    if success:
        add_notification_db("delete", username, doi, title)
        return jsonify({"success": True, "message": "Paper soft-deleted successfully."}), 200
    return jsonify({"success": False, "message": "Failed to soft-delete paper."}), 400


# ============================================================
# POST /restore-paper
# Body: { "doi": "...", "username": "..." }
# Restores a paper from trash to the active feed
# ============================================================
@app.route("/restore-paper", methods=["POST"])
def restore_paper():
    data = request.get_json() or {}
    doi      = data.get("doi")
    username = data.get("username")

    if not doi or not username:
        return jsonify({"success": False, "message": "Missing doi or username."}), 400

    title = _get_paper_title_by_doi(doi)
    success = restore_paper_db(doi, username)
    if success:
        add_notification_db("restore", username, doi, title)
        return jsonify({"success": True, "message": "Paper restored successfully."}), 200
    return jsonify({"success": False, "message": "Failed to restore paper."}), 400


# ============================================================
# POST /delete-permanent
# Body: { "doi": "..." }
# Permanently removes a paper from MongoDB
# ============================================================
@app.route("/delete-permanent", methods=["POST"])
def delete_permanent():
    data = request.get_json() or {}
    doi = data.get("doi")

    if not doi:
        return jsonify({"success": False, "message": "Missing doi."}), 400

    success = permanent_delete_paper_db(doi)
    if success:
        return jsonify({"success": True, "message": "Paper permanently deleted."}), 200
    return jsonify({"success": False, "message": "Failed to delete paper permanently."}), 400


# ============================================================
# POST /delete-all-permanent
# Body: {}
# Permanently clears all soft-deleted papers from Trash
# ============================================================
@app.route("/delete-all-permanent", methods=["POST"])
def delete_all_permanent():
    success = permanent_delete_all_trash_db()
    if success:
        return jsonify({"success": True, "message": "All trash cleared permanently."}), 200
    return jsonify({"success": False, "message": "Failed to clear trash."}), 400


# ============================================================
# POST /star
# Body: { "doi": "...", "starred": true|false }
# Toggle starred status globally
# ============================================================
@app.route("/star", methods=["POST"])
def star_paper():
    data = request.get_json() or {}
    doi     = data.get("doi")
    starred = data.get("starred")

    if not doi or starred is None:
        return jsonify({"success": False, "message": "Missing doi or starred fields."}), 400

    success = toggle_star_paper_db(doi, starred)
    if success:
        status_word = "starred" if starred else "unstarred"
        return jsonify({"success": True, "message": f"Paper globally {status_word} successfully."}), 200
    return jsonify({"success": False, "message": "Failed to toggle star."}), 400


# ============================================================
# POST /add-paper
# Body: { "identifier": "...", "username": "..." }
# Manually fetches and injects a single paper. If already deleted, restores it.
# ============================================================
@app.route("/add-paper", methods=["POST"])
def add_paper():
    data = request.get_json() or {}
    identifier = data.get("identifier")
    username   = data.get("username")

    if not identifier or not username:
        return jsonify({"success": False, "message": "Missing identifier or username."}), 400

    # Query arXiv details
    paper = fetch_single_arxiv_paper(identifier)
    if not paper:
        return jsonify({"success": False, "message": "Could not find or fetch paper metadata from arXiv. Please verify the ID or URL."}), 400

    doi = paper["doi"]
    title = paper["title"]

    # Check if exists in DB
    existing = collection.find_one({"doi": doi})
    if existing:
        if existing.get("deleted"):
            # Restore it if it was previously soft-deleted
            restore_paper_db(doi, username)
            collection.update_one({"doi": doi}, {"$set": {"manual": True}})
            add_notification_db("restore", username, doi, title)
            return jsonify({
                "success": True,
                "message": f"Paper '{title}' restored from Temporary Memory.",
                "paper": {**existing, "deleted": False, "manual": True, "_id": str(existing["_id"])}
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Paper already exists in the team's feeds."
            }), 400

    # Insert brand new
    paper["manual"] = True
    success = save_paper_metadata(paper)
    if success:
        add_notification_db("add", username, doi, title)
        # Fetch the newly created document
        new_doc = collection.find_one({"doi": doi})
        new_doc["_id"] = str(new_doc["_id"])
        return jsonify({
            "success": True,
            "message": f"Successfully added paper: {title}",
            "paper": new_doc
        }), 200

    return jsonify({"success": False, "message": "Failed to save the paper to the database."}), 500


# ============================================================
# GET /notifications
# Returns recent 50 activity logs for the team
# ============================================================
@app.route("/notifications", methods=["GET"])
def get_notifications():
    try:
        logs = get_notifications_db()
        return jsonify({
            "success": True,
            "count":   len(logs),
            "notifications": logs
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500



# ============================================================
# GET /firebase-config
# Returns Firebase Web Credentials loaded securely from git-ignored .env
# ============================================================
@app.route("/firebase-config", methods=["GET"])
def get_firebase_config():
    return jsonify({
        "apiKey":            os.getenv("FIREBASE_API_KEY", ""),
        "authDomain":        os.getenv("FIREBASE_AUTH_DOMAIN", ""),
        "projectId":         os.getenv("FIREBASE_PROJECT_ID", ""),
        "storageBucket":     os.getenv("FIREBASE_STORAGE_BUCKET", ""),
        "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID", ""),
        "appId":             os.getenv("FIREBASE_APP_ID", "")
    }), 200



# ============================================================
# POST /clear-database
# Body: {}
# Wipes all database data (papers and notifications collections)
# ============================================================
@app.route("/clear-database", methods=["POST"])
def clear_database():
    success = clear_all_data_db()
    if success:
        return jsonify({"success": True, "message": "Database wiped successfully!"}), 200
    return jsonify({"success": False, "message": "Failed to wipe database collections."}), 500


# ============================================================
# Run the Flask server
# Port 5001 — macOS AirPlay occupies port 5000
# ============================================================

if __name__ == "__main__":
    print("Starting arXiv Research Pipeline API...")
    print("Endpoints:")
    print("  GET  http://localhost:5001/papers  -> All saved papers")
    print("  GET  http://localhost:5001/fetch   -> Stream & save yesterday's papers (SSE)")
    print("  POST http://localhost:5001/rate    -> Rate a paper { link, rating }")
    print("  POST http://localhost:5001/clear-database -> Wipe MongoDB collections")
    app.run(debug=True, host="0.0.0.0", port=5001, threaded=True)
