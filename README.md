# ♟️ Chess Engine Testing Framework

Professionelles Framework zum Testen und Vergleichen von Schach-Engines unter Windows.

## 🎯 Features

- **UCI-Protokoll-Unterstützung** - Robust und fehler-tolerant
- **Windows .exe Support** - Direkte Integration von Engine-Executables
- **Engine vs Engine Matches** - Automatische Spielverwaltung
- **Turniere**
  - Round-Robin (alle gegen alle)
  - Gauntlet (eine Engine gegen mehrere)
- **Eröffnungsbuch-Integration** - Polyglot .bin Format
- **Web-Interface** - Grafische Oberfläche mit Live-Schachbrett
- **CLI-Tool** - Kommandozeilenzugriff für Automatisierung
- **UCI-Validator** - Prüft Engine-Kompatibilität
- **Umfangreiche Statistiken** - ELO-Berechnung, Nodes/Sec, etc.

## 📋 Voraussetzungen

- **Python 3.8+**
- **Windows** (für .exe-Engines)
- **Git**

## 🚀 Installation

### 1. Repository klonen

```bash
git clone https://github.com/IhrUsername/testchess.git
cd testchess
```

### 2. Python-Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 3. Engines hinzufügen

Kopieren Sie Ihre Engine-Executables (.exe) in das `Engines/` Verzeichnis:

```
testchess/
├── Engines/
│   ├── stockfish.exe
│   ├── SchachConsole.exe
│   └── andere_engine.exe
```

**Hinweis:** Stockfish und SchachConsole sind bereits im Repository enthalten!

### 4. Eröffnungsbuch (optional)

Das Polyglot-Eröffnungsbuch `komodo.bin` liegt bereits im `OpeningBooks/` Verzeichnis.

## 💻 Verwendung

### Web-Interface (empfohlen)

Das grafische Web-Interface bietet die einfachste Bedienung:

```bash
python backend/web_app.py
```

Dann Browser öffnen: **http://localhost:8000**

#### Features des Web-Interfaces:

1. **Engines verwalten**
   - Automatische Erkennung
   - UCI-Validierung
   - Engine-Informationen anzeigen

2. **Matches starten**
   - 2 Engines auswählen
   - Bedenkzeit einstellen
   - Live-Schachbrett verfolgen

3. **Turniere durchführen**
   - Round-Robin oder Gauntlet
   - Mehrere Runden
   - Eröffnungsbuch aktivieren
   - Live-Tabelle

### Command Line Interface (CLI)

Für Automatisierung und Skripting:

#### Engines auflisten

```bash
cd backend
python cli.py list
```

#### Engines suchen

```bash
python cli.py discover
```

#### Engine validieren

```bash
python cli.py validate
```

Prüft alle Engines auf UCI-Konformität und zeigt Probleme an.

#### Engine-Informationen anzeigen

```bash
python cli.py info SchachConsole
```

#### Einzelnes Match

```bash
python cli.py match SchachConsole stockfish --time 60000 --increment 1000
```

**Parameter:**
- `--time`: Bedenkzeit in Millisekunden (Standard: 60000 = 60s)
- `--increment`: Inkrement pro Zug in ms (Standard: 0)

#### Round-Robin Turnier

```bash
python cli.py tournament "Mein_Turnier" --type roundrobin --engines SchachConsole,stockfish --rounds 2 --time 60000
```

**Parameter:**
- `--type`: `roundrobin` oder `gauntlet`
- `--engines`: Komma-getrennte Engine-Namen
- `--rounds`: Anzahl Runden (Standard: 1)
- `--time`: Bedenkzeit (Standard: 60000ms)
- `--openings`: Eröffnungsbuch verwenden

#### Gauntlet Turnier

```bash
python cli.py tournament "SchachConsole_Test" --type gauntlet --engines SchachConsole,stockfish --rounds 1
```

Bei Gauntlet spielt die erste Engine gegen alle anderen.

## 📁 Projektstruktur

```
testchess/
├── backend/                    # Python Backend
│   ├── cli.py                 # Command-Line Interface
│   ├── web_app.py             # FastAPI Web-Server
│   ├── uci_interface.py       # UCI-Protokoll-Implementation
│   ├── engine_manager.py      # Engine-Verwaltung
│   ├── match.py               # Match-System
│   ├── tournament.py          # Turnier-System
│   ├── uci_validator.py       # UCI-Validierung
│   └── opening_book.py        # Eröffnungsbuch-Handler
├── frontend/                   # Web-Frontend
│   ├── index.html             # Haupt-HTML
│   └── app.js                 # JavaScript-Logik
├── Engines/                    # Engine-Executables
│   ├── stockfish.exe
│   └── SchachConsole.exe
├── OpeningBooks/               # Eröffnungsbücher
│   └── komodo.bin
├── config/                     # Konfigurationsdateien
│   └── engines.json           # Engine-Registry
├── results/                    # Turnier-Ergebnisse
│   ├── *.pgn                  # Partien im PGN-Format
│   └── *.json                 # Statistiken
├── logs/                       # Log-Dateien
├── tests/                      # Unit-Tests
├── requirements.txt            # Python-Abhängigkeiten
└── README.md                   # Diese Datei
```

## 🔧 Engine-Entwicklung: SchachConsole.exe

### Bekannte Einschränkungen

Ihr Framework unterstützt auch Engines mit **nicht-standardkonformer UCI-Implementierung**:

