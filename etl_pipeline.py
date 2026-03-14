"""
UrbanScore ETL-Pipeline
=======================
Wird täglich von GitHub Actions ausgeführt.
Holt Daten von 4 APIs, bereinigt sie und schreibt sie in urbanscore.db
"""

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
    {"name": "Berlin",    "ags": "11000000", "lat": 52.52,  "lon": 13.405},
    {"name": "Hamburg",   "ags": "02000000", "lat": 53.575, "lon": 10.015},
    {"name": "München",   "ags": "09162000", "lat": 48.135, "lon": 11.582},
    {"name": "Köln",      "ags": "05315000", "lat": 50.933, "lon":  6.950},
    {"name": "Frankfurt", "ags": "06412000", "lat": 50.111, "lon":  8.682},
]

JAHR = date.today().year

# ---------------------------------------------------------------
# Hilfsfunktion: Datenbankverbindung
# ---------------------------------------------------------------

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_oder_erstelle_zeit_id(conn, jahr):
    """Gibt die zeit_id für das aktuelle Jahr zurück, legt sie ggf. an."""
    label = f"Jahr {jahr}"
    row = conn.execute(
        "SELECT zeit_id FROM zeit WHERE jahr = ? AND quartal IS NULL",
        (jahr,)
    ).fetchone()
    if row:
        return row[0]
    cursor = conn.execute(
        "INSERT INTO zeit (jahr, zeitraum_label) VALUES (?, ?)",
        (jahr, label)
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
# Keine Authentifizierung nötig — direkt einsetzbar
# ---------------------------------------------------------------

def extract_wetter(stadt):
    """
    Ruft die Open-Meteo Archive API ab und aggregiert Tageswerte zu Jahreswerten.
    Gibt ein dict mit den bereinigten Werten zurück.
    """
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude":           stadt["lat"],
        "longitude":          stadt["lon"],
        "start_date":         f"{JAHR-1}-01-01",
        "end_date":           f"{JAHR-1}-12-31",
        "daily":              "sunshine_duration,precipitation_sum,temperature_2m_mean",
        "timezone":           "Europe/Berlin",
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()["daily"]
        df = pd.DataFrame(data)

        sonnenstunden   = df["sunshine_duration"].sum() / 3600   # Sekunden → Stunden
        niederschlag    = df["precipitation_sum"].mean()
        temperatur      = df["temperature_2m_mean"].mean()

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
# EXTRACT + TRANSFORM: ImmoScout24
# Platzhalter — OAuth 2.0 Token erforderlich
# ---------------------------------------------------------------

def extract_miete(stadt):
    """
    TODO: OAuth-2.0-Token in GitHub Secret hinterlegen (IMMOSCOUT_TOKEN).
    Dann hier den echten API-Aufruf implementieren.
    Rückgabe: {"mietpreis_kalt_qm": float, "anzahl_inserate": int}
    """
    # Beispiel-Struktur (ersetzen sobald API-Zugang vorhanden):
    # token = os.environ["IMMOSCOUT_TOKEN"]
    # url = f"https://rest.immobilienscout24.de/restapi/api/search/v1.0/..."
    # ...Ausreißer entfernen, Median berechnen...

    print(f"  [Miete] {stadt['name']}: Platzhalter — API noch nicht verbunden")
    return None  # None → kein Datenbankeintrag für diese Stadt


# ---------------------------------------------------------------
# EXTRACT + TRANSFORM: Arbeitsagentur
# Platzhalter — API-Key erforderlich
# ---------------------------------------------------------------

def extract_arbeitsmarkt(stadt):
    """
    TODO: API-Key in GitHub Secret hinterlegen (ARBEITSAGENTUR_KEY).
    Rückgabe: {"arbeitslosenquote": float, "offene_stellen": int}
    """
    print(f"  [Arbeit] {stadt['name']}: Platzhalter — API noch nicht verbunden")
    return None


# ---------------------------------------------------------------
# EXTRACT + TRANSFORM: Overpass / OSM
# Platzhalter — kein Key nötig, aber Query muss gebaut werden
# ---------------------------------------------------------------

def extract_infrastruktur(stadt):
    """
    TODO: Overpass QL Query implementieren.
    Haltestellen zählen, POI-Dichte berechnen (POIs / Stadtfläche km²).
    Rückgabe: {"haltestellen_anzahl": int, "poi_dichte": float}
    """
    print(f"  [Infra] {stadt['name']}: Platzhalter — Query noch nicht implementiert")
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
    """, (
        stadt_id, zeit_id,
        daten["sonnenstunden_jahr"],
        daten["durchschnittstemperatur"],
        daten["niederschlag_avg"],
    ))


def load_miete(conn, stadt_id, zeit_id, daten):
    conn.execute("""
        INSERT INTO mietdaten (stadt_id, zeit_id, mietpreis_kalt_qm, anzahl_inserate)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            mietpreis_kalt_qm = excluded.mietpreis_kalt_qm,
            anzahl_inserate   = excluded.anzahl_inserate
    """, (stadt_id, zeit_id, daten["mietpreis_kalt_qm"], daten["anzahl_inserate"]))


def load_arbeitsmarkt(conn, stadt_id, zeit_id, daten):
    conn.execute("""
        INSERT INTO arbeitsmarktdaten (stadt_id, zeit_id, arbeitslosenquote, offene_stellen)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            arbeitslosenquote = excluded.arbeitslosenquote,
            offene_stellen    = excluded.offene_stellen
    """, (stadt_id, zeit_id, daten["arbeitslosenquote"], daten["offene_stellen"]))


def load_infrastruktur(conn, stadt_id, zeit_id, daten):
    conn.execute("""
        INSERT INTO infrastruktur (stadt_id, zeit_id, haltestellen_anzahl, poi_dichte)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
            haltestellen_anzahl = excluded.haltestellen_anzahl,
            poi_dichte          = excluded.poi_dichte
    """, (stadt_id, zeit_id, daten["haltestellen_anzahl"], daten["poi_dichte"]))


# ---------------------------------------------------------------
# TRANSFORM: Ranking berechnen und speichern
# Läuft nachdem alle Faktentabellen befüllt sind
# ---------------------------------------------------------------

def berechne_ranking(conn, zeit_id):
    """
    Liest alle verfügbaren Metriken für den Zeitraum,
    normalisiert sie (Min-Max 0–1) und berechnet den Gesamtscore.
    Gewichtung: Klima 20%, Wohnen 30%, Wirtschaft 30%, Infrastruktur 20%
    """
    query = """
        SELECT
            s.stadt_id,
            s.name,
            w.sonnenstunden_jahr,
            w.durchschnittstemperatur,
            m.mietpreis_kalt_qm,
            a.arbeitslosenquote,
            a.offene_stellen,
            i.poi_dichte
        FROM stadt s
        LEFT JOIN wetterdaten        w ON w.stadt_id = s.stadt_id AND w.zeit_id = ?
        LEFT JOIN mietdaten          m ON m.stadt_id = s.stadt_id AND m.zeit_id = ?
        LEFT JOIN arbeitsmarktdaten  a ON a.stadt_id = s.stadt_id AND a.zeit_id = ?
        LEFT JOIN infrastruktur      i ON i.stadt_id = s.stadt_id AND i.zeit_id = ?
    """
    df = pd.read_sql_query(query, conn, params=(zeit_id,) * 4)

    if df.empty:
        print("  [Ranking] Keine Daten vorhanden.")
        return

    scaler = MinMaxScaler()

    # Klima-Score: viele Sonnenstunden = gut (höher = besser)
    if df["sonnenstunden_jahr"].notna().any():
        df["score_klima"] = scaler.fit_transform(
            df[["sonnenstunden_jahr"]].fillna(df["sonnenstunden_jahr"].mean())
        )
    else:
        df["score_klima"] = None

    # Wohn-Score: niedriger Mietpreis = gut (invertiert)
    if df["mietpreis_kalt_qm"].notna().any():
        df["score_wohnen"] = 1 - scaler.fit_transform(
            df[["mietpreis_kalt_qm"]].fillna(df["mietpreis_kalt_qm"].mean())
        )
    else:
        df["score_wohnen"] = None

    # Wirtschafts-Score: niedrige Arbeitslosigkeit = gut (invertiert)
    if df["arbeitslosenquote"].notna().any():
        df["score_wirtschaft"] = 1 - scaler.fit_transform(
            df[["arbeitslosenquote"]].fillna(df["arbeitslosenquote"].mean())
        )
    else:
        df["score_wirtschaft"] = None

    # Infrastruktur-Score: hohe POI-Dichte = gut
    if df["poi_dichte"].notna().any():
        df["score_infrastruktur"] = scaler.fit_transform(
            df[["poi_dichte"]].fillna(df["poi_dichte"].mean())
        )
    else:
        df["score_infrastruktur"] = None

    # Gesamtscore (nur verfügbare Scores gewichten)
    GEWICHTE = {
        "score_klima":         0.20,
        "score_wohnen":        0.30,
        "score_wirtschaft":    0.30,
        "score_infrastruktur": 0.20,
    }
    df["gesamtscore"] = sum(
        df[col].fillna(0) * w for col, w in GEWICHTE.items()
        if col in df.columns
    )
    df["rang"] = df["gesamtscore"].rank(ascending=False, method="min").astype(int)

    # In Datenbank schreiben
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
            row.get("score_klima"),   row.get("score_wohnen"),
            row.get("score_wirtschaft"), row.get("score_infrastruktur"),
            round(float(row["gesamtscore"]), 4),
            int(row["rang"]),
        ))
    conn.commit()
    print(f"  [Ranking] Berechnet für {len(df)} Städte.")
    print(df[["name", "gesamtscore", "rang"]].sort_values("rang").to_string(index=False))


# ---------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------

def main():
    print(f"=== UrbanScore ETL-Pipeline gestartet ({date.today()}) ===")
    conn = get_conn()
    zeit_id = get_oder_erstelle_zeit_id(conn, JAHR)
    print(f"Zeitraum: Jahr {JAHR} (zeit_id={zeit_id})")

    for stadt in STAEDTE:
        print(f"\n--- {stadt['name']} ---")
        stadt_id = get_stadt_id(conn, stadt["name"])
        if not stadt_id:
            print(f"  Stadt nicht in DB — bitte urbanscore_setup.sql ausführen.")
            continue

        # Wetter (direkt einsetzbar)
        wetter = extract_wetter(stadt)
        if wetter:
            load_wetter(conn, stadt_id, zeit_id, wetter)

        # Weitere APIs (sobald Keys vorhanden)
        miete = extract_miete(stadt)
        if miete:
            load_miete(conn, stadt_id, zeit_id, miete)

        arbeitsmarkt = extract_arbeitsmarkt(stadt)
        if arbeitsmarkt:
            load_arbeitsmarkt(conn, stadt_id, zeit_id, arbeitsmarkt)

        infra = extract_infrastruktur(stadt)
        if infra:
            load_infrastruktur(conn, stadt_id, zeit_id, infra)

    conn.commit()

    print("\n--- Ranking wird berechnet ---")
    berechne_ranking(conn, zeit_id)
    conn.close()
    print("\n=== Pipeline abgeschlossen ===")


if __name__ == "__main__":
    main()
