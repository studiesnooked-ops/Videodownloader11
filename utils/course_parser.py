import re

PDF_RE = re.compile(r"\.pdf(\?|$)")
VIDEO_HINTS = re.compile(r"\.(mp4|mkv|m3u8|ts|zip)(\?|$)")

def parse_course(text: str):
    videos, pdfs, files = [], [], []

    for line in text.splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if PDF_RE.search(line):
            pdfs.append(line)

        elif VIDEO_HINTS.search(line) or "m3u8" in line:
            videos.append(line)

        else:
            files.append(line)

    return {
        "videos": videos,
        "pdfs": pdfs,
        "files": files
    }
