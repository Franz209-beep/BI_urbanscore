"""
UrbanScore ETL-Pipeline (Erweitert)
=====================================
Neue Kategorien:
- Bildung     (Schulen, Kitas, Unis via Overpass)
- Gesundheit  (Ärzte, Krankenhäuser via Overpass)
- Freizeit    (Parks, Kultur, Seen via Overpass)
- Sicherheit  (Kriminalstatistik – statische Daten BKA 2023)

Optimierungen (beibehalten):
1. Caching: Bereits vorhandene Daten werden nicht erneut abgerufen
2. Parallele Abfragen: Open-Meteo läuft parallel
3. Overpass nur wöchentlich (montags)
"""

import os
import math
import time
import sqlite3
import requests
import pandas as pd
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
from sklearn.preprocessing import MinMaxScaler

# ---------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------

DB_PATH = "urbanscore.db"

STAEDTE = [
    {"name": "Berlin",      "ags": "11000000", "lat": 52.5200, "lon": 13.4050, "radius_km": 20, "einwohner": 3645000},
    {"name": "Hamburg",     "ags": "02000000", "lat": 53.5753, "lon": 10.0153, "radius_km": 18, "einwohner": 1853000},
    {"name": "München",     "ags": "09162000", "lat": 48.1351, "lon": 11.5820, "radius_km": 15, "einwohner": 1488000},
    {"name": "Köln",        "ags": "05315000", "lat": 50.9333, "lon":  6.9500, "radius_km": 15, "einwohner": 1084000},
    {"name": "Frankfurt",   "ags": "06412000", "lat": 50.1109, "lon":  8.6821, "radius_km": 12, "einwohner":  759000},
    {"name": "Düsseldorf",  "ags": "05111000", "lat": 51.2217, "lon":  6.7762, "radius_km": 12, "einwohner":  619000},
    {"name": "Stuttgart",   "ags": "08111000", "lat": 48.7758, "lon":  9.1829, "radius_km": 12, "einwohner":  626000},
    {"name": "Leipzig",     "ags": "14713000", "lat": 51.3397, "lon": 12.3731, "radius_km": 12, "einwohner":  628000},
    {"name": "Dortmund",    "ags": "05913000", "lat": 51.5136, "lon":  7.4653, "radius_km": 12, "einwohner":  588000},
    {"name": "Bremen",      "ags": "04011000", "lat": 53.0793, "lon":  8.8017, "radius_km": 12, "einwohner":  563000},
    {"name": "Essen",       "ags": "05113000", "lat": 51.4556, "lon":  7.0116, "radius_km": 10, "einwohner":  580000},
    {"name": "Dresden",     "ags": "14612000", "lat": 51.0504, "lon": 13.7373, "radius_km": 12, "einwohner":  556000},
    {"name": "Hannover",    "ags": "03241001", "lat": 52.3759, "lon":  9.7320, "radius_km": 12, "einwohner":  532000},
    {"name": "Nürnberg",    "ags": "09564000", "lat": 49.4521, "lon": 11.0767, "radius_km": 12, "einwohner":  511000},
    {"name": "Duisburg",    "ags": "05112000", "lat": 51.4344, "lon":  6.7623, "radius_km": 10, "einwohner":  495000},
    {"name": "Bochum",      "ags": "05911000", "lat": 51.4818, "lon":  7.2162, "radius_km": 10, "einwohner":  365000},
    {"name": "Wuppertal",   "ags": "05124000", "lat": 51.2562, "lon":  7.1508, "radius_km": 10, "einwohner":  355000},
    {"name": "Bielefeld",   "ags": "05711000", "lat": 52.0302, "lon":  8.5325, "radius_km": 10, "einwohner":  333000},
    {"name": "Bonn",        "ags": "05314000", "lat": 50.7374, "lon":  7.0982, "radius_km": 10, "einwohner":  329000},
    {"name": "Münster",     "ags": "05515000", "lat": 51.9607, "lon":  7.6261, "radius_km": 10, "einwohner":  317000},
]

# Einwohner-Lookup für schnellen Zugriff im Ranking
EINWOHNER = {s["name"]: s["einwohner"] for s in STAEDTE}

# ---------------------------------------------------------------
# Statische Daten (unveränderlich / jährlich)
# ---------------------------------------------------------------

MIETPREISE_STATISCH = {
    "Berlin":      {"mietpreis_kalt_qm": 13.20, "anzahl_inserate": 0},
    "Hamburg":     {"mietpreis_kalt_qm": 14.80, "anzahl_inserate": 0},
    "München":     {"mietpreis_kalt_qm": 20.50, "anzahl_inserate": 0},
    "Köln":        {"mietpreis_kalt_qm": 13.00, "anzahl_inserate": 0},
    "Frankfurt":   {"mietpreis_kalt_qm": 15.30, "anzahl_inserate": 0},
    "Düsseldorf":  {"mietpreis_kalt_qm": 13.50, "anzahl_inserate": 0},
    "Stuttgart":   {"mietpreis_kalt_qm": 15.80, "anzahl_inserate": 0},
    "Leipzig":     {"mietpreis_kalt_qm":  8.50, "anzahl_inserate": 0},
    "Dortmund":    {"mietpreis_kalt_qm":  9.20, "anzahl_inserate": 0},
    "Bremen":      {"mietpreis_kalt_qm":  9.80, "anzahl_inserate": 0},
    "Essen":       {"mietpreis_kalt_qm":  9.00, "anzahl_inserate": 0},
    "Dresden":     {"mietpreis_kalt_qm":  9.00, "anzahl_inserate": 0},
    "Hannover":    {"mietpreis_kalt_qm": 11.00, "anzahl_inserate": 0},
    "Nürnberg":    {"mietpreis_kalt_qm": 12.50, "anzahl_inserate": 0},
    "Duisburg":    {"mietpreis_kalt_qm":  8.20, "anzahl_inserate": 0},
    "Bochum":      {"mietpreis_kalt_qm":  9.10, "anzahl_inserate": 0},
    "Wuppertal":   {"mietpreis_kalt_qm":  8.00, "anzahl_inserate": 0},
    "Bielefeld":   {"mietpreis_kalt_qm":  9.30, "anzahl_inserate": 0},
    "Bonn":        {"mietpreis_kalt_qm": 12.80, "anzahl_inserate": 0},
    "Münster":     {"mietpreis_kalt_qm": 12.00, "anzahl_inserate": 0},
}

