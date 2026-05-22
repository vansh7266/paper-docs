from config import KEYWORDS

def filter_relevant_papers(papers):
    filtered = []

    for paper in papers:
        text = (
            paper.get("title", "") + " " +
            paper.get("abstract", "")
        ).lower()

        print("\nChecking Paper:")
        print(paper.get("title"))

        matched_keywords = []

        for keyword in KEYWORDS:
            if keyword.lower() in text:
                matched_keywords.append(keyword)
                print(f"Matched Keyword: {keyword}")

        if matched_keywords:
            paper["matched_keywords"] = matched_keywords
            paper["keyword_match_count"] = len(matched_keywords)
            filtered.append(paper)

    print(f"\nTotal Filtered Papers: {len(filtered)}")

    return filtered