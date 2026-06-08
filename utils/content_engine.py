"""
Smart Content Engine v1
Classifies and normalizes Appx course links
"""

import re
from urllib.parse import urlparse, unquote
from typing import Dict, List


# -----------------------------
# FILE TYPE DETECTOR
# -----------------------------
def detect_type(url: str) -> str:

    u = url.lower()

    if ".pdf" in u:
        return "pdf"

    if ".mkv" in u or ".mp4" in u:
        return "video"

    if ".m3u8" in u:
        return "video"

    if ".zip" in u:
        return "video"   # Appx uses zip for streaming chunks

    return "video"


# -----------------------------
# CLEAN URL (REMOVE NOISE)
# -----------------------------
def clean_url(url: str) -> str:
    return url.strip().replace(" ", "")


# -----------------------------
# EXTRACT NAME
# -----------------------------
def get_name(url: str) -> str:

    try:
        path = urlparse(url).path
        name = path.split("/")[-1]
        name = unquote(name)

        if not name:
            name = "file"

        return name

    except Exception:
        return "file"


# -----------------------------
# MAIN PARSER
# -----------------------------
def parse_course_text(text: str) -> Dict:

    lines = text.splitlines()

    videos = []
    pdfs = []

    for line in lines:

        line = line.strip()

        if not line or ":" not in line:
            continue

        try:
            title, url = line.split(":", 1)
        except:
            continue

        url = clean_url(url)

        if not url.startswith("http"):
            continue

        file_type = detect_type(url)

        item = {
            "title": title.strip(),
            "url": url,
            "name": get_name(url)
        }

        if file_type == "pdf":
            pdfs.append(item)
        else:
            videos.append(item)

    return {
        "videos": videos,
        "pdfs": pdfs
    }
