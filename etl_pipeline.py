"""
UrbanScore ETL-Pipeline
=======================
Wird täglich von GitHub Actions ausgeführt.
Analysiert die 20 größten deutschen Städte.
"""

import os
import math
import time
import sqlite3
import requests
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from datetime import date

# ---------------------------------------------------------------
# Konfiguration: 20 größte deutsche Städte
# ---------------------------------------------------------------

DB_PATH = "urbanscore.db"

STAEDTE = [
    {"name": "Berlin",      "ags": "11000000", "lat": 52.5200, "lon": 13.4050, "radius_km": 20},
    {"name": "Hamburg",     "ags": "02000000", "lat": 53.5753, "lon": 10.0153, "radius_km": 18},
    {"name": "München",     "ags": "09162000", "lat": 48.1351, "lon": 11.5820, "radius_km": 15},
    {"name": "Köln",        "ags": "05315000", "lat": 50.9333, "lon":  6.9500, "radius_km": 15},
    {"name": "Frankfurt",   "ags": "06412000", "lat": 50.1109, "lon":  8.6821, "radius_km": 12},
    {"name": "Düsseldorf",  "ags": "05111000", "lat": 51.2217, "lon":  6.7762, "radius_km": 12},
    {"name": "Stuttgart",   "ags": "08111000", "lat": 48.7758, "lon":  9.1829, "radius_km": 12},
    {"name": "Leipzig",     "ags": "14713000", "lat": 51.3397, "lon": 12.3731, "radius_km": 12},
    {"name": "Dortmund",    "ags": "05913000", "lat": 51.5136, "lon":  7.4653, "radius_km": 12},
    {"name": "Bremen",      "ags": "04011000", "lat": 53.0793, "lon":  8.8017, "radius_km": 12},
    {"name": "Essen",       "ags": "05113000", "lat": 51.4556, "lon":  7.0116, "radius_km": 10},
    {"name": "Dresden",     "ags": "14612000", "lat": 51.0504, "lon": 13.7373, "radius_km": 12},
    {"name": "Hannover",    "ags": "03241001", "lat": 52.3759, "lon":  9.7320, "radius_km": 12},
    {"name": "Nürnberg",    "ags": "09564000", "lat": 49.4521, "lon": 11.0767, "radius_km": 12},
    {"name": "Duisburg",    "ags": "05112000", "lat": 51.4344, "lon":  6.7623, "radius_km": 10},
    {"name": "Bochum",      "ags": "05911000", "lat": 51.4818, "lon":  7.2162, "radius_km": 10},
    {"name": "Wuppertal",   "ags": "05124000", "lat": 51.2562, "lon":  7.1508, "radius_km": 10},
    {"name": "Bielefeld",   "ags": "05711000", "lat": 52.0302, "lon":  8.5325, "radius_km": 10},
    {"name": "Bonn",        "ags": "05314000", "lat": 50.7374, "lon":  7.0982, "radius_km": 10},
    {"name": "Münster",     "ags": "05515000", "lat": 51.9607, "lon":  7.6261, "radius_km": 10},
]

# Mietpreise aus offiziellen Mietspiegeln (€/m² Kaltmiete, Stand 2024)
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

# Arbeitslosenquoten (%, Stand Q4 2024, Quelle: Bundesagentur für Arbeit)
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

JAHR = date.today().year


# ---------------------------------------------------------------
# Hilfsfunktionen
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
    row = conn.execute(
        "SELECT stadt_id FROM stadt WHERE name = ?", (name,)
    ).fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------
# EXTRACT + TRANSFORM: Open-Meteo (Wetter)
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
        print(f"  [Wetter] {stadt['name']}: {sonnenstunden:.0f}h, {temperatur:.1f}°C")
        return {
            "sonnenstunden_jahr":      round(sonnenstunden, 1),
            "durchschnittstemperatur": round(temperatur, 2),
            "niederschlag_avg":        round(niederschlag, 2),
        }
    except Exception as e:
        print(f"  [Wetter] FEHLER {stadt['name']}: {e}")
        return None


# ---------------------------------------------------------------
# EXTRACT + TRANSFORM: Overpass / OSM (Infrastruktur)
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
            print(f"  [Infra] {stadt['name']}: {haltestellen} Haltest., {poi_dichte} POIs/km²")
            return {"haltestellen_anzahl": int(haltestellen), "poi_dichte": poi_dichte}
        except Exception as e:
            print(f"  [Infra] Versuch {versuch+1}/3 fehlgeschlagen ({stadt['name']}): {e}")
            if versuch < 2:
                time.sleep(20)

    print(f"  [Infra] {stadt['name']}: alle Versuche fehlgeschlagen")
    return None


# ---------------------------------------------------------------
# EXTRACT: Statische Daten
# ---------------------------------------------------------------

def extract_miete(stadt):
    daten = MIETPREISE_STATISCH.get(stadt["name"])
    if daten:
        print(f"  [Miete] {stadt['name']}: {daten['mietpreis_kalt_qm']} EUR/m2")
    return daten


