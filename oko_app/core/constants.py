"""Application constants for OKO БОД Manager."""

from __future__ import annotations

# ── Hardware thresholds ──────────────────────────────────────────────────────

# VIBRO sensor valid range (ohms)
VIBRO_MIN = 2000
VIBRO_MAX = 3500

# SPK sensor valid range (ohms)
SPK_MIN = 2000
SPK_MAX = 3500

# GSM signal threshold (0-31 scale)
GSM_GOOD_SIGNAL = 14

# ── Calibration ──────────────────────────────────────────────────────────────

# Calibration timeout in seconds
CALIBRATION_TIMEOUT = 30

# ── GPS ──────────────────────────────────────────────────────────────────────

# GPS update throttle (seconds)
GPS_UPDATE_INTERVAL = 1.0

# ── Terminal ─────────────────────────────────────────────────────────────────

# String deduplication window (seconds)
TERMINAL_DEDUP_WINDOW = 0.1

# ── Connection ───────────────────────────────────────────────────────────────

# WiFi default settings (ТД платы: OKO_XXXXXX, пароль 222333444 — см. руководство, разд. 7–8)
WIFI_DEFAULT_IP = "192.168.4.1"
WIFI_DEFAULT_PORT = 1234

# Port scan interval (milliseconds)
PORT_SCAN_INTERVAL = 3000

# ── LED timing ───────────────────────────────────────────────────────────────

# LED blink duration on event (milliseconds)
LED_BLINK_DURATION = 300
