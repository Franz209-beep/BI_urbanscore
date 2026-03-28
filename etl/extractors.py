"""
etl/extractors.py — Datenbeschaffung aus externen Quellen
==========================================================
Enthält alle Extract-Funktionen der Pipeline:
  - Wetterdaten    (Open-Meteo API, parallel)
  - Infrastruktur  (Overpass API)
  - Bildung, Gesundheit, Freizeit (Overpass, generisch)
  - Miete, Arbeitsmarkt, Sicherheit (statische Daten + BA-API-Versuch)

Jede Funktion gibt ein Dict mit den Rohdaten zurück, oder None bei Fehler.
None-Rückgaben werden in pipeline.py übersprungen und nicht in die DB geschrieben.
"""

import math
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

import config

# ---------------------------------------------------------------------------
# Interne Hilfsfunktionen
# ---------------------------------------------------------------------------

def _dichte(anzahl: int | None, radius_km: float) -> float | None:
    """Normiert einen absoluten Zählwert auf Einrichtungen pro km²."""
    if anzahl is None:
        return None
    return round(anzahl / (math.pi * radius_km**2), 3)


def _pro_100k(anzahl: int | None, einwohner: int) -> float | None:
    """Normiert einen absoluten Zählwert auf 100.000 Einwohner."""
    if anzahl is None or einwohner == 0:
        return None
    return round(anzahl / einwohner * 100_000, 2)


def _overpass_count(query: str, max_versuche: int = 3, pause_s: int = 15) -> int | None:
    """
    Sendet eine Overpass-QL-Abfrage und gibt die Trefferanzahl zurück.
    Gibt None (nicht 0!) zurück wenn alle Versuche fehlschlagen, damit
    der Aufrufer zwischen "keine Einrichtungen" und "Timeout" unterscheiden kann.
    """
    url = "https://overpass-api.de/api/interpreter"
    for versuch in range(max_versuche):
        try:
            resp = requests.post(url, data=query, timeout=70)
            resp.raise_for_status()
            return int(resp.json()["elements"][0]["tags"]["total"])
        except Exception as exc:
            print(f"    [Overpass] Versuch {versuch + 1}/{max_versuche}: {exc}")
            if versuch < max_versuche - 1:
                time.sleep(pause_s)
    return None  # Timeout – wird im Score als fehlend behandelt


# ---------------------------------------------------------------------------
# Overpass: Generische Kategorie-Funktion
# ---------------------------------------------------------------------------
# Alle drei Kategorien (Bildung, Gesundheit, Freizeit) folgen demselben Muster:
# 3 Overpass-Abfragen → Absolute Zählwerte → Dichte + Pro-Kopf-Normierung.
# Statt drei fast identische Funktionen zu haben, werden sie durch eine
# generische Funktion mit einer Query-Konfiguration beschrieben.

# Typ: Liste von (Feldname, Overpass-Query-Template)
# Das Query-Template enthält {rad}, {lat}, {lon} als Platzhalter.
KategorieConfig = list[tuple[str, str]]


def _extract_overpass_kategorie(
    stadt: dict,
    felder: KategorieConfig,
    prefix: str,
) -> dict | None:
    """
    Generische Overpass-Extraktion für eine Dimension (Bildung/Gesundheit/Freizeit).

    Args:
        stadt:  Stadtdict aus config.STAEDTE
        felder: Liste von (feldname, overpass_query) Tupeln
        prefix: Präfix für Dichte/Pro-Kopf-Felder, z.B. "bildungs"

    Returns:
        Dict mit Rohdaten + Dichte + Pro-100k, oder None bei komplettem Fehler
    """
    lat, lon      = stadt["lat"], stadt["lon"]
    rad           = stadt["radius_km"] * 1000
    einwohner     = stadt["einwohner"]
    ergebnis      = {}
    gesamt        = 0

    for feldname, query_template in felder:
        query   = query_template.format(rad=rad, lat=lat, lon=lon)
        anzahl  = _overpass_count(query)
        ergebnis[feldname] = anzahl or 0
        gesamt += anzahl or 0
        time.sleep(5)  # Overpass-Rate-Limit einhalten

    ergebnis[f"{prefix}_dichte"]   = _dichte(gesamt, stadt["radius_km"])
    ergebnis[f"{prefix}_pro_100k"] = _pro_100k(gesamt, einwohner)
    return ergebnis


