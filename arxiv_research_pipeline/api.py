import json
from flask import Flask, jsonify, request, Response, stream_with_context
from flask_cors import CORS

from database.mongodb import collection, get_all_papers, save_paper
from services.ratings import rate_paper
from services.arxiv_fetcher import stream_yesterdays_papers_batched

app = Flask(__name__)
CORS(app)  # Allow requests from the frontend (HTML/JS)


# ============================================================
# GET /papers
# Returns all papers currently stored in the database
# ============================================================

@app.route("/papers", methods=["GET"])
def get_papers():
    try:
        papers = get_all_papers()
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
# Streams yesterday's papers from arXiv live using Server-Sent Events (SSE).
# The frontend connects once and receives papers one by one as they are
# fetched and saved — so the UI starts populating immediately.
# Event format: data: { ...paper fields..., "status": "new"|"duplicate" }
# Final event:  data: { "done": true, "total": N }
# ============================================================

@app.route("/fetch", methods=["GET"])
def fetch_papers_stream():
    def generate():
        total_new        = 0
        total_duplicates = 0

        try:
            # Each iteration of the loop = one arXiv API call = one batch of 100 papers
            for batch in stream_yesterdays_papers_batched():
                batch_new  = []
                batch_dup  = []

                for paper in batch:
                    saved = save_paper(paper)
                    if saved:
                        total_new += 1
                        paper["status"] = "new"
                        batch_new.append(paper)
                    else:
                        total_duplicates += 1
                        paper["status"] = "duplicate"
                        batch_dup.append(paper)

                # Send the whole batch (new + duplicates) in ONE SSE event
                # Frontend receives all 100 at once and renders them together
                event_data = {
                    "batch":      batch_new + batch_dup,
                    "batch_new":  len(batch_new),
                    "batch_dup":  len(batch_dup),
                    "total_new":  total_new,
                    "total_dup":  total_duplicates
                }
                yield f"data: {json.dumps(event_data)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        # Final "done" signal
        yield f"data: {json.dumps({'done': True, 'new': total_new, 'duplicates': total_duplicates})}\n\n"

    headers = {
        "Cache-Control":    "no-cache",
        "X-Accel-Buffering": "no",         # Disable nginx buffering if deployed
        "Content-Type":     "text/event-stream",
        "Access-Control-Allow-Origin": "*"
    }
    return Response(stream_with_context(generate()), headers=headers)


# ============================================================
# POST /rate
# Body: { "link": "https://arxiv.org/abs/...", "rating": 4 }
# Saves a team member's rating (1-5) for a paper.
# Uses the arXiv link as the unique identifier since most
# arXiv papers do not have a DOI until after journal publication.
# ============================================================

@app.route("/rate", methods=["POST"])
def rate():
    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "Request body must be JSON."
        }), 400

    link   = data.get("link")
    rating = data.get("rating")

    if not link:
        return jsonify({
            "success": False,
            "message": "Missing field: link"
        }), 400

    if rating is None:
        return jsonify({
            "success": False,
            "message": "Missing field: rating"
        }), 400

    result = rate_paper(collection, link, rating)

    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


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
    app.run(debug=True, host="0.0.0.0", port=5001, threaded=True)
