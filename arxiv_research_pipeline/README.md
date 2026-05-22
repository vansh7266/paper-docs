# Arxiv Research Paper Fetching Pipeline

This project fetches yesterday's research papers from arXiv daily at 1:30 AM IST,
filters papers based on keywords, stores DOI + metadata in MongoDB,
fetches reference paper abstracts, and allows researchers to rate papers.

## Features
- Fetch yesterday's papers from arXiv API
- Keyword & relevance filtering
- Store papers in MongoDB
- Fetch references and abstracts
- Researcher rating system
- Daily automation scheduler

## Tech Stack
- Python
- arXiv API
- MongoDB
- APScheduler
- Requests
- Pandas

## Run Project

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Start MongoDB
Make sure MongoDB is running locally.

### Run Scheduler
```bash
python scheduler.py
```

## Folder Structure
```
arxiv_research_pipeline/
│
├── main.py
├── scheduler.py
├── requirements.txt
├── config.py
├── database/
│   └── mongodb.py
├── services/
│   ├── arxiv_fetcher.py
│   ├── filter_papers.py
│   ├── references.py
│   └── ratings.py
└── data/
    └── papers.json
```