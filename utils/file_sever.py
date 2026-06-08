"""
Simple file server for downloaded videos and PDF notes.
Used for files too large to send via Telegram.
"""

import os
import logging
from pathlib import Path
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

logger = logging.getLogger("bot.file_server")

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


class FileHandler(SimpleHTTPRequestHandler):

    def translate_path(self, path):
        path = path.lstrip("/")

        if path.startswith("file/"):
            filename = path.replace("file/", "", 1)
            return str(DOWNLOAD_DIR / filename)

        return str(DOWNLOAD_DIR)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, format, *args):
        pass


def run_file_server(port: int = 8000):

    try:
        with TCPServer(("0.0.0.0", port), FileHandler) as server:
            logger.info(
                "File server running on http://0.0.0.0:%d",
                port
            )
            server.serve_forever()

    except Exception as e:
        logger.exception(
            "File server crashed: %s",
            e
        )
