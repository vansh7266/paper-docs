# Use official lightweight Python 3.10 image
FROM python:3.10-slim

# Set workspace directory inside container
WORKDIR /app

# Copy requirements and install dependencies
COPY arxiv_research_pipeline/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install gunicorn production WSGI server
RUN pip install --no-cache-dir gunicorn

# Copy all codebase into the container
COPY arxiv_research_pipeline/ .

# Expose the default port Hugging Face Spaces expects (7860)
EXPOSE 7860

# Start Flask via Gunicorn bound to port 7860 with 600 seconds (10 minutes) worker timeout
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--timeout", "600", "api:app"]
