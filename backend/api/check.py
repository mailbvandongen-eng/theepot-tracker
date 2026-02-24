"""Cron job die elke 10 minuten checkt voor nieuwe advertenties."""

import json
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler

import requests
import resend
from bs4 import BeautifulSoup
from upstash_redis import Redis

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def get_redis():
    """Maak Redis connectie."""
    return Redis(
        url=os.environ.get('UPSTASH_REDIS_REST_URL', ''),
        token=os.environ.get('UPSTASH_REDIS_REST_TOKEN', '')
    )


def scrape_marktplaats(term: str) -> list:
    """Scrape Marktplaats voor advertenties."""
    encoded_term = urllib.parse.quote(term)
    url = f"https://www.marktplaats.nl/q/{encoded_term}/"

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
    }

    ads = []

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        listings = soup.find_all("li", class_="hz-Listing")

        if not listings:
            listings = soup.find_all("article", {"data-testid": "listing"})

        for listing in listings[:10]:
            try:
                title_elem = (
                    listing.find("h3", class_="hz-Listing-title") or
                    listing.find("a", class_="hz-Listing-title") or
                    listing.find("h3")
                )

                price_elem = (
                    listing.find("p", class_="hz-Listing-price") or
                    listing.find("span", class_="hz-Listing-price") or
                    listing.find("p", {"data-testid": "price"})
                )

                link_elem = listing.find("a", href=True)

                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    price = price_elem.get_text(strip=True) if price_elem else "Prijs onbekend"
                    href = link_elem.get("href", "")

                    if not href.startswith("http"):
                        href = f"https://www.marktplaats.nl{href}"

                    ad_id = f"mp_{href.split('/')[-1].split('.')[0]}"

                    ads.append({
                        "id": ad_id,
                        "title": title,
                        "price": price,
                        "url": href,
                        "site": "Marktplaats"
                    })
            except Exception:
                continue

    except requests.RequestException:
        pass

    return ads


def scrape_vinted(term: str) -> list:
    """Scrape Vinted voor advertenties."""
    encoded_term = urllib.parse.quote(term)
    url = f"https://www.vinted.nl/catalog?search_text={encoded_term}"

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
    }

    ads = []

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.find_all(attrs={"data-testid": "grid-item"})

        if not items:
            items = soup.find_all("div", class_="feed-grid__item")

        for item in items[:10]:
            try:
                title_elem = (
                    item.find("h2") or
                    item.find("p", class_="web_ui__Text__text") or
                    item.find("a", {"data-testid": "item-title"})
                )

                price_elem = (
                    item.find("p", {"data-testid": "item-price"}) or
                    item.find("span", class_="web_ui__Text__text")
                )

                link_elem = item.find("a", href=True)

                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    price = price_elem.get_text(strip=True) if price_elem else "Prijs onbekend"
                    href = link_elem.get("href", "")

                    if not href.startswith("http"):
                        href = f"https://www.vinted.nl{href}"

                    ad_id = f"vi_{href.split('/')[-1].split('-')[0]}"

                    ads.append({
                        "id": ad_id,
                        "title": title,
                        "price": price,
                        "url": href,
                        "site": "Vinted"
                    })
            except Exception:
                continue

    except requests.RequestException:
        pass

    return ads


def send_email(to_email: str, term: str, ad: dict) -> bool:
    """Stuur email notificatie."""
    resend.api_key = os.environ.get('RESEND_API_KEY', '')

    if not resend.api_key:
        return False

    try:
        resend.Emails.send({
            "from": os.environ.get('FROM_EMAIL', 'Theepot Tracker <onboarding@resend.dev>'),
            "to": [to_email],
            "subject": f"Nieuwe {ad['site']} advertentie: {term}",
            "html": f"""
            <h2>Nieuwe advertentie gevonden!</h2>
            <p><strong>Zoekterm:</strong> {term}</p>
            <p><strong>Site:</strong> {ad['site']}</p>
            <p><strong>Titel:</strong> {ad['title']}</p>
            <p><strong>Prijs:</strong> {ad['price']}</p>
            <p><a href="{ad['url']}" style="background: #4fc3f7; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Bekijk advertentie</a></p>
            <hr>
            <p style="color: #888; font-size: 12px;">Theepot Tracker - Automatische monitoring van Marktplaats en Vinted</p>
            """
        })
        return True
    except Exception:
        return False


def is_seen(r, ad_id: str) -> bool:
    """Check of advertentie al gezien is."""
    return r.sismember('seen_ads', ad_id)


def mark_seen(r, ad_id: str):
    """Markeer advertentie als gezien."""
    r.sadd('seen_ads', ad_id)
    # Houd max 10000 IDs bij
    if r.scard('seen_ads') > 10000:
        r.spop('seen_ads', 1000)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            r = get_redis()

            # Haal alle subscriptions op
            raw_subs = r.hgetall('subscriptions')

            new_ads_count = 0
            emails_sent = 0

            if raw_subs:
                for key, value in raw_subs.items():
                    try:
                        sub = json.loads(value) if isinstance(value, str) else value
                        term = sub.get('term', '')
                        email = sub.get('email', '')
                        sites = sub.get('sites', [])

                        all_ads = []

                        if 'marktplaats' in sites:
                            all_ads.extend(scrape_marktplaats(term))

                        if 'vinted' in sites:
                            all_ads.extend(scrape_vinted(term))

                        for ad in all_ads:
                            if not is_seen(r, ad['id']):
                                mark_seen(r, ad['id'])
                                new_ads_count += 1

                                if send_email(email, term, ad):
                                    emails_sent += 1

                    except Exception:
                        continue

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'new_ads': new_ads_count,
                'emails_sent': emails_sent
            }).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
