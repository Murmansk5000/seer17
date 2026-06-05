FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      ca-certificates \
      chromium \
      fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY autocheckin.py .

ENV DATA_DIR=/data
ENV HEADLESS=true
ENV BROWSER_EXECUTABLE=/usr/bin/chromium

VOLUME ["/data"]

CMD ["python", "autocheckin.py"]