- ❌ Keine Mattsuche (`mate` Befehl)
- ⚠️ Möglicherweise unvollständige UCI-Ausgaben
- ✅ Funktioniert in Arena → Funktioniert auch hier!

### Spezielle Behandlung

Das Framework erkennt automatisch:
- Fehlende UCI-Features
- Timeout-Probleme
- Unvollständige Antworten

**Logging** ist ausführlich aktiviert, um Debugging zu erleichtern:
- `logs/chess_testing.log` - Alle Engine-Kommunikation

### Testing Ihrer Engine

```bash
# 1. UCI-Kompatibilität prüfen
python backend/cli.py validate

# 2. Gegen Stockfish testen
python backend/cli.py match SchachConsole stockfish --time 30000

# 3. Turnier gegen mehrere Gegner
python backend/cli.py tournament "SchachConsole_Development" --type gauntlet --engines SchachConsole,stockfish --rounds 3
```

## 📊 Ergebnisse auswerten

### PGN-Dateien

Alle Partien werden als PGN gespeichert:
```
results/
├── Mein_Turnier/
│   ├── game_1.pgn
│   ├── game_2.pgn
│   └── ...
```

Diese können Sie in **Arena**, **ChessBase**, oder anderen Schach-Tools öffnen.

### JSON-Statistiken

```json
{
  "tournament": "Mein_Turnier",
  "standings": [
    {
      "engine": "stockfish",
      "games": 2,
      "wins": 2,
      "draws": 0,
      "losses": 0,
      "points": 2.0,
      "score_percentage": 100.0
    },
    {
      "engine": "SchachConsole",
      "games": 2,
      "wins": 0,
      "draws": 0,
      "losses": 2,
      "points": 0.0,
      "score_percentage": 0.0
    }
  ]
}
```

## 🐛 Debugging

### UCI-Kommunikation debuggen

Die komplette Engine-Kommunikation wird geloggt:

```bash
tail -f logs/chess_testing.log
```

Ausgabe-Beispiel:
```
2025-11-05 14:30:12 - uci_interface - DEBUG - >> uci
2025-11-05 14:30:12 - uci_interface - DEBUG - << id name Stockfish 16
2025-11-05 14:30:12 - uci_interface - DEBUG - << id author the Stockfish developers
2025-11-05 14:30:12 - uci_interface - DEBUG - << uciok
```

### Engine startet nicht

**Problem:** Engine-Prozess startet nicht

**Lösung:**
1. Prüfen Sie den Pfad: `python backend/cli.py list`
2. Prüfen Sie Berechtigungen (muss ausführbar sein)
3. Prüfen Sie fehlende DLLs (auf Windows)

### Engine antwortet nicht

**Problem:** Timeout beim Warten auf `uciok`

**Lösung:**
1. Engine manuell in Console testen:
   ```cmd
   cd Engines
   SchachConsole.exe
   uci
   ```
2. Timeout erhöhen in `uci_interface.py` (Zeile 62):
   ```python
   lines = self.read_until("uciok", timeout=30)  # 30 Sekunden
   ```

## 🎓 Weiterführende Themen

### Eigene Eröffnungen hinzufügen

```python
from backend.opening_book import OpeningSuite

suite = OpeningSuite()
suite.add_opening("Italienisch", ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4"])
suite.add_opening("Sizilianisch", ["e2e4", "c7c5"])
```

### UCI-Optionen setzen

Editieren Sie `config/engines.json`:

```json
{
  "stockfish": {
    "name": "stockfish",
    "path": "Engines/stockfish.exe",
    "enabled": true,
    "options": {
      "Hash": "256",
      "Threads": "4"
    }
  }
}
```

### Python-API verwenden

```python
from backend.engine_manager import EngineManager
from backend.match import Match

manager = EngineManager()
white = manager.get_engine("SchachConsole")
black = manager.get_engine("stockfish")

match = Match(
    white_engine_path=white.path,
    black_engine_path=black.path,
    time_control=60000
)

result = match.play()
print(f"Winner: {result.winner}")
```

## 🤝 Tipps für Ihre Engine-Entwicklung

### Must-Have UCI-Befehle

Minimum für Kompatibilität:
```
uci          → id name ... \n id author ... \n uciok
isready      → readyok
ucinewgame   → (keine Antwort nötig)
position ... → (keine Antwort nötig)
go ...       → info ... \n bestmove ...
quit         → (Engine beenden)
```

### Empfohlene Info-Ausgaben

```
info depth 5 score cp 25 nodes 1000 nps 50000 time 20 pv e2e4
```

**Wichtig:** Immer mit `bestmove` abschließen!

### Testen während der Entwicklung

```bash
# Schneller Test (10 Sekunden Bedenkzeit)
python backend/cli.py match SchachConsole stockfish --time 10000

# Mit Live-Visualisierung
python backend/web_app.py
# Dann im Browser verfolgen
```

## 📝 Lizenz

MIT License - Frei verwendbar für private und kommerzielle Projekte.

## 🙏 Credits

- **python-chess** - Schach-Logik
- **Stockfish** - Referenz-Engine
- **chessboard.js** - Schachbrett-Visualisierung
- **FastAPI** - Web-Framework

## 📧 Support

Bei Fragen oder Problemen:
1. Prüfen Sie die Logs: `logs/chess_testing.log`
2. Validieren Sie die Engines: `python backend/cli.py validate`
3. Erstellen Sie ein Issue auf GitHub

---

**Viel Erfolg beim Testen Ihrer Schach-Engine! ♟️**
