FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      ca-certificates \
      chromium \
      fonts-noto-cjk \
      fluxbox \
      novnc \
      websockify \
      x11vnc \
      xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY autocheckin.py entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

ENV DATA_DIR=/data
ENV HEADLESS=true
ENV BROWSER_EXECUTABLE=/usr/bin/chromium
ENV DISPLAY=:0
ENV VNC_RESOLUTION=1280x900x24

VOLUME ["/data"]
EXPOSE 6080 5900

ENTRYPOINT ["/app/entrypoint.sh"]
