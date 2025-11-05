#!/usr/bin/env python3
"""
Quick Test Script
Schneller Test des Chess Engine Testing Frameworks
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Quick test of the framework"""
    print("=" * 60)
    print("CHESS ENGINE TESTING FRAMEWORK - QUICK TEST")
    print("=" * 60)
    print()

    # Create necessary directories
    Path("logs").mkdir(exist_ok=True)
    Path("results").mkdir(exist_ok=True)
    Path("config").mkdir(exist_ok=True)

    # Import backend modules
    try:
        from backend.engine_manager import EngineManager
        from backend.uci_validator import validate_all_engines
        print("✓ Backend-Module erfolgreich geladen")
    except Exception as e:
        print(f"✗ Fehler beim Laden der Backend-Module: {e}")
        print("\nBitte installieren Sie die Abhängigkeiten:")
        print("  pip install -r requirements.txt")
        return 1

    # Check for engines
    print("\n" + "-" * 60)
    print("1. ENGINES SUCHEN")
    print("-" * 60)

    engines_dir = Path("Engines")
    if not engines_dir.exists():
        print("✗ Engines/ Verzeichnis nicht gefunden")
        print("  Bitte erstellen Sie das Verzeichnis und fügen Sie Engines hinzu")
        return 1

    exe_files = list(engines_dir.glob("*.exe"))
    print(f"Gefundene Engines: {len(exe_files)}")

    if not exe_files:
        print("✗ Keine .exe-Dateien im Engines/ Verzeichnis gefunden")
        print("  Bitte fügen Sie Ihre Engines hinzu")
        return 1

    for exe in exe_files:
        print(f"  - {exe.name}")

    # Discover engines
    print("\n" + "-" * 60)
    print("2. ENGINES REGISTRIEREN")
    print("-" * 60)

    manager = EngineManager()
    manager.discover_engines()

    engines = manager.list_engines()
    print(f"✓ {len(engines)} Engines registriert")

    # Validate engines
    print("\n" + "-" * 60)
    print("3. UCI-VALIDIERUNG")
    print("-" * 60)

    print("Validiere Engines (dies kann einige Sekunden dauern)...")
    results = validate_all_engines("Engines")

    print("\nValidierungs-Ergebnisse:")
    for result in results:
        status = "✓" if result["compatible"] else "✗"
        score = result["score"]
        print(f"  {status} {result['engine']}: {score:.1f}% "
              f"({result['passed']}/{result['total']} Tests)")

        if result['issues']:
            for issue in result['issues'][:3]:  # Max 3 issues
                print(f"     - {issue}")

        if result['warnings']:
            for warning in result['warnings'][:2]:  # Max 2 warnings
                print(f"     ⚠ {warning}")

    # Summary
    print("\n" + "=" * 60)
    print("TEST ABGESCHLOSSEN")
    print("=" * 60)

    compatible_count = sum(1 for r in results if r["compatible"])
    print(f"\nErgebnis: {compatible_count}/{len(results)} Engines UCI-kompatibel")

    print("\n📋 NÄCHSTE SCHRITTE:")
    print("\n1. CLI verwenden:")
    print("   cd backend")
    print("   python cli.py list")
    print("   python cli.py match engine1 engine2")
    print("\n2. Web-Interface starten:")
    print("   python backend/web_app.py")
    print("   Dann Browser öffnen: http://localhost:8000")
    print("\n3. Dokumentation lesen:")
    print("   cat README.md")
    print()

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nUnterbrochen durch Benutzer")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {e}", exc_info=True)
        sys.exit(1)
