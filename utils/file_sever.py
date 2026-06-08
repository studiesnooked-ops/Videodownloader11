"""
Simple file server for large downloads (MKV / MP4 / PDF).
Render-safe static file host.
"""

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

        # serve only downloads folder
        file_path = DOWNLOAD_DIR / path
        return str(file_path)

    def end_headers(self):
        # allow browser access
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, format, *args):
        # silence logs
        return


def run_file_server(port: int = 8000):
    """
    Runs simple HTTP server for large files.
    Used when Telegram cannot send >50MB files.
    """

    try:
        with TCPServer(("0.0.0.0", port), FileHandler) as httpd:
            logger.info(f"📁 File server running on port {port}")
            httpd.serve_forever()

    except Exception as e:
        logger.exception(f"File server crashed: {e}")
