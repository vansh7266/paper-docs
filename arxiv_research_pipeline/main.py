from services.arxiv_fetcher import fetch_yesterdays_papers
from database.mongodb import save_paper


# ============================================================
# OLD CODE (Batched pipeline with filter + references) - KEPT FOR REFERENCE
# ============================================================

# import time
# from services.arxiv_fetcher import fetch_arxiv_papers
# from services.filter_papers import filter_relevant_papers
# from services.references import fetch_references
# from database.mongodb import save_paper

# BATCH_SIZE = 20
# BATCH_DELAY_SECONDS = 100  # 5 minutes

# def run_pipeline():
#     start = 0
#     batch_number = 1
#     total_fetched = 0
#     total_filtered = 0
#     total_saved = 0
#     total_duplicates = 0
#     seen_titles = set()

#     print("Starting batched arXiv extraction...")

#     while True:
#         print(f"\n=== Batch {batch_number}: fetching papers starting at {start} ===")
#         papers = fetch_arxiv_papers(start=start, max_results=BATCH_SIZE)

#         if not papers:
#             print("\nNo more papers returned by the arXiv API.")
#             break

#         batch_fetched = len(papers)
#         total_fetched += batch_fetched

#         print("\nFiltering relevant papers...")
#         filtered = filter_relevant_papers(papers)

#         batch_filtered = len(filtered)
#         total_filtered += batch_filtered

#         batch_saved = 0
#         batch_duplicates = 0

#         for paper in filtered:
#             title = paper.get("title")
#             if title in seen_titles:
#                 print(f"Skipping paper already processed in this run: {title}")
#                 batch_duplicates += 1
#                 continue

#             seen_titles.add(title)

#             refs = fetch_references(paper)
#             paper["references"] = refs

#             print("\n====================================")
#             print(f"Paper Title: {paper['title']}")
#             if refs:
#                 print(f"References found: {len(refs)}")
#                 for idx, ref in enumerate(refs, start=1):
#                     print(f"  [{idx}] {ref.get('title', 'No title')}")
#                     print(f"      Abstract: {ref.get('abstract', 'Not Available')}")
#             else:
#                 print("No references found for this paper.")
#             print("====================================")

#             saved = save_paper(paper)
#             if saved:
#                 batch_saved += 1
#             else:
#                 batch_duplicates += 1

#         total_saved += batch_saved
#         total_duplicates += batch_duplicates

#         print(f"\nBatch {batch_number} summary:")
#         print(f"  Papers fetched this batch: {batch_fetched}")
#         print(f"  Relevant papers this batch: {batch_filtered}")
#         print(f"  New papers saved this batch: {batch_saved}")
#         print(f"  Duplicate papers skipped this batch: {batch_duplicates}")

#         if batch_fetched < BATCH_SIZE:
#             print("\nLast batch was smaller than batch size, assuming all available papers have been fetched.")
#             break

#         batch_number += 1
#         start += BATCH_SIZE

#         print(f"\nWaiting {BATCH_DELAY_SECONDS // 60} minutes before next batch...")
#         time.sleep(BATCH_DELAY_SECONDS)

#     print("\n================ FINAL SUMMARY ================")
#     print(f"Total Papers Fetched: {total_fetched}")
#     print(f"Total Relevant Papers: {total_filtered}")
#     print(f"New Papers Saved: {total_saved}")
#     print(f"Duplicate Papers Skipped: {total_duplicates}")
#     print("\nAll available papers have been extracted for this run.")
#     print("Pipeline completed successfully!")
#     print("================================================")

# ============================================================
# NEW CODE - Simple pipeline: fetch all of yesterday's papers, save to Atlas
# ============================================================

def run_pipeline():
    print("\n========== arXiv Pipeline Started ==========")

    # Step 1: Fetch all of yesterday's papers from arXiv (no filter, no batches)
    papers = fetch_yesterdays_papers()

    if not papers:
        print("No papers fetched. Pipeline exiting.")
        return

    print(f"\nTotal papers fetched: {len(papers)}")

    # Step 2: Save each paper to MongoDB Atlas
    total_saved      = 0
    total_duplicates = 0

    for paper in papers:
        saved = save_paper(paper)
        if saved:
            total_saved += 1
        else:
            total_duplicates += 1

    # Final summary
    print("\n========== Pipeline Complete ==========")
    print(f"  Papers Fetched    : {len(papers)}")
    print(f"  New Papers Saved  : {total_saved}")
    print(f"  Duplicates Skipped: {total_duplicates}")
    print("=======================================")


if __name__ == "__main__":
    run_pipeline()
