"""
etl/db.py — Datenbankzugriff und Cache-Verwaltung
==================================================
Kapselt alle direkten SQLite-Operationen, die nicht zum Laden von
Rohdaten gehören: Verbindungsaufbau, Zeitraum-Verwaltung und der
Cache-Check, der verhindert dass Daten unnötig neu abgerufen werden.
"""

import sqlite3

DB_PATH = "urbanscore.db"

# Konfiguration für den Cache-Check pro Tabelle:
# Schlüssel  → DB-Tabellenname
# Wert       → Liste von Spalten, die ALLE > 0 sein müssen damit der
#              Eintrag als vollständig gilt. Ist eine Spalte 0 oder NULL,
#              wird der Eintrag gelöscht und neu abgerufen.
# Hintergrund: Overpass-Timeouts liefern manchmal stille 0-Werte zurück.
#              Statische Tabellen haben keine Pflichtfelder (immer gültig).
CACHE_PFLICHTFELDER: dict[str, list[str]] = {
    "infrastruktur":    ["haltestellen_anzahl", "poi_dichte"],
    "bildungsdaten":    ["schulen_anzahl", "kitas_anzahl", "unis_anzahl"],
    "gesundheitsdaten": ["aerzte_anzahl", "apotheken_anzahl", "krankenhaeuser_anzahl"],
    "freizeitdaten":    ["parks_anzahl", "kultur_anzahl", "sport_anzahl"],
    # Statische Tabellen: kein Pflichtfeld-Check nötig
    "wetterdaten":        [],
    "mietdaten":          [],
    "arbeitsmarktdaten":  [],
    "sicherheitsdaten":   [],
}


def get_conn() -> sqlite3.Connection:
    """Öffnet eine SQLite-Verbindung mit aktivierten Foreign Keys."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_oder_erstelle_zeit_id(conn: sqlite3.Connection, jahr: int) -> int:
    """
    Gibt die zeit_id für ein Jahr zurück und legt den Eintrag an,
    falls er noch nicht existiert.
    """
    row = conn.execute(
        "SELECT zeit_id FROM zeit WHERE jahr = ? AND quartal IS NULL", (jahr,)
    ).fetchone()
    if row:
        return row[0]
    cursor = conn.execute(
        "INSERT INTO zeit (jahr, zeitraum_label) VALUES (?, ?)",
        (jahr, f"Jahr {jahr}"),
    )
    conn.commit()
    return cursor.lastrowid


def get_stadt_id(conn: sqlite3.Connection, name: str) -> int | None:
    """Gibt die stadt_id für einen Städtenamen zurück, oder None."""
    row = conn.execute(
        "SELECT stadt_id FROM stadt WHERE name = ?", (name,)
    ).fetchone()
    return row[0] if row else None


def bereits_vorhanden(
    conn: sqlite3.Connection, tabelle: str, stadt_id: int, zeit_id: int
) -> bool:
    """
    Prüft ob ein vollständiger Datensatz für (stadt_id, zeit_id) existiert.

    Für Overpass-Tabellen (Pflichtfelder definiert): Ist auch nur ein
    Pflichtfeld 0 oder NULL, gilt der Eintrag als Timeout-Artefakt und
    wird gelöscht → Rückgabe False, damit er neu abgerufen wird.

    Für statische Tabellen (keine Pflichtfelder): Einmal vorhanden = immer gültig.
    """
    row = conn.execute(
        f"SELECT 1 FROM {tabelle} WHERE stadt_id = ? AND zeit_id = ?",
        (stadt_id, zeit_id),
    ).fetchone()

    if not row:
        return False

    pflichtfelder = CACHE_PFLICHTFELDER.get(tabelle, [])
    if not pflichtfelder:
        # Statische Tabelle – kein weiterer Check nötig
        return True

    # Prüfen ob alle Pflichtfelder befüllt sind
    cols = ", ".join(pflichtfelder)
    werte = conn.execute(
        f"SELECT {cols} FROM {tabelle} WHERE stadt_id = ? AND zeit_id = ?",
        (stadt_id, zeit_id),
    ).fetchone()

    if werte and any((v or 0) == 0 for v in werte):
        print(f"  [Cache] {tabelle}: unvollständige Daten erkannt → wird neu abgerufen")
        conn.execute(
            f"DELETE FROM {tabelle} WHERE stadt_id = ? AND zeit_id = ?",
            (stadt_id, zeit_id),
        )
        conn.commit()
        return False

    return True
