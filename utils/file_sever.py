"""
Simple file server for large video delivery (Render-safe).
Used when Telegram limit is exceeded.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import logging

logger = logging.getLogger("bot.file_server")

FILES_DIR = "downloads"


class FileHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            filename = self.path.replace("/file/", "")
            file_path = os.path.join(FILES_DIR, filename)

            if not os.path.exists(file_path):
                self.send_response(404)
                self.end_headers()
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.end_headers()

            with open(file_path, "rb") as f:
                self.wfile.write(f.read())

        except Exception as e:
            logger.error("File server error: %s", e)
            self.send_response(500)
            self.end_headers()


def run_file_server(port: int = 8000):
    server = HTTPServer(("0.0.0.0", port), FileHandler)
    logger.info("File server running on port %d", port)
    server.serve_forever()