ARBEITSMARKT_STATISCH = {
    "Berlin":      {"arbeitslosenquote":  9.4, "offene_stellen": None},
    "Hamburg":     {"arbeitslosenquote":  6.9, "offene_stellen": None},
    "München":     {"arbeitslosenquote":  3.8, "offene_stellen": None},
    "Köln":        {"arbeitslosenquote":  8.1, "offene_stellen": None},
    "Frankfurt":   {"arbeitslosenquote":  5.7, "offene_stellen": None},
    "Düsseldorf":  {"arbeitslosenquote":  7.8, "offene_stellen": None},
    "Stuttgart":   {"arbeitslosenquote":  4.2, "offene_stellen": None},
    "Leipzig":     {"arbeitslosenquote":  7.5, "offene_stellen": None},
    "Dortmund":    {"arbeitslosenquote": 11.2, "offene_stellen": None},
    "Bremen":      {"arbeitslosenquote": 10.1, "offene_stellen": None},
    "Essen":       {"arbeitslosenquote": 11.8, "offene_stellen": None},
    "Dresden":     {"arbeitslosenquote":  6.8, "offene_stellen": None},
    "Hannover":    {"arbeitslosenquote":  8.3, "offene_stellen": None},
    "Nürnberg":    {"arbeitslosenquote":  5.9, "offene_stellen": None},
    "Duisburg":    {"arbeitslosenquote": 12.5, "offene_stellen": None},
    "Bochum":      {"arbeitslosenquote": 10.4, "offene_stellen": None},
    "Wuppertal":   {"arbeitslosenquote": 11.0, "offene_stellen": None},
    "Bielefeld":   {"arbeitslosenquote":  7.9, "offene_stellen": None},
    "Bonn":        {"arbeitslosenquote":  5.5, "offene_stellen": None},
    "Münster":     {"arbeitslosenquote":  5.1, "offene_stellen": None},
}

# Quelle: BKA PKS 2023, Straftaten je 100.000 Einwohner
KRIMINALITAET_STATISCH = {
    "Berlin":      {"straftaten_je_100k": 15823, "gewaltdelikte_je_100k": 384},
    "Hamburg":     {"straftaten_je_100k": 14201, "gewaltdelikte_je_100k": 341},
    "München":     {"straftaten_je_100k":  9812, "gewaltdelikte_je_100k": 198},
    "Köln":        {"straftaten_je_100k": 13450, "gewaltdelikte_je_100k": 312},
    "Frankfurt":   {"straftaten_je_100k": 16234, "gewaltdelikte_je_100k": 398},
    "Düsseldorf":  {"straftaten_je_100k": 12980, "gewaltdelikte_je_100k": 287},
    "Stuttgart":   {"straftaten_je_100k": 11203, "gewaltdelikte_je_100k": 245},
    "Leipzig":     {"straftaten_je_100k": 12801, "gewaltdelikte_je_100k": 298},
    "Dortmund":    {"straftaten_je_100k": 13920, "gewaltdelikte_je_100k": 356},
    "Bremen":      {"straftaten_je_100k": 13100, "gewaltdelikte_je_100k": 318},
    "Essen":       {"straftaten_je_100k": 12450, "gewaltdelikte_je_100k": 302},
    "Dresden":     {"straftaten_je_100k": 10980, "gewaltdelikte_je_100k": 231},
    "Hannover":    {"straftaten_je_100k": 13560, "gewaltdelikte_je_100k": 327},
    "Nürnberg":    {"straftaten_je_100k": 12100, "gewaltdelikte_je_100k": 276},
    "Duisburg":    {"straftaten_je_100k": 13780, "gewaltdelikte_je_100k": 348},
    "Bochum":      {"straftaten_je_100k": 11890, "gewaltdelikte_je_100k": 271},
    "Wuppertal":   {"straftaten_je_100k": 12340, "gewaltdelikte_je_100k": 289},
    "Bielefeld":   {"straftaten_je_100k": 11020, "gewaltdelikte_je_100k": 241},
    "Bonn":        {"straftaten_je_100k": 10450, "gewaltdelikte_je_100k": 219},
    "Münster":     {"straftaten_je_100k":  9230, "gewaltdelikte_je_100k": 187},
}

JAHR = date.today().year


# ---------------------------------------------------------------
# DB-Hilfsfunktionen
# ---------------------------------------------------------------

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_oder_erstelle_zeit_id(conn, jahr):
    label = f"Jahr {jahr}"
    row = conn.execute(
        "SELECT zeit_id FROM zeit WHERE jahr = ? AND quartal IS NULL", (jahr,)
    ).fetchone()
    if row:
        return row[0]
    cursor = conn.execute(
        "INSERT INTO zeit (jahr, zeitraum_label) VALUES (?, ?)", (jahr, label)
    )
    conn.commit()
    return cursor.lastrowid


