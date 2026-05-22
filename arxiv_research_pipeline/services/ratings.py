from config import KEYWORDS


def add_rating(paper):
    text = (
        paper.get("title", "") + " " +
        paper.get("abstract", "")
    ).lower()

    matched_keywords = paper.get("matched_keywords", [])
    unique_matches = len(matched_keywords)
    total_keyword_occurrences = sum(
        text.count(keyword.lower()) for keyword in KEYWORDS
    )

    if unique_matches == 0:
        relevance_score = 0
        importance_score = 0
    else:
        relevance_score = min(100, unique_matches * 12 + total_keyword_occurrences * 3)
        importance_score = min(100, unique_matches * 10 + total_keyword_occurrences * 2)

    paper["relevance_score"] = relevance_score
    paper["importance_score"] = importance_score

    return paper