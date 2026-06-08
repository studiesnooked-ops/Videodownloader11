import logging
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, HTTPServer

logger = logging.getLogger("bot.file_server")

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


class FileHandler(SimpleHTTPRequestHandler):

    def translate_path(self, path):
        path = path.lstrip("/")

        # URL: /file/video.mkv
        if path.startswith("file/"):
            filename = path.replace("file/", "", 1)
            return str(DOWNLOAD_DIR / filename)

        return str(DOWNLOAD_DIR)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, format, *args):
        pass


def run_file_server(port=8000):
    server = HTTPServer(("0.0.0.0", port), FileHandler)
    logger.info(f"File server running on port {port}")
    server.serve_forever()
