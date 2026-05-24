---
title: Moleculyst Hub
emoji: 🧬
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# 🧬 Moleculyst Research Team Hub

This is the secure, production deployment of the **Moleculyst Research Team Hub** hosted on Hugging Face Spaces. It runs our high-performance Flask API serving the curated arXiv preprints pipeline.

### Setup and Deployment

The environment is built using a custom `Dockerfile` that packages the Python server, Gunicorn WSGI server, and serves the static HTML/CSS/JS frontend dynamically at root `/`.

All MongoDB and Firebase credentials are dynamically loaded from environment variables (configured via Settings -> Variables and secrets on Hugging Face).