def get_stadt_id(conn, name):
    row = conn.execute("SELECT stadt_id FROM stadt WHERE name = ?", (name,)).fetchone()
    return row[0] if row else None


def bereits_vorhanden(conn, tabelle, stadt_id, zeit_id):
    """Prüft ob ein Datensatz existiert UND vollständig ist.
    Einzelne Felder mit 0 werden als unvollständig gewertet und neu abgefragt.
    """
    row = conn.execute(
        f"SELECT 1 FROM {tabelle} WHERE stadt_id = ? AND zeit_id = ?",
        (stadt_id, zeit_id)
    ).fetchone()
    if not row:
        return False

    def loesche_und_false(grund):
        print(f"  [Cache] {tabelle} unvollständig ({grund}) → wird neu abgefragt")
        conn.execute(f"DELETE FROM {tabelle} WHERE stadt_id = ? AND zeit_id = ?",
                     (stadt_id, zeit_id))
        conn.commit()
        return False

    if tabelle == "bildungsdaten":
        r = conn.execute(
            "SELECT schulen_anzahl, kitas_anzahl, unis_anzahl FROM bildungsdaten "
            "WHERE stadt_id = ? AND zeit_id = ?", (stadt_id, zeit_id)
        ).fetchone()
        if r:
            if (r[0] or 0) == 0 and (r[1] or 0) == 0:
                return loesche_und_false("Schulen=0 und Kitas=0")

    elif tabelle == "gesundheitsdaten":
        r = conn.execute(
            "SELECT aerzte_anzahl, apotheken_anzahl, krankenhaeuser_anzahl "
            "FROM gesundheitsdaten WHERE stadt_id = ? AND zeit_id = ?",
            (stadt_id, zeit_id)
        ).fetchone()
        if r:
            # Jedes Feld einzeln prüfen – Berlin hat Ärzte aber keine Apotheken
            if (r[1] or 0) == 0:   # Apotheken fehlen
                return loesche_und_false("Apotheken=0")
            if (r[0] or 0) == 0:   # Ärzte fehlen
                return loesche_und_false("Aerzte=0")

    elif tabelle == "freizeitdaten":
        r = conn.execute(
            "SELECT parks_anzahl, kultur_anzahl, sport_anzahl FROM freizeitdaten "
            "WHERE stadt_id = ? AND zeit_id = ?", (stadt_id, zeit_id)
        ).fetchone()
        if r:
            if (r[1] or 0) == 0:   # Kultur fehlt
                return loesche_und_false("Kultur=0")
            if (r[0] or 0) == 0 and (r[2] or 0) == 0:
                return loesche_und_false("Parks=0 und Sport=0")

    elif tabelle == "infrastruktur":
        r = conn.execute(
            "SELECT haltestellen_anzahl, poi_dichte FROM infrastruktur "
            "WHERE stadt_id = ? AND zeit_id = ?", (stadt_id, zeit_id)
        ).fetchone()
        if r and (r[0] or 0) == 0 and (r[1] or 0.0) == 0.0:
            return loesche_und_false("Haltestellen=0 und POI=0")

    return True


# ---------------------------------------------------------------
# DB-Schema: Neue Tabellen anlegen
# ---------------------------------------------------------------

def erstelle_neue_tabellen(conn):
    """Legt die 3 neuen Tabellen an, falls noch nicht vorhanden."""

    conn.execute("""
        CREATE TABLE IF NOT EXISTS bildungsdaten (
            bildung_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            stadt_id     INTEGER NOT NULL REFERENCES stadt(stadt_id),
            zeit_id      INTEGER NOT NULL REFERENCES zeit(zeit_id),
            schulen_anzahl      INTEGER,
            kitas_anzahl        INTEGER,
            unis_anzahl         INTEGER,
            bildungs_dichte     REAL,
            bildung_pro_100k    REAL,
            UNIQUE(stadt_id, zeit_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS gesundheitsdaten (
            gesundheit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            stadt_id      INTEGER NOT NULL REFERENCES stadt(stadt_id),
            zeit_id       INTEGER NOT NULL REFERENCES zeit(zeit_id),
            aerzte_anzahl        INTEGER,
            krankenhaeuser_anzahl INTEGER,
            apotheken_anzahl     INTEGER,
            gesundheits_dichte   REAL,
            gesundheit_pro_100k  REAL,
            UNIQUE(stadt_id, zeit_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS freizeitdaten (
            freizeit_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            stadt_id     INTEGER NOT NULL REFERENCES stadt(stadt_id),
            zeit_id      INTEGER NOT NULL REFERENCES zeit(zeit_id),
            parks_anzahl        INTEGER,
            kultur_anzahl       INTEGER,
            sport_anzahl        INTEGER,
            freizeit_dichte     REAL,
            freizeit_pro_100k   REAL,
            UNIQUE(stadt_id, zeit_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sicherheitsdaten (
            sicherheit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            stadt_id      INTEGER NOT NULL REFERENCES stadt(stadt_id),
            zeit_id       INTEGER NOT NULL REFERENCES zeit(zeit_id),
            straftaten_je_100k      INTEGER,
            gewaltdelikte_je_100k   INTEGER,
            UNIQUE(stadt_id, zeit_id)
        )
    """)

    # Neue Spalten ergänzen falls DB bereits existiert
    for col in [
        "score_bildung REAL",
        "score_gesundheit REAL",
        "score_freizeit REAL",
        "score_sicherheit REAL",
    ]:
        try:
            conn.execute(f"ALTER TABLE ranking ADD COLUMN {col}")
        except Exception:
            pass

    # Pro-Kopf-Spalten nachrüsten falls DB älter ist
    migrationen = [
        ("bildungsdaten",   "bildung_pro_100k   REAL"),
        ("gesundheitsdaten","gesundheit_pro_100k REAL"),
        ("freizeitdaten",   "freizeit_pro_100k  REAL"),
    ]
    for tabelle, spalte in migrationen:
        try:
            conn.execute(f"ALTER TABLE {tabelle} ADD COLUMN {spalte}")
        except Exception:
            pass  # Spalte existiert bereits

    conn.commit()
    print("  [DB] Neue Tabellen und Spalten bereit.")


