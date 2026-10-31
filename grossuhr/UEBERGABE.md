# Große Uhr – Projektübergabe (Stand 31.10.2026)

## Projekt
Große Wanduhr für ein Theaterstück. Zwei ca. 60 cm lange Styropor-Zeiger, angetrieben von EINEM Nema-17 über ein 3D-gedrucktes PETG-Zahnradgetriebe ohne Kugellager. Peter arbeitet auf Deutsch (Elektronik-Techniker, Theater); in Fusion 360 bitte verifizierte deutsche UI-Begriffe verwenden.

## Mechanik (Fusion 360)
- Hybrid-Konstruktion, Komponenten, Gelenke, Starre Gruppe, Bewegungsverknüpfung (Winkelpaare, "Umkehren").
- Übersetzung 12:1 = 3:1 × 4:1; Modul 1,5; Stufen 20→60 und 16→64 Zähne, Achsabstand je 60 mm (Zeiger koaxial), Außendurchmesser 33/93/27/99 mm, Fußrundung ca. 0,4 mm, für FDM 0,2–0,3 mm extra Achsabstand erwogen, Reibungsminderung durch Ringe/Aussparungen.
- Motorwelle = Minutenzeiger: 1 Umdrehung der Welle = 1 Stunde Uhrzeit.

## Elektronik
- Motor 17HS15-1504S-X1, A4988 (Vref 0,64 V bei R100), 12-V-Netzteil, 100 µF Elko.
- ESP32: STEP=GPIO14, DIR=GPIO12 (Strapping-Pin), MS1/2/3=GPIO25/26/27.
- Fehler gefunden und behoben: lose Dupont-Kabel an MS1-3 -> Vollschritt statt 1/16. Test "+1 Std = genau 1 Wellenumdrehung" bestätigt Mikroschritt (jetzt OK, Peter bestätigt "funktioniert").
- Maximalgeschwindigkeit: Software bis 8000 Schritte/s (1/16: 150 U/min, Vollschritt 2400 U/min), Admin-Grenze 600 U/min; realistisch für den Motor ca. 200-400 U/min, mit Last/Getriebe weniger. Standard-Max 60 U/min.
- Merke: Bei künftigen Hardware-Projekten Temperatursensor (Übertemperaturschutz) vorschlagen.

## Firmware: /home/claude/GrossUhr/GrossUhr.ino (Einzeldatei, ESP32 Arduino)
- 20-kHz-Timer-ISR mit 32-Bit-Phasenakkumulator, Trapez-Planer als FreeRTOS-Task (Core 1), 1/16-Mikroschritt/Vollschritt-Umschaltung automatisch (nur bei pos%16==0), 3200 µSchritte/U, 38400 = 12 h.
- Webinterface (WebServer, mDNS grossuhr.local, WLAN AP+STA, Prefs/NVS): Hauptseite mit STOP, 5 Zeitfelder + "Rückwärts" + Go, Geschwindigkeits-Fader, ±1 min / ±1 h, AUTO + Multiplikator (Auswahlfeld), "aktuelle Uhrzeit setzen" (kürzester Weg), Ablauf (Von/Bis/Dauer in Minuten, optional rückwärts, "Start"). Admin: Motorwerte, Kalibrierung (Zeiger-Uhrzeit eintragen, Jog), Art-Net, WLAN, Standardwerte, Speichern springt zurück auf Hauptseite.
- Art-Net (UDP 6454): K1 Stunde = Wert/20, K2 Minute = Wert/4, K3 Tempo/Richtung (0 Stopp, 1-126 vor, 127-255 zurück).
- Auto-Modus: Standard = Minutensprung (1 Minute pro Minute, ×Faktor); Admin-Checkbox "Auto fließend" = kleinste Schritte.
- Drehrichtung: Checkbox "invertieren" Standard AUS (Grundrichtung intern bereits passend); Migration in loadAll (dirv-Key).
- Ablauf-Logik: sweepStart() fährt kürzesten Weg zur Von-Zeit, dann gleichmäßig zur Bis-Zeit; Von=Bis = volle 12-h-Runde; STOP/Go/Jog/Auto brechen ab.

## Tests
Host-Testharness /home/claude/test/test_main.cpp mit Arduino/ESP-Stubs in /home/claude/test/stubs; Build: `g++ -std=c++17 -w -I stubs -x c++ test_main.cpp -o t && ./t` (Stand: ALLE TESTS OK). Playwright-Check der Seiten: /home/claude/test/pw.js.

## Offen / Ideen
- Mechanik noch ohne Ziffernblatt; Zeigerkalibrierung und Praxistest der Höchstgeschwindigkeit mit Zeigern stehen aus.
- Ggf. Beschleunigung/Maximaltempo im Admin schrittweise hochtesten.
- Temperatursensor am Motortreiber/Motor erwägen.
