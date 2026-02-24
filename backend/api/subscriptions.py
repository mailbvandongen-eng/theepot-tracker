"""API endpoint om alle subscriptions op te halen."""

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
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        try:
            r = get_redis()
            raw_subs = r.hgetall('subscriptions')

            subscriptions = []
            if raw_subs:
                for key, value in raw_subs.items():
                    try:
                        sub = json.loads(value) if isinstance(value, str) else value
                        subscriptions.append(sub)
                    except (json.JSONDecodeError, TypeError):
                        continue

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'subscriptions': subscriptions
            }).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
