# Theepot Tracker (Marktwatch)

Een Python CLI-tool die Marktplaats en Vinted monitort op nieuwe advertenties en Telegram-meldingen stuurt bij treffers.

## Features

- Monitor meerdere zoektermen tegelijk
- Scraping van Marktplaats en Vinted
- Telegram notificaties voor nieuwe advertenties
- Deduplicatie (geen dubbele meldingen)
- Mooie CLI output met Rich

## Installatie

```bash
git clone https://github.com/mailbvandongen-eng/theepot-tracker.git
cd theepot-tracker
pip install -r requirements.txt
```

## Configuratie

### 1. Telegram instellen

```bash
python marktwatch.py setup
```

Je hebt nodig:
- Een Telegram Bot Token (maak een bot via [@BotFather](https://t.me/BotFather))
- Je Chat ID (verkrijg via [@userinfobot](https://t.me/userinfobot))

### 2. Zoekwoorden toevoegen

```bash
python marktwatch.py keywords add
```

## Gebruik

```bash
# Toon alle zoekwoorden
python marktwatch.py keywords list

# Voeg zoekwoord toe (interactief)
python marktwatch.py keywords add

# Verwijder zoekwoord
python marktwatch.py keywords remove <id>

# Zoekwoord aan/uit zetten
python marktwatch.py keywords toggle <id>

# Eenmalige check
python marktwatch.py run

# Continue monitoring (elke 10 minuten)
python marktwatch.py watch
```

## Bestandsstructuur

```
marktwatch/
  marktwatch.py      # Hoofdscript
  config.json        # Telegram token + chat_id (niet in git)
  keywords.json      # Opgeslagen zoekwoorden
  seen.json          # Geziene advertentie-IDs (niet in git)
  requirements.txt   # Dependencies
```

## Telegram melding voorbeeld

```
Nieuwe advertentie gevonden!

Zoekterm: theepot delfts blauw
Site: Marktplaats
Theepot 19e eeuw - Delfts Blauw
€45,00
https://www.marktplaats.nl/...
```

## Disclaimer

Deze tool is bedoeld voor persoonlijk gebruik. Respecteer de gebruiksvoorwaarden van Marktplaats en Vinted. Overmatig scrapen kan leiden tot IP-blokkades.

## Licentie

MIT
