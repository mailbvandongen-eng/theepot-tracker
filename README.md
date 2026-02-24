# Theepot Tracker

Monitor Marktplaats en Vinted automatisch op nieuwe advertenties. Ontvang email notificaties bij nieuwe vondsten.

## Web Versie (Aanbevolen)

Draait volledig in de cloud - geen PC nodig.

**Live website:** https://mailbvandongen-eng.github.io/theepot-tracker/

### Zelf hosten

#### 1. Frontend (GitHub Pages)

De `index.html` wordt automatisch gehost via GitHub Pages.

#### 2. Backend (Vercel)

**Benodigde accounts (gratis):**
- [Vercel](https://vercel.com) - hosting
- [Upstash](https://upstash.com) - Redis database
- [Resend](https://resend.com) - email verzending

**Stappen:**

1. **Upstash Redis aanmaken:**
   - Ga naar [Upstash Console](https://console.upstash.com)
   - Maak een nieuwe Redis database
   - Kopieer de `UPSTASH_REDIS_REST_URL`

2. **Resend API key:**
   - Ga naar [Resend Dashboard](https://resend.com/api-keys)
   - Maak een API key

3. **Deploy naar Vercel:**
   ```bash
   cd backend
   npx vercel --prod
   ```

4. **Environment variables instellen in Vercel:**
   - `REDIS_URL` = je Upstash Redis URL
   - `RESEND_API_KEY` = je Resend API key
   - `FROM_EMAIL` = afzender email (optioneel)

5. **Update frontend:**
   - Pas `API_URL` aan in `index.html` naar je Vercel URL

### Hoe het werkt

```
Jouw browser (website)
        │
        ▼
Vercel backend (Python)
   - Slaat zoektermen op in Redis
   - Cron job elke 10 minuten
   - Scraped Marktplaats & Vinted
   - Stuurt email bij nieuwe items
```

---

## CLI Versie

Draait lokaal op je PC met Telegram notificaties.

### Installatie

```bash
git clone https://github.com/mailbvandongen-eng/theepot-tracker.git
cd theepot-tracker
pip install -r requirements.txt
```

### Configuratie

```bash
python marktwatch.py setup    # Telegram instellen
python marktwatch.py keywords add   # Zoekwoorden toevoegen
```

### Gebruik

```bash
python marktwatch.py keywords list      # Toon zoekwoorden
python marktwatch.py keywords remove 1  # Verwijder zoekwoord
python marktwatch.py keywords toggle 1  # Aan/uit zetten
python marktwatch.py run                # Eenmalige check
python marktwatch.py watch              # Loop elke 10 min
```

---

## Disclaimer

Deze tool is bedoeld voor persoonlijk gebruik. Respecteer de gebruiksvoorwaarden van Marktplaats en Vinted.

## Licentie

MIT
