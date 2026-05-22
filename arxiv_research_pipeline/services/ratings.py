# ============================================================
# OLD CODE (Auto-calculated relevance/importance scores) - KEPT FOR REFERENCE
# ============================================================

# from config import KEYWORDS

# def add_rating(paper):
#     text = (
#         paper.get("title", "") + " " +
#         paper.get("abstract", "")
#     ).lower()

#     matched_keywords = paper.get("matched_keywords", [])
#     unique_matches = len(matched_keywords)
#     total_keyword_occurrences = sum(
#         text.count(keyword.lower()) for keyword in KEYWORDS
#     )

#     if unique_matches == 0:
#         relevance_score = 0
#         importance_score = 0
#     else:
#         relevance_score = min(100, unique_matches * 12 + total_keyword_occurrences * 3)
#         importance_score = min(100, unique_matches * 10 + total_keyword_occurrences * 2)

#     paper["relevance_score"] = relevance_score
#     paper["importance_score"] = importance_score

#     return paper

# ============================================================
# NEW CODE - Manual rating by team member (1 to 5 stars)
# Uses arXiv "link" as the unique identifier (always present,
# unlike "doi" which is often unavailable for arXiv papers).
# No threshold logic applied yet — just saves the rating.
# ============================================================

from pymongo.errors import PyMongoError


def rate_paper(collection, link, rating):
    """
    Save a team member's rating for a paper identified by its arXiv link.

    Args:
        collection : pymongo Collection object (papers collection)
        link       : The arXiv link URL of the paper (e.g. https://arxiv.org/abs/2605.xxxxx)
        rating     : Integer rating between 1 and 5

    Returns:
        dict with "success" (bool) and "message" (str)
    """

    # Validate rating range
    if not isinstance(rating, (int, float)) or not (1 <= rating <= 5):
        return {
            "success": False,
            "message": "Rating must be a number between 1 and 5."
        }

    if not link:
        return {
            "success": False,
            "message": "Invalid or missing paper link."
        }

    try:
        result = collection.update_one(
            {"link": link},
            {"$set": {"rating": rating}}
        )

        if result.matched_count == 0:
            return {
                "success": False,
                "message": f"No paper found with link: {link}"
            }

        print(f"Rating {rating} saved for paper: {link}")

        return {
            "success": True,
            "message": f"Rating {rating} saved successfully."
        }

    except PyMongoError as e:
        print(f"MongoDB error while saving rating: {e}")
        return {
            "success": False,
            "message": f"Database error: {str(e)}"
        }