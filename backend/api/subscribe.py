"""API endpoint om een nieuwe subscription toe te voegen."""

import json
import os
import uuid
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

            term = data.get('term', '').strip()
            email = data.get('email', '').strip()
            sites = data.get('sites', [])

            if not term or not email or not sites:
                self.send_error_response(400, 'Vul alle velden in')
                return

            # Valideer sites
            valid_sites = ['marktplaats', 'vinted', 'rataplan']
            sites = [s for s in sites if s in valid_sites]
            if not sites:
                self.send_error_response(400, 'Selecteer minimaal 1 site')
                return

            # Maak subscription
            sub_id = str(uuid.uuid4())[:8]
            subscription = {
                'id': sub_id,
                'term': term,
                'email': email,
                'sites': sites
            }

            # Sla op in Redis
            r = get_redis()
            r.hset('subscriptions', sub_id, json.dumps(subscription))

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'subscription': subscription
            }).encode())

        except Exception as e:
            self.send_error_response(500, str(e))

    def send_error_response(self, code, message):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}).encode())
