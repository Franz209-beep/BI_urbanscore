"""
etl/loaders.py — Daten in die SQLite-Datenbank schreiben
=========================================================
Jede Funktion nimmt ein aufbereitetes Dict (aus extractors.py) entgegen
und schreibt es per UPSERT in die entsprechende Tabelle.
ON CONFLICT ... DO UPDATE stellt sicher, dass ein erneuter Lauf
bestehende Einträge aktualisiert statt zu duplizieren.
"""

import sqlite3


def load_wetter(conn: sqlite3.Connection, stadt_id: int, zeit_id: int, d: dict) -> None:
    conn.execute("""
        INSERT INTO wetterdaten
            (stadt_id, zeit_id, sonnenstunden_jahr, durchschnittstemperatur, niederschlag_avg)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            sonnenstunden_jahr      = excluded.sonnenstunden_jahr,
            durchschnittstemperatur = excluded.durchschnittstemperatur,
            niederschlag_avg        = excluded.niederschlag_avg
    """, (stadt_id, zeit_id,
          d["sonnenstunden_jahr"], d["durchschnittstemperatur"], d["niederschlag_avg"]))


def load_miete(conn: sqlite3.Connection, stadt_id: int, zeit_id: int, d: dict) -> None:
    conn.execute("""
        INSERT INTO mietdaten (stadt_id, zeit_id, mietpreis_kalt_qm, anzahl_inserate)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            mietpreis_kalt_qm = excluded.mietpreis_kalt_qm,
            anzahl_inserate   = excluded.anzahl_inserate
    """, (stadt_id, zeit_id, d["mietpreis_kalt_qm"], d["anzahl_inserate"]))


def load_arbeitsmarkt(conn: sqlite3.Connection, stadt_id: int, zeit_id: int, d: dict) -> None:
    conn.execute("""
        INSERT INTO arbeitsmarktdaten (stadt_id, zeit_id, arbeitslosenquote, offene_stellen)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            arbeitslosenquote = excluded.arbeitslosenquote,
            offene_stellen    = excluded.offene_stellen
    """, (stadt_id, zeit_id, d["arbeitslosenquote"], d.get("offene_stellen")))


def load_infrastruktur(conn: sqlite3.Connection, stadt_id: int, zeit_id: int, d: dict) -> None:
    conn.execute("""
        INSERT INTO infrastruktur (stadt_id, zeit_id, haltestellen_anzahl, poi_dichte)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            haltestellen_anzahl = excluded.haltestellen_anzahl,
            poi_dichte          = excluded.poi_dichte
    """, (stadt_id, zeit_id, d["haltestellen_anzahl"], d["poi_dichte"]))


def load_bildung(conn: sqlite3.Connection, stadt_id: int, zeit_id: int, d: dict) -> None:
    conn.execute("""
        INSERT INTO bildungsdaten
            (stadt_id, zeit_id, schulen_anzahl, kitas_anzahl, unis_anzahl,
             bildungs_dichte, bildung_pro_100k)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            schulen_anzahl   = excluded.schulen_anzahl,
            kitas_anzahl     = excluded.kitas_anzahl,
            unis_anzahl      = excluded.unis_anzahl,
            bildungs_dichte  = excluded.bildungs_dichte,
            bildung_pro_100k = excluded.bildung_pro_100k
    """, (stadt_id, zeit_id,
          d["schulen_anzahl"], d["kitas_anzahl"], d["unis_anzahl"],
          d["bildungs_dichte"], d["bildung_pro_100k"]))


def load_gesundheit(conn: sqlite3.Connection, stadt_id: int, zeit_id: int, d: dict) -> None:
    conn.execute("""
        INSERT INTO gesundheitsdaten
            (stadt_id, zeit_id, aerzte_anzahl, krankenhaeuser_anzahl, apotheken_anzahl,
             gesundheits_dichte, gesundheit_pro_100k)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            aerzte_anzahl         = excluded.aerzte_anzahl,
            krankenhaeuser_anzahl = excluded.krankenhaeuser_anzahl,
            apotheken_anzahl      = excluded.apotheken_anzahl,
            gesundheits_dichte    = excluded.gesundheits_dichte,
            gesundheit_pro_100k   = excluded.gesundheit_pro_100k
    """, (stadt_id, zeit_id,
          d["aerzte_anzahl"], d["krankenhaeuser_anzahl"], d["apotheken_anzahl"],
          d["gesundheits_dichte"], d["gesundheit_pro_100k"]))


def load_freizeit(conn: sqlite3.Connection, stadt_id: int, zeit_id: int, d: dict) -> None:
    conn.execute("""
        INSERT INTO freizeitdaten
            (stadt_id, zeit_id, parks_anzahl, kultur_anzahl, sport_anzahl,
             freizeit_dichte, freizeit_pro_100k)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            parks_anzahl      = excluded.parks_anzahl,
            kultur_anzahl     = excluded.kultur_anzahl,
            sport_anzahl      = excluded.sport_anzahl,
            freizeit_dichte   = excluded.freizeit_dichte,
            freizeit_pro_100k = excluded.freizeit_pro_100k
    """, (stadt_id, zeit_id,
          d["parks_anzahl"], d["kultur_anzahl"], d["sport_anzahl"],
          d["freizeit_dichte"], d["freizeit_pro_100k"]))


def load_sicherheit(conn: sqlite3.Connection, stadt_id: int, zeit_id: int, d: dict) -> None:
    conn.execute("""
        INSERT INTO sicherheitsdaten
            (stadt_id, zeit_id, straftaten_je_100k, gewaltdelikte_je_100k)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            straftaten_je_100k    = excluded.straftaten_je_100k,
            gewaltdelikte_je_100k = excluded.gewaltdelikte_je_100k
    """, (stadt_id, zeit_id, d["straftaten_je_100k"], d["gewaltdelikte_je_100k"]))
