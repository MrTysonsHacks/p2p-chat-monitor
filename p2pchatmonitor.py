import os
import time
import re
import requests
from pathlib import Path
from datetime import datetime, timedelta

# === CONFIG ===
LOG_DIR = Path(r"C:\Users\User\DreamBot\Logs\DreamBot")  # ← Adjust this to your actual log folder
WEBHOOK_URL = "Webhook Here"
CHECK_INTERVAL = 300  # 5 minutes
CHUNK_LINE_LIMIT = 20  # max lines per embed field
DISCORD_MENTION = "<@User ID Here>"  # use your actual Discord user ID if needed

def get_latest_log_file():
    print(f"Scanning directory: {LOG_DIR}")
    log_files = sorted(LOG_DIR.glob("logfile-*.log"), key=os.path.getmtime, reverse=True)
    print(f"Found: {[f.name for f in log_files]}")
    return log_files[0] if log_files else None

def parse_log_timestamp(line):
    try:
        return datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

def split_chunks(lines, chunk_size):
    for i in range(0, len(lines), chunk_size):
        yield lines[i:i + chunk_size]

def extract_chat_response_segments(lines):
    """
    From the provided lines (already filtered to recent timeframe), find segments that begin with a line containing "CHAT"
    and end with the next subsequent line containing "SLOWLY TYPING RESPONSE". Returns list of segment line lists.
    """
    segments = []
    current_start_idx = None
    for idx, line in enumerate(lines):
        upper = line.upper()
        if "CHAT" in upper and current_start_idx is None:
            current_start_idx = idx
        elif "SLOWLY TYPING RESPONSE" in upper and current_start_idx is not None:
            # include from start to this line
            segment = lines[current_start_idx: idx + 1]
            segments.append(segment)
            current_start_idx = None
    return segments

def send_lines_in_embeds(segments, filename):
    if not segments:
        return

    now = datetime.utcnow().isoformat()
    # flatten each segment into its own chunk grouping if it's too big
    print(f"Preparing {len(segments)} chat/response segments...")
    for seg_idx, segment in enumerate(segments, start=1):
        # further split if longer than CHUNK_LINE_LIMIT
        for chunk_idx, chunk in enumerate(split_chunks(segment, CHUNK_LINE_LIMIT), start=1):
            cleaned = [line.strip() for line in chunk]
            field = {
                "name": f"Segment {seg_idx} Part {chunk_idx}",
                "value": "```" + "\n".join(cleaned)[:1000] + "\n```",
                "inline": False
            }
            embed = {
                "title": "P2P Log CHAT/SLOWLY TYPING RESPONSE",
                "description": f"Captured segment from `{filename}` containing CHAT → SLOWLY TYPING RESPONSE", 
                "color": 0x7289da,
                "timestamp": now,
                "fields": [field]
            }
            payload = {
                "content": f"{DISCORD_MENTION} – detected conversation segment.", 
                "embeds": [embed]
            }
            response = requests.post(WEBHOOK_URL, json=payload)
            if response.status_code != 204:
                print(f"Failed to send: {response.status_code} - {response.text}")
            else:
                print(f"Sent segment {seg_idx} chunk {chunk_idx}")

def main():
    print("Starting log monitor daemon (filtered for CHAT → SLOWLY TYPING RESPONSE segments)...")
    last_file = None

    while True:
        try:
            latest = get_latest_log_file()
            if not latest:
                print("No log files found.")
                time.sleep(CHECK_INTERVAL)
                continue

            if latest != last_file:
                print(f"📄 New log file detected: {latest.name}")
                last_file = latest

            with open(latest, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()

            now = datetime.now()
            cutoff = now - timedelta(minutes=5)
            recent_lines = []

            for line in all_lines:
                ts = parse_log_timestamp(line)
                if ts and ts > cutoff:
                    recent_lines.append(line)

            segments = extract_chat_response_segments(recent_lines)
            if segments:
                print(f"📨 Found {len(segments)} matching CHAT→SLOWLY TYPING RESPONSE segment(s); sending to Discord...")
                send_lines_in_embeds(segments, latest.name)
            else:
                print("No matching CHAT→SLOWLY TYPING RESPONSE segments in the last 5 minutes.")

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()

