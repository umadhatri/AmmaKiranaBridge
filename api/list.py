import cgi
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler

from app import make_response


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                },
            )
            self.respond(make_response(form))
        except Exception as error:
            self.respond({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    def do_GET(self):
        self.respond({"error": "Use POST for /api/list."}, HTTPStatus.METHOD_NOT_ALLOWED)

    def respond(self, body, status=HTTPStatus.OK):
        payload = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
