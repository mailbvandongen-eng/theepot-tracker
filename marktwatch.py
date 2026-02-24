#!/usr/bin/env python3
"""
Marktwatch - Monitor Marktplaats en Vinted voor nieuwe advertenties
"""

import argparse
import asyncio
import json
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich import print as rprint
from telegram import Bot
from telegram.error import TelegramError

# Paden naar configuratiebestanden
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
KEYWORDS_FILE = BASE_DIR / "keywords.json"
SEEN_FILE = BASE_DIR / "seen.json"

console = Console()


def load_json(filepath: Path) -> dict:
    """Laad een JSON bestand."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        console.print(f"[red]Fout bij het lezen van {filepath}[/red]")
        return {}


def save_json(filepath: Path, data: dict) -> None:
    """Sla data op in een JSON bestand."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_config() -> dict:
    """Haal configuratie op."""
    default_config = {
        "telegram_token": "",
        "telegram_chat_id": "",
        "check_interval_minutes": 10,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    config = load_json(CONFIG_FILE)
    return {**default_config, **config}


def get_keywords() -> dict:
    """Haal zoekwoorden op."""
    default = {"keywords": []}
    data = load_json(KEYWORDS_FILE)
    return {**default, **data}


def get_seen() -> dict:
    """Haal geziene advertenties op."""
    default = {"seen_ids": []}
    data = load_json(SEEN_FILE)
    return {**default, **data}


def add_seen(ad_id: str) -> None:
    """Markeer een advertentie als gezien."""
    seen = get_seen()
    if ad_id not in seen["seen_ids"]:
        seen["seen_ids"].append(ad_id)
        save_json(SEEN_FILE, seen)


def is_seen(ad_id: str) -> bool:
    """Controleer of een advertentie al gezien is."""
    seen = get_seen()
    return ad_id in seen["seen_ids"]


# =============================================================================
# Keyword Management
# =============================================================================

def cmd_keywords_list() -> None:
    """Toon alle zoekwoorden."""
    data = get_keywords()
    keywords = data.get("keywords", [])

    if not keywords:
        console.print("[yellow]Geen zoekwoorden gevonden. Voeg er een toe met 'keywords add'[/yellow]")
        return

    table = Table(title="Zoekwoorden")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Zoekterm", style="green")
    table.add_column("Sites", style="blue")
    table.add_column("Actief", style="magenta")

    for kw in keywords:
        status = "[green]Ja[/green]" if kw.get("active", True) else "[red]Nee[/red]"
        sites = ", ".join(kw.get("sites", []))
        table.add_row(str(kw["id"]), kw["term"], sites, status)

    console.print(table)


def cmd_keywords_add() -> None:
    """Voeg interactief een zoekwoord toe."""
    data = get_keywords()
    keywords = data.get("keywords", [])

    # Bepaal nieuw ID
    new_id = max([kw["id"] for kw in keywords], default=0) + 1

    console.print(Panel("Nieuw zoekwoord toevoegen", style="blue"))

    term = Prompt.ask("Zoekterm")
    if not term.strip():
        console.print("[red]Zoekterm mag niet leeg zijn[/red]")
        return

    console.print("\nBeschikbare sites: [cyan]marktplaats[/cyan], [cyan]vinted[/cyan]")
    sites_input = Prompt.ask("Sites (komma-gescheiden)", default="marktplaats,vinted")
    sites = [s.strip().lower() for s in sites_input.split(",")]

    valid_sites = ["marktplaats", "vinted"]
    sites = [s for s in sites if s in valid_sites]

    if not sites:
        console.print("[red]Geen geldige sites geselecteerd[/red]")
        return

    new_keyword = {
        "id": new_id,
        "term": term.strip(),
        "sites": sites,
        "active": True
    }

    keywords.append(new_keyword)
    data["keywords"] = keywords
    save_json(KEYWORDS_FILE, data)

    console.print(f"\n[green]Zoekwoord toegevoegd met ID {new_id}[/green]")


def cmd_keywords_remove(keyword_id: int) -> None:
    """Verwijder een zoekwoord."""
    data = get_keywords()
    keywords = data.get("keywords", [])

    original_len = len(keywords)
    keywords = [kw for kw in keywords if kw["id"] != keyword_id]

    if len(keywords) == original_len:
        console.print(f"[red]Zoekwoord met ID {keyword_id} niet gevonden[/red]")
        return

    data["keywords"] = keywords
    save_json(KEYWORDS_FILE, data)
    console.print(f"[green]Zoekwoord met ID {keyword_id} verwijderd[/green]")


def cmd_keywords_toggle(keyword_id: int) -> None:
    """Zet een zoekwoord aan of uit."""
    data = get_keywords()
    keywords = data.get("keywords", [])

    found = False
    for kw in keywords:
        if kw["id"] == keyword_id:
            kw["active"] = not kw.get("active", True)
            found = True
            status = "geactiveerd" if kw["active"] else "gedeactiveerd"
            console.print(f"[green]Zoekwoord '{kw['term']}' {status}[/green]")
            break

    if not found:
        console.print(f"[red]Zoekwoord met ID {keyword_id} niet gevonden[/red]")
        return

    data["keywords"] = keywords
    save_json(KEYWORDS_FILE, data)


# =============================================================================
# Setup
# =============================================================================

def cmd_setup() -> None:
    """Configureer Telegram token en chat_id."""
    config = get_config()

    console.print(Panel("Telegram Configuratie", style="blue"))
    console.print("\nOm meldingen te ontvangen heb je nodig:")
    console.print("1. Een Telegram Bot Token (via @BotFather)")
    console.print("2. Je Chat ID (via @userinfobot)\n")

    token = Prompt.ask("Telegram Bot Token", default=config.get("telegram_token", ""))
    chat_id = Prompt.ask("Telegram Chat ID", default=config.get("telegram_chat_id", ""))

    config["telegram_token"] = token
    config["telegram_chat_id"] = chat_id

    save_json(CONFIG_FILE, config)
    console.print("\n[green]Configuratie opgeslagen![/green]")

    # Test de verbinding
    if token and chat_id:
        if Confirm.ask("Wil je de Telegram verbinding testen?"):
            asyncio.run(test_telegram(token, chat_id))


async def test_telegram(token: str, chat_id: str) -> None:
    """Test de Telegram verbinding."""
    try:
        bot = Bot(token=token)
        await bot.send_message(chat_id=chat_id, text="Marktwatch verbinding succesvol!")
        console.print("[green]Testbericht verzonden![/green]")
    except TelegramError as e:
        console.print(f"[red]Telegram fout: {e}[/red]")


# =============================================================================
# Scraping
# =============================================================================

def scrape_marktplaats(term: str, config: dict) -> list[dict]:
    """Scrape Marktplaats voor advertenties."""
    encoded_term = urllib.parse.quote(term)
    url = f"https://www.marktplaats.nl/q/{encoded_term}/"

    headers = {
        "User-Agent": config.get("user_agent"),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
    }

    ads = []

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Zoek naar advertentie-items
        listings = soup.find_all("li", class_="hz-Listing")

        if not listings:
            # Probeer alternatieve selector
            listings = soup.find_all("article", {"data-testid": "listing"})

        for listing in listings:
            try:
                # Probeer verschillende selectors voor titel
                title_elem = (
                    listing.find("h3", class_="hz-Listing-title") or
                    listing.find("a", class_="hz-Listing-title") or
                    listing.find("h3")
                )

                # Probeer verschillende selectors voor prijs
                price_elem = (
                    listing.find("p", class_="hz-Listing-price") or
                    listing.find("span", class_="hz-Listing-price") or
                    listing.find("p", {"data-testid": "price"})
                )

                # Probeer link te vinden
                link_elem = listing.find("a", href=True)

                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    price = price_elem.get_text(strip=True) if price_elem else "Prijs onbekend"
                    href = link_elem.get("href", "")

                    if not href.startswith("http"):
                        href = f"https://www.marktplaats.nl{href}"

                    # Genereer uniek ID
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

    except requests.RequestException as e:
        console.print(f"[yellow]Waarschuwing: Marktplaats niet bereikbaar ({e})[/yellow]")

    return ads


def scrape_vinted(term: str, config: dict) -> list[dict]:
    """Scrape Vinted voor advertenties."""
    encoded_term = urllib.parse.quote(term)
    url = f"https://www.vinted.nl/catalog?search_text={encoded_term}"

    headers = {
        "User-Agent": config.get("user_agent"),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
    }

    ads = []

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Zoek naar items met data-testid="grid-item"
        items = soup.find_all(attrs={"data-testid": "grid-item"})

        if not items:
            # Probeer alternatieve selectors
            items = soup.find_all("div", class_="feed-grid__item")

        for item in items:
            try:
                # Zoek titel
                title_elem = (
                    item.find("h2") or
                    item.find("p", class_="web_ui__Text__text") or
                    item.find("a", {"data-testid": "item-title"})
                )

                # Zoek prijs
                price_elem = (
                    item.find("p", {"data-testid": "item-price"}) or
                    item.find("span", class_="web_ui__Text__text")
                )

                # Zoek link
                link_elem = item.find("a", href=True)

                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    price = price_elem.get_text(strip=True) if price_elem else "Prijs onbekend"
                    href = link_elem.get("href", "")

                    if not href.startswith("http"):
                        href = f"https://www.vinted.nl{href}"

                    # Genereer uniek ID uit URL
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

    except requests.RequestException as e:
        console.print(f"[yellow]Waarschuwing: Vinted niet bereikbaar ({e})[/yellow]")

    return ads


# =============================================================================
# Telegram Notifications
# =============================================================================

async def send_telegram_notification(ad: dict, term: str, config: dict) -> bool:
    """Stuur een Telegram melding voor een nieuwe advertentie."""
    token = config.get("telegram_token")
    chat_id = config.get("telegram_chat_id")

    if not token or not chat_id:
        console.print("[yellow]Telegram niet geconfigureerd. Gebruik 'setup' commando.[/yellow]")
        return False

    message = (
        f"Nieuwe advertentie gevonden!\n\n"
        f"Zoekterm: {term}\n"
        f"Site: {ad['site']}\n"
        f"{ad['title']}\n"
        f"{ad['price']}\n"
        f"{ad['url']}"
    )

    try:
        bot = Bot(token=token)
        await bot.send_message(chat_id=chat_id, text=message)
        return True
    except TelegramError as e:
        console.print(f"[red]Telegram fout: {e}[/red]")
        return False


# =============================================================================
# Run & Watch
# =============================================================================

async def run_check() -> int:
    """Voer een enkele check uit voor alle actieve zoekwoorden."""
    config = get_config()
    data = get_keywords()
    keywords = [kw for kw in data.get("keywords", []) if kw.get("active", True)]

    if not keywords:
        console.print("[yellow]Geen actieve zoekwoorden. Voeg er een toe met 'keywords add'[/yellow]")
        return 0

    new_ads_count = 0

    with console.status("[bold blue]Zoeken naar nieuwe advertenties...") as status:
        for kw in keywords:
            term = kw["term"]
            sites = kw.get("sites", ["marktplaats", "vinted"])

            status.update(f"[bold blue]Zoeken naar '{term}'...")

            all_ads = []

            if "marktplaats" in sites:
                all_ads.extend(scrape_marktplaats(term, config))

            if "vinted" in sites:
                all_ads.extend(scrape_vinted(term, config))

            # Filter nieuwe advertenties
            for ad in all_ads:
                if not is_seen(ad["id"]):
                    new_ads_count += 1
                    add_seen(ad["id"])

                    # Toon in console
                    console.print(Panel(
                        f"[cyan]Zoekterm:[/cyan] {term}\n"
                        f"[cyan]Site:[/cyan] {ad['site']}\n"
                        f"[cyan]Titel:[/cyan] {ad['title']}\n"
                        f"[cyan]Prijs:[/cyan] {ad['price']}\n"
                        f"[cyan]URL:[/cyan] {ad['url']}",
                        title="Nieuwe advertentie!",
                        border_style="green"
                    ))

                    # Stuur Telegram melding
                    await send_telegram_notification(ad, term, config)

            # Kleine pauze tussen zoekwoorden
            time.sleep(1)

    if new_ads_count == 0:
        console.print("[dim]Geen nieuwe advertenties gevonden[/dim]")
    else:
        console.print(f"\n[green]Totaal {new_ads_count} nieuwe advertentie(s) gevonden[/green]")

    return new_ads_count


def cmd_run() -> None:
    """Voer een eenmalige check uit."""
    console.print(Panel("Marktwatch - Eenmalige Check", style="blue"))
    asyncio.run(run_check())


def cmd_watch() -> None:
    """Start de continue monitoring."""
    config = get_config()
    interval = config.get("check_interval_minutes", 10)

    console.print(Panel(
        f"Marktwatch - Continue Monitoring\n"
        f"Interval: elke {interval} minuten\n"
        f"Druk Ctrl+C om te stoppen",
        style="blue"
    ))

    try:
        while True:
            console.print(f"\n[dim]Check gestart om {time.strftime('%H:%M:%S')}[/dim]")
            asyncio.run(run_check())
            console.print(f"[dim]Volgende check over {interval} minuten...[/dim]")
            time.sleep(interval * 60)
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring gestopt[/yellow]")


# =============================================================================
# Main
# =============================================================================

def main() -> None:
    """Hoofdfunctie met argument parsing."""
    parser = argparse.ArgumentParser(
        description="Marktwatch - Monitor Marktplaats en Vinted",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Beschikbare commando's")

    # Keywords subcommand
    keywords_parser = subparsers.add_parser("keywords", help="Beheer zoekwoorden")
    keywords_subparsers = keywords_parser.add_subparsers(dest="action")

    keywords_subparsers.add_parser("list", help="Toon alle zoekwoorden")
    keywords_subparsers.add_parser("add", help="Voeg een zoekwoord toe")

    remove_parser = keywords_subparsers.add_parser("remove", help="Verwijder een zoekwoord")
    remove_parser.add_argument("id", type=int, help="ID van het zoekwoord")

    toggle_parser = keywords_subparsers.add_parser("toggle", help="Zet zoekwoord aan/uit")
    toggle_parser.add_argument("id", type=int, help="ID van het zoekwoord")

    # Other commands
    subparsers.add_parser("setup", help="Configureer Telegram")
    subparsers.add_parser("run", help="Eenmalige check uitvoeren")
    subparsers.add_parser("watch", help="Continue monitoring starten")

    args = parser.parse_args()

    if args.command == "keywords":
        if args.action == "list":
            cmd_keywords_list()
        elif args.action == "add":
            cmd_keywords_add()
        elif args.action == "remove":
            cmd_keywords_remove(args.id)
        elif args.action == "toggle":
            cmd_keywords_toggle(args.id)
        else:
            keywords_parser.print_help()
    elif args.command == "setup":
        cmd_setup()
    elif args.command == "run":
        cmd_run()
    elif args.command == "watch":
        cmd_watch()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
