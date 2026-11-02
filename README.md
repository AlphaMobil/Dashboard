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