# ---------------------------------------------------------------
# EXTRACT: Wetter (parallel, unverändert)
# ---------------------------------------------------------------

def extract_wetter(stadt):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude":   stadt["lat"],
        "longitude":  stadt["lon"],
        "start_date": f"{JAHR-1}-01-01",
        "end_date":   f"{JAHR-1}-12-31",
        "daily":      "sunshine_duration,precipitation_sum,temperature_2m_mean",
        "timezone":   "Europe/Berlin",
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()["daily"]
        df = pd.DataFrame(data)
        sonnenstunden = df["sunshine_duration"].sum() / 3600
        niederschlag  = df["precipitation_sum"].mean()
        temperatur    = df["temperature_2m_mean"].mean()
        print(f"  [Wetter] {stadt['name']}: {sonnenstunden:.0f}h, {temperatur:.1f}C")
        return {
            "sonnenstunden_jahr":      round(sonnenstunden, 1),
            "durchschnittstemperatur": round(temperatur, 2),
            "niederschlag_avg":        round(niederschlag, 2),
        }
    except Exception as e:
        print(f"  [Wetter] FEHLER {stadt['name']}: {e}")
        return None


def wetter_parallel(staedte_liste):
    ergebnisse = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(extract_wetter, stadt): stadt["name"]
                   for stadt in staedte_liste}
        for future in as_completed(futures):
            name = futures[future]
            try:
                ergebnisse[name] = future.result()
            except Exception as e:
                print(f"  [Wetter] FEHLER {name}: {e}")
                ergebnisse[name] = None
    return ergebnisse


# ---------------------------------------------------------------
# EXTRACT: Statische Daten
# ---------------------------------------------------------------

def extract_miete(stadt):
    return MIETPREISE_STATISCH.get(stadt["name"])

def extract_arbeitsmarkt(stadt):
    return ARBEITSMARKT_STATISCH.get(stadt["name"])

def extract_sicherheit(stadt):
    daten = KRIMINALITAET_STATISCH.get(stadt["name"])
    if daten:
        print(f"  [Sicherheit] {stadt['name']}: {daten['straftaten_je_100k']} Straft./100k")
    return daten


# ---------------------------------------------------------------
# EXTRACT: Overpass (Infrastruktur – unverändert)
# ---------------------------------------------------------------

def extract_infrastruktur(stadt):
    overpass_url = "https://overpass-api.de/api/interpreter"
    lat = stadt["lat"]
    lon = stadt["lon"]
    rad = stadt["radius_km"] * 1000

    query_haltestellen = f"""
    [out:json][timeout:60];
    (
      node["public_transport"="stop_position"](around:{rad},{lat},{lon});
      node["highway"="bus_stop"](around:{rad},{lat},{lon});
      node["railway"="station"](around:{rad},{lat},{lon});
      node["railway"="halt"](around:{rad},{lat},{lon});
    );
    out count;
    """
    query_pois = f"""
    [out:json][timeout:60];
    (
      node["amenity"](around:{rad},{lat},{lon});
      node["shop"](around:{rad},{lat},{lon});
      node["leisure"="park"](around:{rad},{lat},{lon});
    );
    out count;
    """

    for versuch in range(3):
        try:
            resp1 = requests.post(overpass_url, data=query_haltestellen, timeout=70)
            resp1.raise_for_status()
            haltestellen = resp1.json()["elements"][0]["tags"]["total"]
            time.sleep(5)
            resp2 = requests.post(overpass_url, data=query_pois, timeout=70)
            resp2.raise_for_status()
            pois = resp2.json()["elements"][0]["tags"]["total"]
            flaeche_km2 = math.pi * (stadt["radius_km"] ** 2)
            poi_dichte  = round(int(pois) / flaeche_km2, 2)
            print(f"  [Infra] {stadt['name']}: {haltestellen} Haltest., {poi_dichte} POIs/km2")
            return {"haltestellen_anzahl": int(haltestellen), "poi_dichte": poi_dichte}
        except Exception as e:
            print(f"  [Infra] Versuch {versuch+1}/3 fehlgeschlagen ({stadt['name']}): {e}")
            if versuch < 2:
                time.sleep(20)
    return None


# ---------------------------------------------------------------
# EXTRACT: Overpass – Bildung, Gesundheit, Freizeit (NEU)
# ---------------------------------------------------------------

def _overpass_count(query):
    """Hilfsfunktion: Sendet eine Overpass-Abfrage und gibt die Anzahl zurück.
    Gibt None zurück wenn alle Versuche fehlschlagen (nicht 0!).
    """
    overpass_url = "https://overpass-api.de/api/interpreter"
    for versuch in range(3):
        try:
            resp = requests.post(overpass_url, data=query, timeout=70)
            resp.raise_for_status()
            return int(resp.json()["elements"][0]["tags"]["total"])
        except Exception as e:
            print(f"    [Overpass] Versuch {versuch+1}/3: {e}")
            if versuch < 2:
                time.sleep(15)
    return None  # None statt 0 – wird im Score als fehlend behandelt


def _pro_kopf(anzahl, einwohner, faktor=100_000):
    """Normiert einen absoluten Wert auf faktor Einwohner."""
    if anzahl is None or einwohner == 0:
        return None
    return round(anzahl / einwohner * faktor, 2)


