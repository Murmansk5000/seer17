FROM mcr.microsoft.com/playwright/python:v1.53.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY autocheckin.py .

ENV DATA_DIR=/data
ENV HEADLESS=true

VOLUME ["/data"]

CMD ["python", "autocheckin.py"]
