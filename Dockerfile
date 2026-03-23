FROM python:3.13.5-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
COPY frontend/app.py ./frontend/
COPY frontend/src/ ./frontend/src/
COPY api/src/ ./api/src/

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app/api/src:/app/frontend/src

WORKDIR /app/frontend

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