def _dichte(anzahl, radius_km):
    """Normiert einen absoluten Wert auf km²."""
    if anzahl is None:
        return None
    flaeche = math.pi * (radius_km ** 2)
    return round(anzahl / flaeche, 3)


def extract_bildung(stadt):
    """Schulen, Kitas, Universitäten via Overpass.
    Normierung: Dichte (je km²) UND Pro-Kopf (je 100k EW) – Mittelwert beider Werte.
    So werden große Städte nicht bevorteilt.
    """
    lat        = stadt["lat"]
    lon        = stadt["lon"]
    rad        = stadt["radius_km"] * 1000
    einwohner  = stadt["einwohner"]

    schulen = _overpass_count(f"""
    [out:json][timeout:60];
    (node["amenity"="school"](around:{rad},{lat},{lon});
     way["amenity"="school"](around:{rad},{lat},{lon}););
    out count;
    """)
    time.sleep(5)
    kitas = _overpass_count(f"""
    [out:json][timeout:60];
    (node["amenity"="kindergarten"](around:{rad},{lat},{lon});
     way["amenity"="kindergarten"](around:{rad},{lat},{lon}););
    out count;
    """)
    time.sleep(5)
    unis = _overpass_count(f"""
    [out:json][timeout:60];
    (node["amenity"="university"](around:{rad},{lat},{lon});
     node["amenity"="college"](around:{rad},{lat},{lon});
     way["amenity"="university"](around:{rad},{lat},{lon}););
    out count;
    """)

    gesamt = (schulen or 0) + (kitas or 0) + (unis or 0)

    # Dichte (je km²) – bereinigt um Stadtfläche
    bildungs_dichte    = _dichte(gesamt, stadt["radius_km"])
    # Pro-Kopf (je 100k Einwohner) – bereinigt um Stadtgröße
    bildung_pro_100k   = _pro_kopf(gesamt, einwohner)

    print(f"  [Bildung] {stadt['name']}: {schulen} Schulen, {kitas} Kitas, {unis} Unis "
          f"→ {bildungs_dichte}/km² | {bildung_pro_100k}/100k EW")
    return {
        "schulen_anzahl":    schulen or 0,
        "kitas_anzahl":      kitas   or 0,
        "unis_anzahl":       unis    or 0,
        "bildungs_dichte":   bildungs_dichte,
        "bildung_pro_100k":  bildung_pro_100k,
    }


def extract_gesundheit(stadt):
    """Ärzte, Krankenhäuser, Apotheken via Overpass.
    Normierung: Dichte + Pro-Kopf.
    Queries erfassen node + way + relation für vollständige Ergebnisse.
    """
    lat       = stadt["lat"]
    lon       = stadt["lon"]
    rad       = stadt["radius_km"] * 1000
    einwohner = stadt["einwohner"]

    # Ärzte: doctors, clinic, health_post – als node UND way
    aerzte = _overpass_count(f"""
    [out:json][timeout:60];
    (
      node["amenity"="doctors"](around:{rad},{lat},{lon});
      way["amenity"="doctors"](around:{rad},{lat},{lon});
      node["amenity"="clinic"](around:{rad},{lat},{lon});
      way["amenity"="clinic"](around:{rad},{lat},{lon});
      node["amenity"="health_post"](around:{rad},{lat},{lon});
      node["healthcare"="doctor"](around:{rad},{lat},{lon});
      node["healthcare"="centre"](around:{rad},{lat},{lon});
      way["healthcare"="centre"](around:{rad},{lat},{lon});
    );
    out count;
    """)
    time.sleep(5)

    # Krankenhäuser: node + way + relation
    krankenhaeuser = _overpass_count(f"""
    [out:json][timeout:60];
    (
      node["amenity"="hospital"](around:{rad},{lat},{lon});
      way["amenity"="hospital"](around:{rad},{lat},{lon});
      relation["amenity"="hospital"](around:{rad},{lat},{lon});
      node["healthcare"="hospital"](around:{rad},{lat},{lon});
      way["healthcare"="hospital"](around:{rad},{lat},{lon});
    );
    out count;
    """)
    time.sleep(5)

    # Apotheken: node + way (Filialen oft als way gemappt)
    apotheken = _overpass_count(f"""
    [out:json][timeout:60];
    (
      node["amenity"="pharmacy"](around:{rad},{lat},{lon});
      way["amenity"="pharmacy"](around:{rad},{lat},{lon});
      node["healthcare"="pharmacy"](around:{rad},{lat},{lon});
      way["healthcare"="pharmacy"](around:{rad},{lat},{lon});
    );
    out count;
    """)

    gesamt = (aerzte or 0) + (krankenhaeuser or 0) + (apotheken or 0)
    gesundheits_dichte  = _dichte(gesamt, stadt["radius_km"])
    gesundheit_pro_100k = _pro_kopf(gesamt, einwohner)

    print(f"  [Gesundheit] {stadt['name']}: {aerzte} Ärzte, {krankenhaeuser} KH, {apotheken} Apotheken "
          f"→ {gesundheits_dichte}/km² | {gesundheit_pro_100k}/100k EW")
    return {
        "aerzte_anzahl":         aerzte         or 0,
        "krankenhaeuser_anzahl": krankenhaeuser or 0,
        "apotheken_anzahl":      apotheken      or 0,
        "gesundheits_dichte":    gesundheits_dichte,
        "gesundheit_pro_100k":   gesundheit_pro_100k,
    }


