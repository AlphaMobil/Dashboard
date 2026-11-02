#!/usr/bin/env python3
"""Einmalige Einrichtung: holt den Refresh-Token für die Google-Business-Profile-API und
zeigt die Standort-Kennungen (GBP_LOCATIONS) an.

Aufruf auf einem eigenen Rechner (nicht auf einem Server):
  python3 tools/google_auth.py <CLIENT_ID> <CLIENT_SECRET>

Es öffnet sich der Browser; dort mit dem Google-Konto anmelden, das das Unternehmensprofil
von Alpha-Mobil verwaltet, und den Zugriff erlauben. Danach stehen hier die Werte für die
GitHub-Secrets. Den Refresh-Token wie ein Passwort behandeln.
"""
import http.server, json, sys, threading, urllib.parse, urllib.request, webbrowser

PORT = 8765
REDIRECT = f'http://127.0.0.1:{PORT}/'
SCOPE = 'https://www.googleapis.com/auth/business.manage'


def http_json(url, data=None, token=None):
    req = urllib.request.Request(url, data=data, headers={'Authorization': 'Bearer ' + token} if token else {})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    cid, secret = sys.argv[1], sys.argv[2]
    code = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            code['c'] = (q.get('code') or [''])[0]
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
            self.wfile.write('Fertig – du kannst dieses Fenster schließen.'.encode())
        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(('127.0.0.1', PORT), H)
    threading.Thread(target=srv.handle_request, daemon=True).start()
    url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({
        'client_id': cid, 'redirect_uri': REDIRECT, 'response_type': 'code', 'scope': SCOPE,
        'access_type': 'offline', 'prompt': 'consent'})
    print('Browser öffnet sich. Falls nicht, diese Adresse öffnen:\n' + url)
    webbrowser.open(url)
    while 'c' not in code:
        pass
    tok = http_json('https://oauth2.googleapis.com/token', urllib.parse.urlencode({
        'code': code['c'], 'client_id': cid, 'client_secret': secret, 'redirect_uri': REDIRECT,
        'grant_type': 'authorization_code'}).encode())
    access, refresh = tok['access_token'], tok.get('refresh_token')
    print('\nGBP_REFRESH_TOKEN =', refresh or '(keiner – Zugriff in myaccount.google.com entfernen und erneut ausführen)')
    konten = http_json('https://mybusinessaccountmanagement.googleapis.com/v1/accounts', token=access).get('accounts', [])
    print('\nStandorte (für GBP_LOCATIONS, mehrere kommagetrennt):')
    for k in konten:
        d = http_json(f"https://mybusinessbusinessinformation.googleapis.com/v1/{k['name']}/locations?readMask=name,title&pageSize=100", token=access)
        for loc in d.get('locations', []):
            print(f"  {k['name']}/{loc['name']}   –  {loc.get('title', '')}")


if __name__ == '__main__':
    main()
