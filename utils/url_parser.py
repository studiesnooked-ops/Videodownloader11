"""
Advanced URL parser
Supports:
- Video URLs
- M3U8 streams
- PDF Notes
- Images / Thumbnails
"""

import re
from urllib.parse import urlparse
from typing import List, Dict

# --------------------------------------------------
# URL REGEX
# --------------------------------------------------

_URL_RE = re.compile(
    r"https?://[a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+",
    re.IGNORECASE,
)

# --------------------------------------------------
# VIDEO PATTERNS
# --------------------------------------------------

_VIDEO_EXTENSIONS = re.compile(
    r"\.(mp4|mkv|avi|mov|m4v|webm|flv|wmv|mpeg|mpg|ts|m3u8)(\?|$|#)",
    re.IGNORECASE,
)

# --------------------------------------------------
# PDF NOTES
# --------------------------------------------------

_PDF_EXTENSIONS = re.compile(
    r"\.(pdf)(\?|$|#)",
    re.IGNORECASE,
)

# --------------------------------------------------
# THUMBNAILS
# --------------------------------------------------

_IMAGE_EXTENSIONS = re.compile(
    r"\.(jpg|jpeg|png|webp)(\?|$|#)",
    re.IGNORECASE,
)

# --------------------------------------------------
# VIDEO DETECTION
# --------------------------------------------------

def is_video_url(url: str) -> bool:
    parsed = urlparse(url)

    path = parsed.path.lower()
    query = parsed.query.lower()

    combined = path + "?" + query

    return bool(_VIDEO_EXTENSIONS.search(combined))


# --------------------------------------------------
# PDF DETECTION
# --------------------------------------------------

def is_pdf_url(url: str) -> bool:
    parsed = urlparse(url)

    path = parsed.path.lower()
    query = parsed.query.lower()

    combined = path + "?" + query

    return bool(_PDF_EXTENSIONS.search(combined))


# --------------------------------------------------
# IMAGE DETECTION
# --------------------------------------------------

def is_image_url(url: str) -> bool:
    parsed = urlparse(url)

    path = parsed.path.lower()
    query = parsed.query.lower()

    combined = path + "?" + query

    return bool(_IMAGE_EXTENSIONS.search(combined))


# --------------------------------------------------
# MAIN PARSER
# --------------------------------------------------

def parse_content(text: str) -> Dict[str, List[str]]:

    videos = []
    pdfs = []
    images = []

    seen = set()

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            continue

        matches = _URL_RE.findall(line)

        for url in matches:

            url = url.rstrip(".,;)'\"")

            if url in seen:
                continue

            seen.add(url)

            if is_video_url(url):
                videos.append(url)

            elif is_pdf_url(url):
                pdfs.append(url)

            elif is_image_url(url):
                images.append(url)

    return {
        "videos": videos,
        "pdfs": pdfs,
        "images": images,
    }


# --------------------------------------------------
# OLD COMPATIBILITY FUNCTION
# --------------------------------------------------

def parse_video_urls(text: str) -> List[str]:
    return parse_content(text)["videos"]


# --------------------------------------------------
# FORMATTER
# --------------------------------------------------

def format_url_list(urls: List[str]) -> str:

    lines = []

    for i, url in enumerate(urls, start=1):

        try:
            parsed = urlparse(url)
            name = parsed.path.split("/")[-1] or url
        except Exception:
            name = url

        lines.append(f"{i}. {name}")

    return "\n".join(lines)