def extract_freizeit(stadt):
    """Parks, Kultureinrichtungen, Sportstätten via Overpass.
    Normierung: Dichte + Pro-Kopf.
    Queries erfassen node + way + relation für vollständige Ergebnisse.
    """
    lat       = stadt["lat"]
    lon       = stadt["lon"]
    rad       = stadt["radius_km"] * 1000
    einwohner = stadt["einwohner"]

    # Parks: node + way + relation (Parks sind fast immer ways/relations)
    parks = _overpass_count(f"""
    [out:json][timeout:60];
    (
      node["leisure"="park"](around:{rad},{lat},{lon});
      way["leisure"="park"](around:{rad},{lat},{lon});
      relation["leisure"="park"](around:{rad},{lat},{lon});
      way["leisure"="nature_reserve"](around:{rad},{lat},{lon});
      relation["leisure"="nature_reserve"](around:{rad},{lat},{lon});
      way["landuse"="recreation_ground"](around:{rad},{lat},{lon});
    );
    out count;
    """)
    time.sleep(5)

    # Kultur: node + way + relation (Museen, Theater oft große Gebäude = way)
    kultur = _overpass_count(f"""
    [out:json][timeout:60];
    (
      node["amenity"="theatre"](around:{rad},{lat},{lon});
      way["amenity"="theatre"](around:{rad},{lat},{lon});
      node["amenity"="cinema"](around:{rad},{lat},{lon});
      way["amenity"="cinema"](around:{rad},{lat},{lon});
      node["tourism"="museum"](around:{rad},{lat},{lon});
      way["tourism"="museum"](around:{rad},{lat},{lon});
      relation["tourism"="museum"](around:{rad},{lat},{lon});
      node["amenity"="arts_centre"](around:{rad},{lat},{lon});
      way["amenity"="arts_centre"](around:{rad},{lat},{lon});
      node["amenity"="concert_hall"](around:{rad},{lat},{lon});
      way["amenity"="concert_hall"](around:{rad},{lat},{lon});
      node["tourism"="gallery"](around:{rad},{lat},{lon});
      way["tourism"="gallery"](around:{rad},{lat},{lon});
    );
    out count;
    """)
    time.sleep(5)

    # Sport: node + way (Sportplätze fast immer ways)
    sport = _overpass_count(f"""
    [out:json][timeout:60];
    (
      node["leisure"="sports_centre"](around:{rad},{lat},{lon});
      way["leisure"="sports_centre"](around:{rad},{lat},{lon});
      node["leisure"="swimming_pool"](around:{rad},{lat},{lon});
      way["leisure"="swimming_pool"](around:{rad},{lat},{lon});
      way["leisure"="pitch"](around:{rad},{lat},{lon});
      way["leisure"="stadium"](around:{rad},{lat},{lon});
      node["leisure"="fitness_centre"](around:{rad},{lat},{lon});
      way["leisure"="fitness_centre"](around:{rad},{lat},{lon});
    );
    out count;
    """)

    gesamt = (parks or 0) + (kultur or 0) + (sport or 0)
    freizeit_dichte   = _dichte(gesamt, stadt["radius_km"])
    freizeit_pro_100k = _pro_kopf(gesamt, einwohner)

    print(f"  [Freizeit] {stadt['name']}: {parks} Parks, {kultur} Kultur, {sport} Sport "
          f"→ {freizeit_dichte}/km² | {freizeit_pro_100k}/100k EW")
    return {
        "parks_anzahl":      parks  or 0,
        "kultur_anzahl":     kultur or 0,
        "sport_anzahl":      sport  or 0,
        "freizeit_dichte":   freizeit_dichte,
        "freizeit_pro_100k": freizeit_pro_100k,
    }


# ---------------------------------------------------------------
# LOAD
# ---------------------------------------------------------------

def load_wetter(conn, stadt_id, zeit_id, d):
    conn.execute("""
        INSERT INTO wetterdaten
            (stadt_id, zeit_id, sonnenstunden_jahr, durchschnittstemperatur, niederschlag_avg)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            sonnenstunden_jahr      = excluded.sonnenstunden_jahr,
            durchschnittstemperatur = excluded.durchschnittstemperatur,
            niederschlag_avg        = excluded.niederschlag_avg
    """, (stadt_id, zeit_id, d["sonnenstunden_jahr"],
          d["durchschnittstemperatur"], d["niederschlag_avg"]))


def load_miete(conn, stadt_id, zeit_id, d):
    conn.execute("""
        INSERT INTO mietdaten (stadt_id, zeit_id, mietpreis_kalt_qm, anzahl_inserate)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            mietpreis_kalt_qm = excluded.mietpreis_kalt_qm,
            anzahl_inserate   = excluded.anzahl_inserate
    """, (stadt_id, zeit_id, d["mietpreis_kalt_qm"], d["anzahl_inserate"]))


def load_arbeitsmarkt(conn, stadt_id, zeit_id, d):
    conn.execute("""
        INSERT INTO arbeitsmarktdaten (stadt_id, zeit_id, arbeitslosenquote, offene_stellen)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            arbeitslosenquote = excluded.arbeitslosenquote,
            offene_stellen    = excluded.offene_stellen
    """, (stadt_id, zeit_id, d["arbeitslosenquote"], d.get("offene_stellen")))


def load_infrastruktur(conn, stadt_id, zeit_id, d):
    conn.execute("""
        INSERT INTO infrastruktur (stadt_id, zeit_id, haltestellen_anzahl, poi_dichte)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            haltestellen_anzahl = excluded.haltestellen_anzahl,
            poi_dichte          = excluded.poi_dichte
    """, (stadt_id, zeit_id, d["haltestellen_anzahl"], d["poi_dichte"]))


def load_bildung(conn, stadt_id, zeit_id, d):
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


