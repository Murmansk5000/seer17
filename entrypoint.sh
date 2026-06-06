#!/bin/sh
set -eu

is_true() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

if is_true "${GUI:-false}" || is_true "${VNC:-false}"; then
  export DISPLAY="${DISPLAY:-:0}"
  export HEADLESS=false
  export FIRST_LOGIN_GUI=true
  export LOGIN_WAIT_SECONDS="${LOGIN_WAIT_SECONDS:-900}"

  Xvfb "$DISPLAY" -screen 0 "${VNC_RESOLUTION:-1280x900x24}" -nolisten tcp &
  sleep 1
  fluxbox >/tmp/fluxbox.log 2>&1 &
  x11vnc -display "$DISPLAY" -forever -shared -nopw -listen 0.0.0.0 -rfbport 5900 >/tmp/x11vnc.log 2>&1 &
  websockify --web=/usr/share/novnc 0.0.0.0:6080 localhost:5900 >/tmp/novnc.log 2>&1 &

  echo "GUI mode enabled."
  echo "Open noVNC: http://<unraid-ip>:6080/vnc.html"
fi

exec python /app/autocheckin.py