# ---------------------------------------------------------------------------
# Overpass: Query-Konfigurationen pro Kategorie
# ---------------------------------------------------------------------------

_BILDUNG_FELDER: KategorieConfig = [
    ("schulen_anzahl", """
        [out:json][timeout:60];
        (node["amenity"="school"](around:{rad},{lat},{lon});
         way["amenity"="school"](around:{rad},{lat},{lon}););
        out count;
    """),
    ("kitas_anzahl", """
        [out:json][timeout:60];
        (node["amenity"="kindergarten"](around:{rad},{lat},{lon});
         way["amenity"="kindergarten"](around:{rad},{lat},{lon}););
        out count;
    """),
    ("unis_anzahl", """
        [out:json][timeout:60];
        (node["amenity"="university"](around:{rad},{lat},{lon});
         node["amenity"="college"](around:{rad},{lat},{lon});
         way["amenity"="university"](around:{rad},{lat},{lon}););
        out count;
    """),
]

_GESUNDHEIT_FELDER: KategorieConfig = [
    ("aerzte_anzahl", """
        [out:json][timeout:60];
        (node["amenity"="doctors"](around:{rad},{lat},{lon});
         way["amenity"="doctors"](around:{rad},{lat},{lon});
         node["amenity"="clinic"](around:{rad},{lat},{lon});
         way["amenity"="clinic"](around:{rad},{lat},{lon});
         node["healthcare"="doctor"](around:{rad},{lat},{lon});
         node["healthcare"="centre"](around:{rad},{lat},{lon});
         way["healthcare"="centre"](around:{rad},{lat},{lon}););
        out count;
    """),
    ("krankenhaeuser_anzahl", """
        [out:json][timeout:60];
        (node["amenity"="hospital"](around:{rad},{lat},{lon});
         way["amenity"="hospital"](around:{rad},{lat},{lon});
         relation["amenity"="hospital"](around:{rad},{lat},{lon});
         node["healthcare"="hospital"](around:{rad},{lat},{lon});
         way["healthcare"="hospital"](around:{rad},{lat},{lon}););
        out count;
    """),
    ("apotheken_anzahl", """
        [out:json][timeout:60];
        (node["amenity"="pharmacy"](around:{rad},{lat},{lon});
         way["amenity"="pharmacy"](around:{rad},{lat},{lon});
         node["healthcare"="pharmacy"](around:{rad},{lat},{lon});
         way["healthcare"="pharmacy"](around:{rad},{lat},{lon}););
        out count;
    """),
]

_FREIZEIT_FELDER: KategorieConfig = [
    ("parks_anzahl", """
        [out:json][timeout:60];
        (node["leisure"="park"](around:{rad},{lat},{lon});
         way["leisure"="park"](around:{rad},{lat},{lon});
         relation["leisure"="park"](around:{rad},{lat},{lon});
         way["leisure"="nature_reserve"](around:{rad},{lat},{lon});
         relation["leisure"="nature_reserve"](around:{rad},{lat},{lon});
         way["landuse"="recreation_ground"](around:{rad},{lat},{lon}););
        out count;
    """),
    ("kultur_anzahl", """
        [out:json][timeout:60];
        (node["amenity"="theatre"](around:{rad},{lat},{lon});
         way["amenity"="theatre"](around:{rad},{lat},{lon});
         node["amenity"="cinema"](around:{rad},{lat},{lon});
         way["amenity"="cinema"](around:{rad},{lat},{lon});
         node["tourism"="museum"](around:{rad},{lat},{lon});
         way["tourism"="museum"](around:{rad},{lat},{lon});
         relation["tourism"="museum"](around:{rad},{lat},{lon});
         node["amenity"="arts_centre"](around:{rad},{lat},{lon});
         way["amenity"="arts_centre"](around:{rad},{lat},{lon});
         node["tourism"="gallery"](around:{rad},{lat},{lon});
         way["tourism"="gallery"](around:{rad},{lat},{lon}););
        out count;
    """),
    ("sport_anzahl", """
        [out:json][timeout:60];
        (node["leisure"="sports_centre"](around:{rad},{lat},{lon});
         way["leisure"="sports_centre"](around:{rad},{lat},{lon});
         node["leisure"="swimming_pool"](around:{rad},{lat},{lon});
         way["leisure"="swimming_pool"](around:{rad},{lat},{lon});
         way["leisure"="pitch"](around:{rad},{lat},{lon});
         way["leisure"="stadium"](around:{rad},{lat},{lon});
         node["leisure"="fitness_centre"](around:{rad},{lat},{lon});
         way["leisure"="fitness_centre"](around:{rad},{lat},{lon}););
        out count;
    """),
]