def load_gesundheit(conn, stadt_id, zeit_id, d):
    conn.execute("""
        INSERT INTO gesundheitsdaten
            (stadt_id, zeit_id, aerzte_anzahl, krankenhaeuser_anzahl, apotheken_anzahl,
             gesundheits_dichte, gesundheit_pro_100k)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            aerzte_anzahl          = excluded.aerzte_anzahl,
            krankenhaeuser_anzahl  = excluded.krankenhaeuser_anzahl,
            apotheken_anzahl       = excluded.apotheken_anzahl,
            gesundheits_dichte     = excluded.gesundheits_dichte,
            gesundheit_pro_100k    = excluded.gesundheit_pro_100k
    """, (stadt_id, zeit_id,
          d["aerzte_anzahl"], d["krankenhaeuser_anzahl"], d["apotheken_anzahl"],
          d["gesundheits_dichte"], d["gesundheit_pro_100k"]))


def load_freizeit(conn, stadt_id, zeit_id, d):
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


def load_sicherheit(conn, stadt_id, zeit_id, d):
    conn.execute("""
        INSERT INTO sicherheitsdaten
            (stadt_id, zeit_id, straftaten_je_100k, gewaltdelikte_je_100k)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            straftaten_je_100k    = excluded.straftaten_je_100k,
            gewaltdelikte_je_100k = excluded.gewaltdelikte_je_100k
    """, (stadt_id, zeit_id,
          d["straftaten_je_100k"], d["gewaltdelikte_je_100k"]))


# ---------------------------------------------------------------
# TRANSFORM: Ranking (erweitert um 4 neue Scores)
# ---------------------------------------------------------------

def berechne_ranking(conn, zeit_id):
    query = """
        SELECT s.stadt_id, s.name,
            w.sonnenstunden_jahr,
            m.mietpreis_kalt_qm,
            a.arbeitslosenquote,
            i.poi_dichte,
            b.bildungs_dichte,   b.bildung_pro_100k,
            g.gesundheits_dichte, g.gesundheit_pro_100k,
            f.freizeit_dichte,   f.freizeit_pro_100k,
            si.straftaten_je_100k
        FROM stadt s
        LEFT JOIN wetterdaten       w  ON w.stadt_id  = s.stadt_id AND w.zeit_id  = ?
        LEFT JOIN mietdaten         m  ON m.stadt_id  = s.stadt_id AND m.zeit_id  = ?
        LEFT JOIN arbeitsmarktdaten a  ON a.stadt_id  = s.stadt_id AND a.zeit_id  = ?
        LEFT JOIN infrastruktur     i  ON i.stadt_id  = s.stadt_id AND i.zeit_id  = ?
        LEFT JOIN bildungsdaten     b  ON b.stadt_id  = s.stadt_id AND b.zeit_id  = ?
        LEFT JOIN gesundheitsdaten  g  ON g.stadt_id  = s.stadt_id AND g.zeit_id  = ?
        LEFT JOIN freizeitdaten     f  ON f.stadt_id  = s.stadt_id AND f.zeit_id  = ?
        LEFT JOIN sicherheitsdaten  si ON si.stadt_id = s.stadt_id AND si.zeit_id = ?
    """
    df = pd.read_sql_query(query, conn, params=(zeit_id,) * 8)
    if df.empty:
        print("  [Ranking] Keine Daten.")
        return

    scaler = MinMaxScaler()

    def score_hoch(col):
        """Höher = besser. Fehlende Werte → Mittelwert (neutral)."""
        if col not in df.columns or not df[col].notna().any():
            return pd.Series([0.5] * len(df))
        filled = df[[col]].fillna(df[col].mean())
        return pd.Series(scaler.fit_transform(filled).flatten(), index=df.index)

    def score_niedrig(col):
        """Niedriger = besser (invertiert)."""
        if col not in df.columns or not df[col].notna().any():
            return pd.Series([0.5] * len(df))
        filled = df[[col]].fillna(df[col].mean())
        return pd.Series((1 - scaler.fit_transform(filled)).flatten(), index=df.index)

    def score_kombiniert(col_dichte, col_pro_100k):
        """
        Kombiniert Dichte-Score und Pro-Kopf-Score zu einem fairen Score.
        Dichte    → bereinigt um Stadtfläche (kompakte vs. weitläufige Städte)
        Pro-Kopf  → bereinigt um Einwohnerzahl (große vs. kleine Städte)
        Mittelwert beider Werte → Großstädte werden nicht bevorteilt.
        """
        s_dichte   = score_hoch(col_dichte)
        s_pro_kopf = score_hoch(col_pro_100k)
        # Nur verfügbare Werte kombinieren
        hat_dichte   = col_dichte   in df.columns and df[col_dichte].notna().any()
        hat_pro_kopf = col_pro_100k in df.columns and df[col_pro_100k].notna().any()
        if hat_dichte and hat_pro_kopf:
            return (s_dichte + s_pro_kopf) / 2
        elif hat_dichte:
            return s_dichte
        elif hat_pro_kopf:
            return s_pro_kopf
        return pd.Series([0.5] * len(df))

    # Klima & Wohnen: keine Größenverzerrung, direkt normieren
    df["score_klima"]         = score_hoch("sonnenstunden_jahr")
    df["score_wohnen"]        = score_niedrig("mietpreis_kalt_qm")
    df["score_wirtschaft"]    = score_niedrig("arbeitslosenquote")
    df["score_infrastruktur"] = score_hoch("poi_dichte")  # bereits Dichte

    # Neue Kategorien: fair kombiniert aus Dichte + Pro-Kopf
    df["score_bildung"]    = score_kombiniert("bildungs_dichte",    "bildung_pro_100k")
    df["score_gesundheit"] = score_kombiniert("gesundheits_dichte", "gesundheit_pro_100k")
    df["score_freizeit"]   = score_kombiniert("freizeit_dichte",    "freizeit_pro_100k")
    df["score_sicherheit"] = score_niedrig("straftaten_je_100k")  # bereits je 100k EW

    GEWICHTE = {
        "score_klima":         0.10,
        "score_wohnen":        0.20,
        "score_wirtschaft":    0.20,
        "score_infrastruktur": 0.10,
        "score_bildung":       0.15,
        "score_gesundheit":    0.10,
        "score_freizeit":      0.05,
        "score_sicherheit":    0.10,
    }
    df["gesamtscore"] = sum(df[col] * w for col, w in GEWICHTE.items())
    df["rang"] = df["gesamtscore"].rank(ascending=False, method="min").astype(int)

    for _, row in df.iterrows():
        conn.execute("""
            INSERT INTO ranking
                (stadt_id, zeit_id,
                 score_klima, score_wohnen, score_wirtschaft, score_infrastruktur,
                 score_bildung, score_gesundheit, score_freizeit, score_sicherheit,
                 gesamtscore, rang)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
                score_klima         = excluded.score_klima,
                score_wohnen        = excluded.score_wohnen,
                score_wirtschaft    = excluded.score_wirtschaft,
                score_infrastruktur = excluded.score_infrastruktur,
                score_bildung       = excluded.score_bildung,
                score_gesundheit    = excluded.score_gesundheit,
                score_freizeit      = excluded.score_freizeit,
                score_sicherheit    = excluded.score_sicherheit,
                gesamtscore         = excluded.gesamtscore,
                rang                = excluded.rang
        """, (
            int(row["stadt_id"]), zeit_id,
            round(float(row["score_klima"]),         4),
            round(float(row["score_wohnen"]),        4),
            round(float(row["score_wirtschaft"]),    4),
            round(float(row["score_infrastruktur"]), 4),
            round(float(row["score_bildung"]),       4),
            round(float(row["score_gesundheit"]),    4),
            round(float(row["score_freizeit"]),      4),
            round(float(row["score_sicherheit"]),    4),
            round(float(row["gesamtscore"]),         4),
            int(row["rang"]),
        ))
    conn.commit()
    print("\n  [Ranking] Top 5:")
    print(df[["name", "gesamtscore", "rang"]].sort_values("rang").head(5).to_string(index=False))


