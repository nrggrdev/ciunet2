# Scanner-Simulator & Werkzeuge

Drei eigenständige Werkzeuge rund um den CIU-NET Scanner-UDP-Datenstrom. Sie
verwenden dieselben Header-/Parser-Definitionen wie die echte Anwendung
(`daq_net.daq`), die erzeugten Pakete sind also byte-genau kompatibel zu
`DaLiReceiver`.

Alle Skripte aus dem Projekt-Hauptverzeichnis starten (als Modul):

```bash
cd /home/nr/programming25/clean_ciunet/clean_ciunet
```

## 1. Scanner-Simulator – sendet den UDP-Strom

```bash
python -m simulator.scanner_simulator --host 127.0.0.1 --port 51002
```

Wichtige Optionen:

| Option | Bedeutung | Default |
|---|---|---|
| `--host` / `--multicast` | Unicast-Ziel-IP **oder** Multicast-Gruppe (z.B. `239.1.1.1`) | `127.0.0.1` |
| `--port` | Ziel-UDP-Port | `51002` |
| `--pattern` | `kiln`, `stripes`, `gradient`, `chessboard` | `kiln` |
| `--length` | Videowerte pro Linie (FoV-Auflösung) | `4096` |
| `--fps` | Linien pro Sekunde | `20` |
| `--trigger-period` | Ofen-Trigger alle N Linien (0 = aus) | `0` |
| `--interface` | lokale IF-IP für Multicast-Versand | – |
| `--lines` | nach N Linien stoppen (0 = endlos) | `0` |

> **Hinweis:** `DaLiReceiver` akzeptiert nur Datagramme, deren Absender-IP der
> in der Scanner-`.ini` eingestellten `source` entspricht. Für lokale Tests in
> der Scanner-Config `source = 127.0.0.1` setzen. Das Muster `stripes` eignet
> sich am besten, um Referenzpunkte im Geometrie-Tool wiederzufinden.

## 2. Live-Datenanzeige

```bash
python -m simulator.data_viewer --port 51002 --source 127.0.0.1
```

Zeigt einen Wasserfall (Spalten = Linien über die Zeit) und die aktuell
empfangene Linie als Kurve, plus Linien-/Segmentzähler und Rate.

## 3. Live-Geometrie mit Referenzpunkten

```bash
python -m simulator.geometry_tool --port 51002 --source 127.0.0.1 \
    --config config/scanner1.ini
```

- **Oben:** Rohlinie über dem FoV-Winkel mit Markern für `phi1` / `phi2`.
- **Unten:** auf die Ofenachse transformierte Linie mit Markern für `pass1` /
  `pass2`.
- Rechts Eingabefelder für `phi1/pass1`, `phi2/pass2`, `tilt`, `fov_angle`
  sowie `kiln_start/kiln_end`. Änderungen wirken sofort; berechnet werden
  Lotfußpunkt `l` und Lotlänge `h` (Tilt-Geometrie wie in
  `GeoTransformator.build_tilt_geometry`).
- **Config laden / In .ini speichern:** schreibt die `[geometry]`-Sektion
  (`phi1, pass1, phi2, pass2, tilt, mode=tilt`) zurück – mit `.bak`-Sicherung
  und unter Erhalt der Kommentare.

## Schnellstart (zwei Terminals)

```bash
# Terminal 1 – Datenquelle
python -m simulator.scanner_simulator --pattern stripes --fps 20 --trigger-period 20

# Terminal 2 – Geometrie einstellen
python -m simulator.geometry_tool --config config/scanner1.ini
```
