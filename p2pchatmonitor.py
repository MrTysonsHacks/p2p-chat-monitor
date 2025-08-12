import os
import time
import re
import requests
from pathlib import Path
from datetime import datetime, timedelta

class Color:
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    RESET = '\033[0m'

# === CONFIG ===
LOG_DIR = Path(r"C:\Users\USER HERE\DreamBot\Logs\ACCOUNT NICKNAME")  # Adjust to your log folder
WEBHOOK_URL = "DISCORD WEBHOOK"
CHUNK_LINE_LIMIT = 20  # max lines per embed field
DISCORD_MENTION = "<@USERIDHERE>"

# Embed colors
COLOR_DEFAULT = 0x7289da  # Discord blurple
COLOR_QUEST = 0xFFD700    # Gold

last_processed_times = {}

def get_monitor_preferences():
    print(Color.CYAN + "=== Monitor Preferences ===" + Color.RESET)
    chat_pref = input("Monitor chat events? (y/n): ").strip().lower().startswith("y")
    quest_pref = input("Monitor quest completions? (y/n): ").strip().lower().startswith("y")
    if not chat_pref and not quest_pref:
        print(Color.YELLOW + "⚠ No segment types selected — nothing will be monitored!" + Color.RESET)
    return chat_pref, quest_pref

def get_check_interval():
    print(Color.CYAN + "=== Check Interval Configuration ===" + Color.RESET)
    user_input = input("Enter the check interval in minutes (default 5): ").strip()
    try:
        interval = float(user_input)
        if interval <= 0:
            raise ValueError()
    except ValueError:
        print(Color.YELLOW + "Invalid input; defaulting to 5 minutes." + Color.RESET)
        interval = 5
    if interval < 5:
        print(Color.RED + "Warning: check intervals less than 5 minutes may cause instability with larger log files." + Color.RESET)
    print(f"Check interval set to {interval} minute(s).")
    return int(interval * 60)

def get_latest_log_file():
    log_files = sorted(LOG_DIR.glob("logfile-*.log"), key=os.path.getmtime, reverse=True)
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
    segments = []
    current_start_idx = None
    for idx, line in enumerate(lines):
        upper = line.upper()
        if "CHAT" in upper and current_start_idx is None:
            current_start_idx = idx
        elif ("SLOWLY TYPING RESPONSE" in upper or "BAD RESPONSE" in upper) and current_start_idx is not None:
            segment = lines[current_start_idx: idx + 1]
            segments.append(segment)
            current_start_idx = None
    return segments

def strip_color_tags(text):
    return re.sub(r"<col=.*?>(.*?)</col>", r"\1", text)

def extract_quest_completions(lines):
    quest_segments = []
    for line in lines:
        if "[GAME] Congratulations, you've completed a quest" in line:
            cleaned_line = strip_color_tags(line.strip())
            quest_match = re.search(r"quest: (.+)", cleaned_line)
            if quest_match:
                quest_name = quest_match.group(1).strip()
                formatted_line = f"[GAME] 🏆 Congratulations, you've completed a quest: **{quest_name}**"
            else:
                formatted_line = cleaned_line
            quest_segments.append([formatted_line])
    return quest_segments

def send_lines_in_embeds(segments, filename, embed_title, embed_color):
    if not segments:
        return

    now = datetime.now().isoformat()
    print(f"Preparing {len(segments)} segment(s) for Discord...")
    for seg_idx, segment in enumerate(segments, start=1):
        for chunk_idx, chunk in enumerate(split_chunks(segment, CHUNK_LINE_LIMIT), start=1):
            cleaned = [line.strip() for line in chunk]
            field = {
                "name": f"Segment {seg_idx} Part {chunk_idx}",
                "value": "```" + "\n".join(cleaned)[:1000] + "\n```",
                "inline": False
            }
            embed = {
                "title": embed_title,
                "description": f"Captured segment from `{filename}`",
                "color": embed_color,
                "timestamp": now,
                "fields": [field]
            }
            payload = {
                "content": f"{DISCORD_MENTION} – detected {embed_title.lower()}.",
                "embeds": [embed]
            }
            response = requests.post(WEBHOOK_URL, json=payload)
            if response.status_code != 204:
                print(f"Failed to send: {response.status_code} - {response.text}")
            else:
                print(f"Sent segment {seg_idx} chunk {chunk_idx}")

def main():
    print("Starting log monitor daemon...")
    print(Color.MAGENTA + "Scrapped together by @CaS5" + Color.RESET)
    monitor_chat, monitor_quests = get_monitor_preferences()
    check_interval = get_check_interval()
    last_file = None

    while True:
        try:
            latest = get_latest_log_file()
            if not latest:
                print("No log files found.")
                time.sleep(check_interval)
                continue

            # Detect new file
            if latest != last_file:
                print(f"📄 New log file detected: {latest.name}")
                last_file = latest
                last_processed_times[latest.name] = None

            with open(latest, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()

            now = datetime.now()

            cutoff_time = last_processed_times.get(latest.name)
            new_lines = []
            for line in all_lines:
                ts = parse_log_timestamp(line)
                if ts and (cutoff_time is None or ts > cutoff_time):
                    new_lines.append(line)

            if not new_lines:
                print(Color.YELLOW + f"No new log entries since last check. ({check_interval // 60} minutes)" + Color.RESET)
            else:
                recent_lines = [
                    line for line in new_lines
                    if (ts := parse_log_timestamp(line)) and ts > now - timedelta(minutes=check_interval / 60)
                ]

                chat_segments = []
                quest_segments = []

                if monitor_chat:
                    chat_segments = extract_chat_response_segments(recent_lines)
                    if chat_segments:
                        print(Color.GREEN + f"📨 Found {len(chat_segments)} chat event(s)" + Color.RESET)

                if monitor_quests:
                    quest_segments = extract_quest_completions(recent_lines)
                    if quest_segments:
                        print(Color.GREEN + f"🏆 Found {len(quest_segments)} quest completion(s)" + Color.RESET)

                if not chat_segments and not quest_segments:
                    print(Color.YELLOW + f"No new chat or quest events detected in the last check interval. ({check_interval // 60} minutes)" + Color.RESET)

                if chat_segments:
                    send_lines_in_embeds(chat_segments, latest.name, "P2P Chat Event", COLOR_DEFAULT)
                if quest_segments:
                    send_lines_in_embeds(quest_segments, latest.name, "P2P Quest Completion", COLOR_QUEST)

                max_ts = max((parse_log_timestamp(line) for line in new_lines if parse_log_timestamp(line)), default=cutoff_time)
                if max_ts:
                    last_processed_times[latest.name] = max_ts

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(check_interval)

if __name__ == "__main__":
    main()
