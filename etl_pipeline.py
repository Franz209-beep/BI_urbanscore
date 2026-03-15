"""
UrbanScore ETL-Pipeline
=======================
Wird täglich von GitHub Actions ausgeführt.
Holt Daten von APIs, bereinigt sie und schreibt sie in urbanscore.db

APIs:
- Open-Meteo:    Wetterdaten (kein Key)
- Overpass/OSM:  Infrastrukturdaten (kein Key)
- GENESIS:       Arbeitsmarktdaten (Username + Passwort als Env-Variablen)
- Mietdaten:     Statische Referenzwerte aus offiziellen Mietspiegeln
"""

import os
import math
import sqlite3
import requests
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from datetime import date

# ---------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------

DB_PATH = "urbanscore.db"

STAEDTE = [
    {"name": "Berlin",    "ags": "11000000", "lat": 52.52,  "lon": 13.405, "radius_km": 20},
    {"name": "Hamburg",   "ags": "02000000", "lat": 53.575, "lon": 10.015, "radius_km": 18},
    {"name": "München",   "ags": "09162000", "lat": 48.135, "lon": 11.582, "radius_km": 15},
    {"name": "Köln",      "ags": "05315000", "lat": 50.933, "lon":  6.950, "radius_km": 15},
    {"name": "Frankfurt", "ags": "06412000", "lat": 50.111, "lon":  8.682, "radius_km": 12},
]

