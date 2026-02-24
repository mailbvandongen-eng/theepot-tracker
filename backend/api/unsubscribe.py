"""API endpoint om een subscription te verwijderen."""

import json
import os
from http.server import BaseHTTPRequestHandler
from upstash_redis import Redis

def get_redis():
    """Maak Redis connectie."""
    return Redis(
        url=os.environ.get('UPSTASH_REDIS_REST_URL', ''),
        token=os.environ.get('UPSTASH_REDIS_REST_TOKEN', '')
    )

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            sub_id = data.get('id', '')

            if not sub_id:
                self.send_error_response(400, 'ID is verplicht')
                return

            r = get_redis()
            deleted = r.hdel('subscriptions', sub_id)

            if deleted:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'success': True}).encode())
            else:
                self.send_error_response(404, 'Subscription niet gevonden')

        except Exception as e:
            self.send_error_response(500, str(e))

    def send_error_response(self, code, message):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}).encode())