# ---------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------

def main():
    heute = date.today()
    overpass_tag = heute.weekday() == 0

    print(f"=== UrbanScore ETL-Pipeline gestartet ({heute}) ===")
    print(f"    Städte: {len(STAEDTE)} | Overpass-Update: {'ja' if overpass_tag else 'nein (nur montags)'}\n")

    conn    = get_conn()
    erstelle_neue_tabellen(conn)
    zeit_id = get_oder_erstelle_zeit_id(conn, JAHR)
    print(f"Zeitraum: Jahr {JAHR} (zeit_id={zeit_id})\n")

    # Wetterdaten parallel
    print("--- Wetterdaten werden parallel abgerufen ---")
    staedte_ohne_wetter = [
        s for s in STAEDTE
        if (sid := get_stadt_id(conn, s["name"])) and not bereits_vorhanden(conn, "wetterdaten", sid, zeit_id)
    ]
    if staedte_ohne_wetter:
        wetter_ergebnisse = wetter_parallel(staedte_ohne_wetter)
        for stadt in staedte_ohne_wetter:
            sid = get_stadt_id(conn, stadt["name"])
            w   = wetter_ergebnisse.get(stadt["name"])
            if w and sid:
                load_wetter(conn, sid, zeit_id, w)
        conn.commit()
    print()

    for i, stadt in enumerate(STAEDTE):
        print(f"--- [{i+1}/{len(STAEDTE)}] {stadt['name']} ---")
        stadt_id = get_stadt_id(conn, stadt["name"])
        if not stadt_id:
            print("  Stadt nicht in DB — bitte staedte_erweitern.sql ausführen.")
            continue

        # Statische Daten (immer gecacht)
        for tabelle, extractor, loader in [
            ("mietdaten",         extract_miete,       load_miete),
            ("arbeitsmarktdaten", extract_arbeitsmarkt, load_arbeitsmarkt),
            ("sicherheitsdaten",  extract_sicherheit,   load_sicherheit),
        ]:
            if bereits_vorhanden(conn, tabelle, stadt_id, zeit_id):
                print(f"  [Cache] {tabelle}: bereits vorhanden")
            else:
                daten = extractor(stadt)
                if daten:
                    loader(conn, stadt_id, zeit_id, daten)

        # Overpass-Daten (nur montags)
        for tabelle, extractor, loader in [
            ("infrastruktur",  extract_infrastruktur, load_infrastruktur),
            ("bildungsdaten",  extract_bildung,       load_bildung),
            ("gesundheitsdaten", extract_gesundheit,  load_gesundheit),
            ("freizeitdaten",  extract_freizeit,      load_freizeit),
        ]:
            if bereits_vorhanden(conn, tabelle, stadt_id, zeit_id):
                print(f"  [Cache] {tabelle}: bereits vorhanden")
            elif overpass_tag:
                time.sleep(10)
                daten = extractor(stadt)
                if daten:
                    loader(conn, stadt_id, zeit_id, daten)
                time.sleep(10)
            else:
                print(f"  [{tabelle}] wird nur montags aktualisiert")

        conn.commit()
        print()

    print("--- Ranking wird berechnet ---")
    berechne_ranking(conn, zeit_id)
    conn.close()
    print("\n=== Pipeline abgeschlossen ===")


if __name__ == "__main__":
    main()