# ---------------------------------------------------------------------------
# Öffentliche Extract-Funktionen
# ---------------------------------------------------------------------------

def extract_wetter(stadt: dict) -> dict | None:
    """
    Ruft Jahresdurchschnittswerte für das Vorjahr von der Open-Meteo
    Archive-API ab. Sonnenstunden, Temperatur und Niederschlag.
    """
    jahr = config.AKTUELLES_JAHR - 1
    url  = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude":   stadt["lat"],
        "longitude":  stadt["lon"],
        "start_date": f"{jahr}-01-01",
        "end_date":   f"{jahr}-12-31",
        "daily":      "sunshine_duration,precipitation_sum,temperature_2m_mean",
        "timezone":   "Europe/Berlin",
    }
    try:
        import pandas as pd
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        df   = pd.DataFrame(resp.json()["daily"])
        data = {
            "sonnenstunden_jahr":      round(df["sunshine_duration"].sum() / 3600, 1),
            "durchschnittstemperatur": round(df["temperature_2m_mean"].mean(), 2),
            "niederschlag_avg":        round(df["precipitation_sum"].mean(), 2),
        }
        print(f"  [Wetter] {stadt['name']}: {data['sonnenstunden_jahr']:.0f} h, "
              f"{data['durchschnittstemperatur']:.1f} °C")
        return data
    except Exception as exc:
        print(f"  [Wetter] FEHLER {stadt['name']}: {exc}")
        return None


def extract_wetter_parallel(staedte: list[dict]) -> dict[str, dict | None]:
    """Ruft Wetterdaten für mehrere Städte gleichzeitig ab (max. 5 Threads)."""
    ergebnisse: dict[str, dict | None] = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(extract_wetter, s): s["name"] for s in staedte}
        for future in as_completed(futures):
            name = futures[future]
            try:
                ergebnisse[name] = future.result()
            except Exception as exc:
                print(f"  [Wetter] FEHLER {name}: {exc}")
                ergebnisse[name] = None
    return ergebnisse


def extract_infrastruktur(stadt: dict) -> dict | None:
    """Haltestellen (ÖPNV) und POI-Dichte via Overpass."""
    lat = stadt["lat"]
    lon = stadt["lon"]
    rad = stadt["radius_km"] * 1000

    haltestellen = _overpass_count(f"""
        [out:json][timeout:60];
        (node["public_transport"="stop_position"](around:{rad},{lat},{lon});
         node["highway"="bus_stop"](around:{rad},{lat},{lon});
         node["railway"="station"](around:{rad},{lat},{lon});
         node["railway"="halt"](around:{rad},{lat},{lon}););
        out count;
    """)
    time.sleep(5)
    pois = _overpass_count(f"""
        [out:json][timeout:60];
        (node["amenity"](around:{rad},{lat},{lon});
         node["shop"](around:{rad},{lat},{lon});
         node["leisure"="park"](around:{rad},{lat},{lon}););
        out count;
    """)

    if haltestellen is None or pois is None:
        return None

    poi_dichte = round(int(pois) / (math.pi * stadt["radius_km"] ** 2), 2)
    print(f"  [Infra] {stadt['name']}: {haltestellen} Haltestellen, {poi_dichte} POIs/km²")
    return {"haltestellen_anzahl": int(haltestellen), "poi_dichte": poi_dichte}


def extract_bildung(stadt: dict) -> dict | None:
    """Schulen, Kitas und Universitäten via Overpass. Normiert auf Dichte + Pro-Kopf."""
    data = _extract_overpass_kategorie(stadt, _BILDUNG_FELDER, "bildungs")
    print(f"  [Bildung] {stadt['name']}: {data['schulen_anzahl']} Schulen, "
          f"{data['kitas_anzahl']} Kitas, {data['unis_anzahl']} Unis")
    return data