# Statische Mietpreise aus offiziellen Mietspiegeln (€/m² Kaltmiete, Stand 2024)
MIETPREISE_STATISCH = {
    "Berlin":    {"mietpreis_kalt_qm": 13.20, "anzahl_inserate": 0},
    "Hamburg":   {"mietpreis_kalt_qm": 14.80, "anzahl_inserate": 0},
    "München":   {"mietpreis_kalt_qm": 20.50, "anzahl_inserate": 0},
    "Köln":      {"mietpreis_kalt_qm": 13.00, "anzahl_inserate": 0},
    "Frankfurt": {"mietpreis_kalt_qm": 15.30, "anzahl_inserate": 0},
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
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()["daily"]
        df = pd.DataFrame(data)

        sonnenstunden = df["sunshine_duration"].sum() / 3600
        niederschlag  = df["precipitation_sum"].mean()
        temperatur    = df["temperature_2m_mean"].mean()

        print(f"  [Wetter] {stadt['name']}: {sonnenstunden:.0f}h Sonne, "
              f"{temperatur:.1f}°C, {niederschlag:.1f}mm")
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
    [out:json][timeout:30];
    (
      node["public_transport"="stop_position"](around:{rad},{lat},{lon});
      node["highway"="bus_stop"](around:{rad},{lat},{lon});
      node["railway"="station"](around:{rad},{lat},{lon});
      node["railway"="halt"](around:{rad},{lat},{lon});
    );
    out count;
    """

    query_pois = f"""
    [out:json][timeout:30];
    (
      node["amenity"](around:{rad},{lat},{lon});
      node["shop"](around:{rad},{lat},{lon});
      node["leisure"="park"](around:{rad},{lat},{lon});
    );
    out count;
    """

    try:
        resp1 = requests.post(overpass_url, data=query_haltestellen, timeout=40)
        resp1.raise_for_status()
        haltestellen = resp1.json()["elements"][0]["tags"]["total"]

        resp2 = requests.post(overpass_url, data=query_pois, timeout=40)
        resp2.raise_for_status()
        pois = resp2.json()["elements"][0]["tags"]["total"]

        flaeche_km2 = math.pi * (stadt["radius_km"] ** 2)
        poi_dichte  = round(int(pois) / flaeche_km2, 2)

        print(f"  [Infra] {stadt['name']}: {haltestellen} Haltestellen, "
              f"{pois} POIs, {poi_dichte} POIs/km²")
        return {
            "haltestellen_anzahl": int(haltestellen),
            "poi_dichte":          poi_dichte,
        }
    except Exception as e:
        print(f"  [Infra] FEHLER {stadt['name']}: {e}")
        return None


# ---------------------------------------------------------------
# EXTRACT + TRANSFORM: Mietdaten (statische Referenzwerte)
# ---------------------------------------------------------------

def extract_miete(stadt):
    daten = MIETPREISE_STATISCH.get(stadt["name"])
    if daten:
        print(f"  [Miete] {stadt['name']}: {daten['mietpreis_kalt_qm']} €/m² (Mietspiegel)")
    return daten


# ---------------------------------------------------------------
# EXTRACT + TRANSFORM: Arbeitsmarkt (GENESIS Regionaldatenbank)
# ---------------------------------------------------------------

def extract_arbeitsmarkt(stadt):
    username = os.environ.get("GENESIS_USERNAME")
    password = os.environ.get("GENESIS_PASSWORD")

    if not username or not password:
        print(f"  [Arbeit] {stadt['name']}: Keine GENESIS-Zugangsdaten — "
              f"bitte GENESIS_USERNAME und GENESIS_PASSWORD als GitHub Secret hinterlegen")
        return None

    url = "https://www-genesis.destatis.de/genesisWS/rest/2020/data/table"
    params = {
        "username":    username,
        "password":    password,
        "name":        "13211-01-03-4",
        "area":        "all",
        "compress":    "false",
        "transpose":   "false",
        "startyear":   str(JAHR - 1),
        "endyear":     str(JAHR - 1),
        "regionalkey": stadt["ags"][:5],
        "format":      "json",
        "language":    "de",
    }

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if data.get("Status", {}).get("Code") != 0:
            print(f"  [Arbeit] {stadt['name']}: GENESIS Fehler — "
                  f"{data.get('Status', {}).get('Content')}")
            return None

        rows = data.get("Object", {}).get("Content", [])
        if not rows:
            print(f"  [Arbeit] {stadt['name']}: Keine Daten in GENESIS-Antwort")
            return None

        arbeitslosenquote = None
        for row in rows:
            wert = row.get("value")
            if wert and arbeitslosenquote is None:
                try:
                    arbeitslosenquote = float(str(wert).replace(",", "."))
                except ValueError:
                    pass

        if arbeitslosenquote is None:
            print(f"  [Arbeit] {stadt['name']}: Wert konnte nicht gelesen werden")
            return None

        print(f"  [Arbeit] {stadt['name']}: {arbeitslosenquote}% Arbeitslosigkeit")
        return {
            "arbeitslosenquote": arbeitslosenquote,
            "offene_stellen":    None,
        }
    except Exception as e:
        print(f"  [Arbeit] FEHLER {stadt['name']}: {e}")
        return None


# ---------------------------------------------------------------
# LOAD: Daten in SQLite schreiben
# ---------------------------------------------------------------

def load_wetter(conn, stadt_id, zeit_id, daten):
    conn.execute("""
        INSERT INTO wetterdaten
            (stadt_id, zeit_id, sonnenstunden_jahr, durchschnittstemperatur, niederschlag_avg)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            sonnenstunden_jahr      = excluded.sonnenstunden_jahr,
            durchschnittstemperatur = excluded.durchschnittstemperatur,
            niederschlag_avg        = excluded.niederschlag_avg
    """, (stadt_id, zeit_id,
          daten["sonnenstunden_jahr"],
          daten["durchschnittstemperatur"],
          daten["niederschlag_avg"]))


def load_miete(conn, stadt_id, zeit_id, daten):
    conn.execute("""
        INSERT INTO mietdaten (stadt_id, zeit_id, mietpreis_kalt_qm, anzahl_inserate)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            mietpreis_kalt_qm = excluded.mietpreis_kalt_qm,
            anzahl_inserate   = excluded.anzahl_inserate
    """, (stadt_id, zeit_id,
          daten["mietpreis_kalt_qm"],
          daten["anzahl_inserate"]))


def load_arbeitsmarkt(conn, stadt_id, zeit_id, daten):
    conn.execute("""
        INSERT INTO arbeitsmarktdaten (stadt_id, zeit_id, arbeitslosenquote, offene_stellen)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            arbeitslosenquote = excluded.arbeitslosenquote,
            offene_stellen    = excluded.offene_stellen
    """, (stadt_id, zeit_id,
          daten["arbeitslosenquote"],
          daten.get("offene_stellen")))


def load_infrastruktur(conn, stadt_id, zeit_id, daten):
    conn.execute("""
        INSERT INTO infrastruktur (stadt_id, zeit_id, haltestellen_anzahl, poi_dichte)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            haltestellen_anzahl = excluded.haltestellen_anzahl,
            poi_dichte          = excluded.poi_dichte
    """, (stadt_id, zeit_id,
          daten["haltestellen_anzahl"],
          daten["poi_dichte"]))


# ---------------------------------------------------------------
# TRANSFORM: Ranking berechnen
# ---------------------------------------------------------------

def berechne_ranking(conn, zeit_id):
    query = """
        SELECT
            s.stadt_id, s.name,
            w.sonnenstunden_jahr,
            m.mietpreis_kalt_qm,
            a.arbeitslosenquote,
            i.poi_dichte
        FROM stadt s
        LEFT JOIN wetterdaten       w ON w.stadt_id = s.stadt_id AND w.zeit_id = ?
        LEFT JOIN mietdaten         m ON m.stadt_id = s.stadt_id AND m.zeit_id = ?
        LEFT JOIN arbeitsmarktdaten a ON a.stadt_id = s.stadt_id AND a.zeit_id = ?
        LEFT JOIN infrastruktur     i ON i.stadt_id = s.stadt_id AND i.zeit_id = ?
    """
    df = pd.read_sql_query(query, conn, params=(zeit_id,) * 4)

    if df.empty:
        print("  [Ranking] Keine Daten vorhanden.")
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

    GEWICHTE = {
        "score_klima":         0.20,
        "score_wohnen":        0.30,
        "score_wirtschaft":    0.30,
        "score_infrastruktur": 0.20,
    }
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

    print(f"\n  [Ranking] Ergebnis:")
    print(df[["name", "score_klima", "score_wohnen",
              "score_wirtschaft", "score_infrastruktur",
              "gesamtscore", "rang"]].sort_values("rang").to_string(index=False))


# ---------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------

def main():
    print(f"=== UrbanScore ETL-Pipeline gestartet ({date.today()}) ===")
    conn = get_conn()
    zeit_id = get_oder_erstelle_zeit_id(conn, JAHR)
    print(f"Zeitraum: Jahr {JAHR} (zeit_id={zeit_id})\n")

    for stadt in STAEDTE:
        print(f"--- {stadt['name']} ---")
        stadt_id = get_stadt_id(conn, stadt["name"])
        if not stadt_id:
            print(f"  Stadt nicht in DB — bitte urbanscore_setup.sql ausführen.")
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

        infra = extract_infrastruktur(stadt)
        if infra:
            load_infrastruktur(conn, stadt_id, zeit_id, infra)

        print()

    conn.commit()
    print("--- Ranking wird berechnet ---")
    berechne_ranking(conn, zeit_id)
    conn.close()
    print("\n=== Pipeline abgeschlossen ===")


if __name__ == "__main__":
    main()
