"""
PRO File Server
Serves videos, PDFs, notes and large files.

Features:
- Render compatible
- Multi-threaded
- Health endpoint
- Safe file serving
- Download headers
- Supports MP4, MKV, PDF, ZIP and more
"""

import logging
import mimetypes
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import unquote

logger = logging.getLogger("bot.file_server")

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────
# THREADED SERVER
# ─────────────────────────────────────────────

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


# ─────────────────────────────────────────────
# FILE HANDLER
# ─────────────────────────────────────────────

class FileHandler(SimpleHTTPRequestHandler):

    def do_GET(self):

        # Health endpoint
        if self.path in ("/health", "/healthz"):

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/plain"
            )
            self.end_headers()

            self.wfile.write(b"OK")
            return

        return super().do_GET()

    def translate_path(self, path):

        path = unquote(path)

        if path.startswith("/file/"):

            filename = path.replace(
                "/file/",
                "",
                1
            )

            # Prevent path traversal
            filename = Path(filename).name

            return str(
                DOWNLOAD_DIR / filename
            )

        return str(DOWNLOAD_DIR)

    def guess_type(self, path):

        mime, _ = mimetypes.guess_type(path)

        if mime:
            return mime

        return "application/octet-stream"

    def send_head(self):

        file_path = Path(
            self.translate_path(self.path)
        )

        if not file_path.exists():

            self.send_error(
                404,
                "File not found"
            )

            return None

        try:

            file = open(
                file_path,
                "rb"
            )

            self.send_response(200)

            self.send_header(
                "Content-Type",
                self.guess_type(str(file_path))
            )

            self.send_header(
                "Content-Length",
                str(file_path.stat().st_size)
            )

            self.send_header(
                "Content-Disposition",
                f'attachment; filename="{file_path.name}"'
            )

            self.send_header(
                "Accept-Ranges",
                "bytes"
            )

            self.end_headers()

            return file

        except Exception:

            logger.exception(
                "Failed serving file %s",
                file_path
            )

            self.send_error(
                500,
                "Internal Server Error"
            )

            return None

    def end_headers(self):

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Cache-Control",
            "public, max-age=86400"
        )

        super().end_headers()

    def log_message(self, format, *args):
        # Disable default spam logging
        pass


# ─────────────────────────────────────────────
# START SERVER
# ─────────────────────────────────────────────

def run_file_server(port: int = 8000):

    try:

        server = ThreadingHTTPServer(
            ("0.0.0.0", port),
            FileHandler
        )

        logger.info(
            "File server running on port %s",
            port
        )

        server.serve_forever()

    except Exception as e:

        logger.exception(
            "File server crashed: %s",
            e
        )