def extract_arbeitsmarkt(stadt):
    daten = ARBEITSMARKT_STATISCH.get(stadt["name"])
    if daten:
        print(f"  [Arbeit] {stadt['name']}: {daten['arbeitslosenquote']}%")
    return daten


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
    """, (stadt_id, zeit_id, d["sonnenstunden_jahr"], d["durchschnittstemperatur"], d["niederschlag_avg"]))


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


# ---------------------------------------------------------------
# TRANSFORM: Ranking
# ---------------------------------------------------------------

def berechne_ranking(conn, zeit_id):
    query = """
        SELECT s.stadt_id, s.name,
            w.sonnenstunden_jahr, m.mietpreis_kalt_qm,
            a.arbeitslosenquote,  i.poi_dichte
        FROM stadt s
        LEFT JOIN wetterdaten       w ON w.stadt_id = s.stadt_id AND w.zeit_id = ?
        LEFT JOIN mietdaten         m ON m.stadt_id = s.stadt_id AND m.zeit_id = ?
        LEFT JOIN arbeitsmarktdaten a ON a.stadt_id = s.stadt_id AND a.zeit_id = ?
        LEFT JOIN infrastruktur     i ON i.stadt_id = s.stadt_id AND i.zeit_id = ?
    """
    df = pd.read_sql_query(query, conn, params=(zeit_id,) * 4)
    if df.empty:
        print("  [Ranking] Keine Daten.")
        return

    scaler = MinMaxScaler()

    df["score_klima"] = scaler.fit_transform(
        df[["sonnenstunden_jahr"]].fillna(df["sonnenstunden_jahr"].mean())
    ) if df["sonnenstunden_jahr"].notna().any() else 0.5

    df["score_wohnen"] = 1 - scaler.fit_transform(
        df[["mietpreis_kalt_qm"]].fillna(df["mietpreis_kalt_qm"].mean())
    ) if df["mietpreis_kalt_qm"].notna().any() else 0.5

    df["score_wirtschaft"] = 1 - scaler.fit_transform(
        df[["arbeitslosenquote"]].fillna(df["arbeitslosenquote"].mean())
    ) if df["arbeitslosenquote"].notna().any() else 0.5

    df["score_infrastruktur"] = scaler.fit_transform(
        df[["poi_dichte"]].fillna(df["poi_dichte"].mean())
    ) if df["poi_dichte"].notna().any() else 0.5

    GEWICHTE = {"score_klima": 0.20, "score_wohnen": 0.30,
                "score_wirtschaft": 0.30, "score_infrastruktur": 0.20}
    df["gesamtscore"] = sum(df[col] * w for col, w in GEWICHTE.items())
    df["rang"] = df["gesamtscore"].rank(ascending=False, method="min").astype(int)

    for _, row in df.iterrows():
        conn.execute("""
            INSERT INTO ranking
                (stadt_id, zeit_id, score_klima, score_wohnen,
                 score_wirtschaft, score_infrastruktur, gesamtscore, rang)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
                score_klima         = excluded.score_klima,
                score_wohnen        = excluded.score_wohnen,
                score_wirtschaft    = excluded.score_wirtschaft,
                score_infrastruktur = excluded.score_infrastruktur,
                gesamtscore         = excluded.gesamtscore,
                rang                = excluded.rang
        """, (
            int(row["stadt_id"]), zeit_id,
            round(float(row["score_klima"]),         4),
            round(float(row["score_wohnen"]),        4),
            round(float(row["score_wirtschaft"]),    4),
            round(float(row["score_infrastruktur"]), 4),
            round(float(row["gesamtscore"]),         4),
            int(row["rang"]),
        ))
    conn.commit()
    print("\n  [Ranking] Top 5:")
    print(df[["name","gesamtscore","rang"]].sort_values("rang").head(5).to_string(index=False))


# ---------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------

def main():
    print(f"=== UrbanScore ETL-Pipeline gestartet ({date.today()}) ===")
    print(f"    Analysiere {len(STAEDTE)} Städte\n")
    conn    = get_conn()
    zeit_id = get_oder_erstelle_zeit_id(conn, JAHR)
    print(f"Zeitraum: Jahr {JAHR} (zeit_id={zeit_id})\n")

    for i, stadt in enumerate(STAEDTE):
        print(f"--- [{i+1}/{len(STAEDTE)}] {stadt['name']} ---")
        stadt_id = get_stadt_id(conn, stadt["name"])
        if not stadt_id:
            print(f"  Stadt nicht in DB — bitte staedte_erweitern.sql in DBeaver ausführen.")
            continue

        wetter = extract_wetter(stadt)
        if wetter:
            load_wetter(conn, stadt_id, zeit_id, wetter)

        miete = extract_miete(stadt)
        if miete:
            load_miete(conn, stadt_id, zeit_id, miete)

        arbeitsmarkt = extract_arbeitsmarkt(stadt)
        if arbeitsmarkt:
            load_arbeitsmarkt(conn, stadt_id, zeit_id, arbeitsmarkt)

        time.sleep(20)
        infra = extract_infrastruktur(stadt)
        if infra:
            load_infrastruktur(conn, stadt_id, zeit_id, infra)

        time.sleep(10)
        print()

    conn.commit()
    print("--- Ranking wird berechnet ---")
    berechne_ranking(conn, zeit_id)
    conn.close()
    print("\n=== Pipeline abgeschlossen ===")


if __name__ == "__main__":
    main()