def extract_gesundheit(stadt: dict) -> dict | None:
    """Ärzte, Krankenhäuser und Apotheken via Overpass. Normiert auf Dichte + Pro-Kopf."""
    data = _extract_overpass_kategorie(stadt, _GESUNDHEIT_FELDER, "gesundheits")
    print(f"  [Gesundheit] {stadt['name']}: {data['aerzte_anzahl']} Ärzte, "
          f"{data['krankenhaeuser_anzahl']} KH, {data['apotheken_anzahl']} Apotheken")
    return data


def extract_freizeit(stadt: dict) -> dict | None:
    """Parks, Kultureinrichtungen und Sportstätten via Overpass. Normiert auf Dichte + Pro-Kopf."""
    data = _extract_overpass_kategorie(stadt, _FREIZEIT_FELDER, "freizeit")
    print(f"  [Freizeit] {stadt['name']}: {data['parks_anzahl']} Parks, "
          f"{data['kultur_anzahl']} Kultur, {data['sport_anzahl']} Sport")
    return data


def extract_miete(stadt: dict) -> dict | None:
    """Statische Mietpreisdaten aus config.MIETPREISE."""
    return config.MIETPREISE.get(stadt["name"])


def extract_sicherheit(stadt: dict) -> dict | None:
    """Statische Kriminalitätsdaten (BKA PKS 2023) aus config.KRIMINALITAET."""
    daten = config.KRIMINALITAET.get(stadt["name"])
    if daten:
        print(f"  [Sicherheit] {stadt['name']}: {daten['straftaten_je_100k']} Straft./100k")
    return daten


def extract_arbeitsmarkt(stadt: dict) -> dict | None:
    """
    Versucht die Arbeitslosenquote live von der BA-Statistik-API zu laden.
    Schlägt das fehl, wird auf statische Daten aus config.ARBEITSMARKT zurückgegriffen.
    """
    name = stadt["name"]
    ags  = stadt.get("ags")

    if ags:
        # Versuch 1: BA Statistik-API (inoffiziell, aber stabil)
        try:
            resp = requests.get(
                "https://statistik.arbeitsagentur.de/api/Veroeff/SuGroupCodes",
                params={"region": ags, "zr": "Monat", "leistung": "Alo", "dat": "Eckwerte"},
                headers={"User-Agent": "UrbanScore-ETL/1.0"},
                timeout=20,
            )
            resp.raise_for_status()
            for eintrag in resp.json().get("eintraege", []):
                if "arbeitslosenquote" in str(eintrag.get("bezeichnung", "")).lower():
                    wert = eintrag.get("wert")
                    if wert is not None:
                        quote = round(float(str(wert).replace(",", ".")), 1)
                        print(f"  [Arbeitsmarkt] {name}: {quote} % (BA-API)")
                        return {"arbeitslosenquote": quote, "offene_stellen": None}
        except Exception as exc:
            print(f"  [Arbeitsmarkt] {name}: BA-API fehlgeschlagen ({exc})")

        # Versuch 2: BA-CSV-Fallback
        try:
            jahr     = config.AKTUELLES_JAHR - 1
            csv_resp = requests.get(
                f"https://statistik.arbeitsagentur.de/SiteGlobals/Forms/Rubrikensuche/"
                f"Rubrikensuche_Form.html?region={ags}&year={jahr}&admtype=gem",
                headers={"User-Agent": "UrbanScore-ETL/1.0"},
                timeout=20,
            )
            csv_resp.raise_for_status()
            treffer = re.findall(r"(\d+[,.]\d+)\s*%", csv_resp.text)
            if treffer:
                quote = round(float(treffer[0].replace(",", ".")), 1)
                print(f"  [Arbeitsmarkt] {name}: {quote} % (BA-CSV)")
                return {"arbeitslosenquote": quote, "offene_stellen": None}
        except Exception:
            pass

    # Letzter Fallback: statische Daten
    fallback = config.ARBEITSMARKT.get(name)
    if fallback:
        print(f"  [Arbeitsmarkt] {name}: {fallback['arbeitslosenquote']} % (statisch)")
    return fallback
