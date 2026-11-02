#!/usr/bin/env python3
"""Holt die Google-Rezensionen des Alpha-Mobil-Unternehmensprofils über die offizielle
Google-Business-Profile-API und legt sie verschlüsselt als google.enc.json ab.

Läuft im GitHub-Workflow „Google-Bewertungen“ (täglich und per Knopf). Benötigte Secrets:
  GBP_CLIENT_ID, GBP_CLIENT_SECRET, GBP_REFRESH_TOKEN  – OAuth-Zugang (siehe tools/google_auth.py)
  GBP_LOCATIONS   – ein oder mehrere Standorte, kommagetrennt, z. B. accounts/123/locations/456
  HC_PASSWORT     – Team-Passwort des Cockpits (zum Verschlüsseln)
  ANTHROPIC_API_KEY (optional) – dann schreibt Claude Kurzfassung, Thema und Antwortvorschlag

Ohne ANTHROPIC_API_KEY werden Stimmung und Thema nach festen Regeln bestimmt und es gibt
eine allgemeine Antwortvorlage für kritische Bewertungen.
"""
import base64, datetime, json, os, re, sys, urllib.parse, urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HIER)
ZIEL = os.path.join(REPO, 'google.enc.json')
sys.path.insert(0, HIER)
from build import verschluesseln  # gleiche Verschlüsselung wie die Seite

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

