"""
etl/pipeline.py — Orchestrierung der ETL-Pipeline
==================================================
Koordiniert den täglichen Datenlauf:
  1. Wetterdaten parallel für alle Städte abrufen
  2. Pro Stadt: statische + Overpass-Daten laden (mit Cache-Check)
  3. Ranking neu berechnen

Overpass-Updates laufen nur montags (reguläres Wochentag-Gate),
es sei denn, Daten fehlen oder sind unvollständig – dann immer.
"""

import time
from datetime import date

import config
from etl.db import get_conn, get_oder_erstelle_zeit_id, get_stadt_id, bereits_vorhanden
from etl.extractors import (
    extract_wetter_parallel,
    extract_wetter,
    extract_miete,
    extract_arbeitsmarkt,
    extract_sicherheit,
    extract_infrastruktur,
    extract_bildung,
    extract_gesundheit,
    extract_freizeit,
)
from etl.loaders import (
    load_wetter,
    load_miete,
    load_arbeitsmarkt,
    load_sicherheit,
    load_infrastruktur,
    load_bildung,
    load_gesundheit,
    load_freizeit,
)
from etl.transform import berechne_ranking


# Zuordnung: Tabellenname → (Extractor, Loader)
# Reihenfolge bestimmt die Verarbeitungsreihenfolge pro Stadt.
STATISCHE_DIMENSIONEN = [
    ("mietdaten",         extract_miete,        load_miete),
    ("arbeitsmarktdaten", extract_arbeitsmarkt,  load_arbeitsmarkt),
    ("sicherheitsdaten",  extract_sicherheit,    load_sicherheit),
]

OVERPASS_DIMENSIONEN = [
    ("infrastruktur",    extract_infrastruktur, load_infrastruktur),
    ("bildungsdaten",    extract_bildung,       load_bildung),
    ("gesundheitsdaten", extract_gesundheit,    load_gesundheit),
    ("freizeitdaten",    extract_freizeit,      load_freizeit),
]

# Pause zwischen Overpass-Aufrufen pro Stadt (Rate-Limit)
OVERPASS_PAUSE_S = 10


def main() -> None:
    heute         = date.today()
    # overpass_tag  = heute.weekday() == 0  # Montag = reguläres Overpass-Update
    overpass_tag = False

    print(f"=== UrbanScore ETL-Pipeline ({heute}) ===")
    print(f"    Städte: {len(config.STAEDTE)} | "
          f"Overpass-Update: {'ja (Montag)' if overpass_tag else 'nein (nur bei fehlenden Daten)'}\n")

    conn    = get_conn()
    zeit_id = get_oder_erstelle_zeit_id(conn, config.AKTUELLES_JAHR)
    print(f"Zeitraum: Jahr {config.AKTUELLES_JAHR} (zeit_id={zeit_id})\n")

    # ── Schritt 1: Wetterdaten parallel ──────────────────────────────────────
    print("--- Wetterdaten (parallel) ---")
    staedte_ohne_wetter = [
        s for s in config.STAEDTE
        if (sid := get_stadt_id(conn, s["name"]))
        and not bereits_vorhanden(conn, "wetterdaten", sid, zeit_id)
    ]
    if staedte_ohne_wetter:
        ergebnisse = extract_wetter_parallel(staedte_ohne_wetter)
        for stadt in staedte_ohne_wetter:
            sid  = get_stadt_id(conn, stadt["name"])
            data = ergebnisse.get(stadt["name"])
            if sid and data:
                load_wetter(conn, sid, zeit_id, data)
        conn.commit()
    else:
        print("  Alle Wetterdaten bereits vorhanden.")
    print()

    # ── Schritt 2: Pro Stadt – statische + Overpass-Daten ────────────────────
    for i, stadt in enumerate(config.STAEDTE):
        print(f"--- [{i + 1}/{len(config.STAEDTE)}] {stadt['name']} ---")
        stadt_id = get_stadt_id(conn, stadt["name"])
        if not stadt_id:
            print("  Stadt nicht in DB – bitte setup_db.sql ausführen.")
            continue

        # Statische Daten: einmal pro Jahr, danach gecacht
        for tabelle, extractor, loader in STATISCHE_DIMENSIONEN:
            if bereits_vorhanden(conn, tabelle, stadt_id, zeit_id):
                print(f"  [Cache] {tabelle}")
            else:
                data = extractor(stadt)
                if data:
                    loader(conn, stadt_id, zeit_id, data)

        # Overpass-Daten: regulär montags ODER wenn Daten fehlen/unvollständig
        for tabelle, extractor, loader in OVERPASS_DIMENSIONEN:
            vorhanden = bereits_vorhanden(conn, tabelle, stadt_id, zeit_id)
            if vorhanden:
                print(f"  [Cache] {tabelle}")
                continue

            grund = "Montags-Update" if overpass_tag else "Daten fehlen/unvollständig"
            print(f"  [{tabelle}] → {grund}")
            time.sleep(OVERPASS_PAUSE_S)
            data = extractor(stadt)
            if data:
                loader(conn, stadt_id, zeit_id, data)
            time.sleep(OVERPASS_PAUSE_S)

        conn.commit()
        print()

    # ── Schritt 3: Ranking berechnen ─────────────────────────────────────────
    print("--- Ranking wird berechnet ---")
    berechne_ranking(conn, zeit_id)

    conn.close()
    print("\n=== Pipeline abgeschlossen ===")


if __name__ == "__main__":
    main()
