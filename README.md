# Alpha-Mobil Händler-Cockpit

Passwortgeschützte Web-App (installierbar) mit Listungen, Preisen, Auffälligkeiten und
Bewertungen von Alpha Motors und GreenStreet bei Lidl, Netto, hagebau und Kaufland.

**Adresse:** https://alphamobil.github.io/Dashboard/

## Als App installieren
- **Chrome/Edge (PC/Mac):** Seite öffnen → Symbol „App installieren“ rechts in der Adressleiste
  (oder Menü ⋮ → „Streamen, speichern und teilen“ → „Seite als App installieren“).
- **Android (Chrome):** Menü ⋮ → „Zum Startbildschirm hinzufügen“ / „App installieren“.
- **iPhone/iPad (Safari):** Teilen-Symbol → „Zum Home-Bildschirm“.

## Aufbau
- `index.html` – fertige Seite; Daten liegen nur verschlüsselt darin (AES-256-GCM, PBKDF2)
- `manifest.webmanifest`, Icons, `service-worker.js` – machen die Seite installierbar
- `d3.min.js` – Diagramm-Bibliothek, lokal für den Offline-Start
- `tools/page.html` – Cockpit-Seite, `tools/shell.html` – Login und Laufzeit, `tools/build.py` – Build

## Aktualisieren
`HC_PASSWORT=… python3 tools/build.py products.json reviews.json [Stand]` und `index.html` committen.
Das übernimmt die Claude-Aufgabe „Bewertungen holen“. Passwort und Klartext-Daten gehören nicht ins Repository.

## Google-Bewertungen (offizielle Google-Business-Profile-API)

Der Workflow **„Google-Bewertungen aktualisieren“** (`.github/workflows/google-bewertungen.yml`) holt
täglich um ca. 7:43 Uhr – oder per „Run workflow“ – alle Rezensionen des Google-Unternehmensprofils,
verschlüsselt sie mit dem Team-Passwort und legt sie als `google.enc.json` ab. Die App lädt die Datei
nach der Anmeldung dazu. Code: `tools/google_reviews.py`.

### Einmalige Einrichtung
1. **Google-Cloud-Projekt** anlegen: https://console.cloud.google.com → neues Projekt „Alpha-Mobil Cockpit“.
2. **API-Zugang beantragen**: Die Business-Profile-APIs sind zugangsbeschränkt. Über das Antragsformular
   von Google (Google Business Profile API – „Request access“) mit der Projektnummer beantragen.
   Nach der Freigabe (meist einige Tage) im Projekt aktivieren:
   *Google My Business API*, *My Business Account Management API*, *My Business Business Information API*.
3. **OAuth-Zustimmungsbildschirm** einrichten (Typ „Extern“, Status „In Produktion“ oder das verwaltende
   Google-Konto als Testnutzer eintragen), Bereich `https://www.googleapis.com/auth/business.manage`.
4. **OAuth-Client** erstellen: Anmeldedaten → „OAuth-Client-ID“ → Anwendungstyp **Desktop-App**.
   Client-ID und Client-Secret notieren.
5. Auf einem eigenen Rechner: `python3 tools/google_auth.py <CLIENT_ID> <CLIENT_SECRET>` – im Browser mit
   dem Google-Konto anmelden, das das Profil verwaltet. Das Skript zeigt den Refresh-Token und die
   Standort-Kennung(en) `accounts/…/locations/…`.
6. **GitHub-Secrets** im Repository anlegen (Settings → Secrets and variables → Actions):
   `GBP_CLIENT_ID`, `GBP_CLIENT_SECRET`, `GBP_REFRESH_TOKEN`, `GBP_LOCATIONS`, `HC_PASSWORT`
   (Team-Passwort) und optional `ANTHROPIC_API_KEY` (dann schreibt Claude Kurzfassung, Thema und
   Antwortvorschlag; sonst feste Regeln und eine Antwortvorlage).
7. Unter **Actions** den Workflow einmal mit „Run workflow“ starten.