STERNE = {'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5}
THEMEN = [('kratz', 'Verarbeitung/Lack'), ('rost', 'Verarbeitung/Lack'), ('garantie', 'Mängel/Garantie'),
          ('gewährleist', 'Mängel/Garantie'), ('defekt', 'Mängel/Garantie'), ('kaputt', 'Mängel/Garantie'),
          ('akku', 'Akku/Reichweite'), ('reichweite', 'Akku/Reichweite'), ('spedition', 'Lieferung/Spedition'),
          ('liefer', 'Lieferung/Spedition'), ('versand', 'Lieferung/Spedition'), ('werkstatt', 'Werkstatt/Service'),
          ('inspektion', 'Werkstatt/Service'), ('reparatur', 'Werkstatt/Service'), ('service', 'Werkstatt/Service'),
          ('beratung', 'Werkstatt/Service'), ('freundlich', 'Werkstatt/Service'), ('telefon', 'Kommunikation'),
          ('erreich', 'Kommunikation'), ('preis', 'Preis-Leistung'), ('fährt', 'Fahrverhalten'), ('fahr', 'Fahrverhalten')]
VORLAGE = ('Vielen Dank für Ihre Bewertung. Es tut uns leid, dass nicht alles Ihren Erwartungen entsprochen hat. '
           'Bitte melden Sie sich mit Ihrer Bestellnummer bei unserem Kundenservice, damit wir uns persönlich um Ihr '
           'Anliegen kümmern können – Garantiefälle lösen wir gemeinsam mit unseren mobilen Servicepartnern.')


def http(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def access_token():
    body = urllib.parse.urlencode({
        'client_id': os.environ['GBP_CLIENT_ID'], 'client_secret': os.environ['GBP_CLIENT_SECRET'],
        'refresh_token': os.environ['GBP_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode()
    return http('https://oauth2.googleapis.com/token', body)['access_token']


def bewertungen(token, standort):
    alle, seite = [], None
    meta = {}
    while True:
        q = {'pageSize': 50, 'orderBy': 'updateTime desc'}
        if seite:
            q['pageToken'] = seite
        d = http(f'https://mybusiness.googleapis.com/v4/{standort}/reviews?' + urllib.parse.urlencode(q),
                 headers={'Authorization': 'Bearer ' + token})
        meta = {'durchschnitt': d.get('averageRating'), 'anzahl': d.get('totalReviewCount')}
        alle += d.get('reviews', [])
        seite = d.get('nextPageToken')
        if not seite:
            return alle, meta


def text_ohne_uebersetzung(t):
    # Google hängt bei übersetzten Rezensionen „(Translated by Google)“ / „(Original)“ an
    t = t or ''
    if '(Original)' in t:
        t = t.split('(Original)')[-1]
    return re.sub(r'\(Translated by Google\).*', '', t, flags=re.S).strip()


def thema(t):
    t = t.lower()
    for k, v in THEMEN:
        if k in t:
            return v
    return 'Allgemein'


def claude_auswertung(text, sterne):
    key = os.environ.get('ANTHROPIC_API_KEY')
    if not key or not text:
        return None
    prompt = ('Du wertest eine Google-Rezension für Alpha-Mobil aus (Händler und Hersteller von Motorrollern, '
              'Elektrorollern und Elektromobilen mit mobilen Servicepartnern). Antworte nur mit JSON: '
              '{"kurz": Kurzfassung in eigenen Worten (max. 250 Zeichen), "stimmung": "positiv"|"neutral"|"negativ", '
              '"thema": eines aus [Allgemein, Fahrverhalten, Preis-Leistung, Zuverlässigkeit, Lieferung/Spedition, '
              'Werkstatt/Service, Kommunikation, Mängel/Garantie, Verarbeitung/Lack, Bedienung, Akku/Reichweite, '
              'Transportschaden], "antwort": bei neutral/negativ oder Fragen ein freundlicher Antwortvorschlag in '
              'Sie-Form aus Sicht von Alpha-Mobil ohne Erstattungsversprechen, sonst ""}.\n\n'
              f'Sterne: {sterne}\nText: {text}')
    body = json.dumps({'model': 'claude-haiku-5-5', 'max_tokens': 600,
                       'messages': [{'role': 'user', 'content': prompt}]}).encode()
    try:
        d = http('https://api.anthropic.com/v1/messages', body, {
            'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'})
        raw = ''.join(b.get('text', '') for b in d.get('content', []))
        return json.loads(raw[raw.find('{'):raw.rfind('}') + 1])
    except Exception as e:  # Auswertung ist optional – bei Fehlern Regeln verwenden
        print('Claude-Auswertung übersprungen:', e)
        return None


def alt_laden(pw):
    if not os.path.exists(ZIEL):
        return {}
    enc = json.load(open(ZIEL))
    ub = lambda s: base64.b64decode(s)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=ub(enc['s']), iterations=enc['n']).derive(pw.encode())
    alt = json.loads(AESGCM(key).decrypt(ub(enc['i']), ub(enc['c']), None))
    return {r['key']: r for r in alt.get('reviews', [])}


def main():
    pw = os.environ.get('HC_PASSWORT', '').strip()
    if len(pw) < 12:
        sys.exit('HC_PASSWORT fehlt.')
    standorte = [s.strip() for s in os.environ['GBP_LOCATIONS'].split(',') if s.strip()]
    heute = datetime.date.today().isoformat()
    alt = alt_laden(pw)
    token = access_token()
    reviews, profile = [], []
    for st in standorte:
        liste, meta = bewertungen(token, st)
        profile.append({'standort': st, **meta})
        for r in liste:
            key = 'G-' + r.get('reviewId', r.get('name', ''))[-40:]
            sterne = STERNE.get(r.get('starRating'), 0)
            text = text_ohne_uebersetzung(r.get('comment'))
            datum = (r.get('createTime') or '')[:10]
            vorher = alt.get(key)
            if vorher and vorher.get('_quelle') == text:
                vorher['neu'] = False
                vorher['beantwortet'] = bool(r.get('reviewReply'))
                reviews.append(vorher)
                continue
            ai = claude_auswertung(text, sterne)
            stimmung = (ai or {}).get('stimmung') or ('positiv' if sterne >= 4 else 'neutral' if sterne == 3 else 'negativ')
            reviews.append({
                'key': key, 'shop': 'Google', 'artnr': st, 'produkt': 'Alpha-Mobil (Google-Profil)', 'modell': '',
                'marke': 'Alpha-Mobil', 'url': 'https://business.google.com/reviews', 'datum': datum, 'sterne': sterne,
                'text': (ai or {}).get('kurz') or (text[:300] if text else 'Bewertung ohne Text'),
                'stimmung': stimmung, 'thema': (ai or {}).get('thema') or thema(text),
                'antwort': (ai or {}).get('antwort') or (VORLAGE if stimmung != 'positiv' else ''),
                'beantwortet': bool(r.get('reviewReply')), 'neu': bool(alt), 'erfasst': heute, '_quelle': text})
    geaendert = set(alt) != {r['key'] for r in reviews} or any(r['neu'] for r in reviews) or \
        any(alt.get(r['key'], {}).get('beantwortet') != r.get('beantwortet') for r in reviews)
    if alt and not geaendert:
        print(f'Keine Änderungen ({len(reviews)} Google-Bewertungen).')
        return
    daten = {'stand': heute, 'profile': profile, 'reviews': reviews}
    json.dump(verschluesseln(json.dumps(daten, ensure_ascii=False), pw), open(ZIEL, 'w'))
    neu = sum(1 for r in reviews if r['neu'])
    print(f'{len(reviews)} Google-Bewertungen gespeichert, davon {neu} neu.')


if __name__ == '__main__':
    main()
