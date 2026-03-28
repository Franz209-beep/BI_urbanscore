"""
config.py — Zentrale Konfiguration für UrbanScore Deutschland
=============================================================
Einzige Quelle der Wahrheit für alle Konstanten, Stammdaten und
statischen Datensätze. Wird von ETL-Pipeline und Dashboard gleichermaßen
importiert – Änderungen hier wirken sich überall aus.
"""

from datetime import date

# ---------------------------------------------------------------------------
# Laufzeit
# ---------------------------------------------------------------------------

# Aktuelles Jahr, wird als Zeitraum-Label in der DB verwendet
AKTUELLES_JAHR: int = date.today().year


# ---------------------------------------------------------------------------
# Städte-Stammdaten
# ---------------------------------------------------------------------------
# Jede Stadt enthält:
#   ags        – Amtlicher Gemeindeschlüssel (8-stellig), für BA-API
#   lat/lon    – Koordinaten für Wetter- und Overpass-Abfragen
#   radius_km  – Suchradius für Overpass (Stadtgröße berücksichtigt)
#   einwohner  – Für Pro-Kopf-Normierung in Bildung/Gesundheit/Freizeit

STAEDTE: list[dict] = [
    {"name": "Berlin",     "ags": "11000000", "lat": 52.5200, "lon": 13.4050, "radius_km": 20, "einwohner": 3_645_000},
    {"name": "Hamburg",    "ags": "02000000", "lat": 53.5753, "lon": 10.0153, "radius_km": 18, "einwohner": 1_853_000},
    {"name": "München",    "ags": "09162000", "lat": 48.1351, "lon": 11.5820, "radius_km": 15, "einwohner": 1_488_000},
    {"name": "Köln",       "ags": "05315000", "lat": 50.9333, "lon":  6.9500, "radius_km": 15, "einwohner": 1_084_000},
    {"name": "Frankfurt",  "ags": "06412000", "lat": 50.1109, "lon":  8.6821, "radius_km": 12, "einwohner":   759_000},
    {"name": "Düsseldorf", "ags": "05111000", "lat": 51.2217, "lon":  6.7762, "radius_km": 12, "einwohner":   619_000},
    {"name": "Stuttgart",  "ags": "08111000", "lat": 48.7758, "lon":  9.1829, "radius_km": 12, "einwohner":   626_000},
    {"name": "Leipzig",    "ags": "14713000", "lat": 51.3397, "lon": 12.3731, "radius_km": 12, "einwohner":   628_000},
    {"name": "Dortmund",   "ags": "05913000", "lat": 51.5136, "lon":  7.4653, "radius_km": 12, "einwohner":   588_000},
    {"name": "Bremen",     "ags": "04011000", "lat": 53.0793, "lon":  8.8017, "radius_km": 12, "einwohner":   563_000},
    {"name": "Essen",      "ags": "05113000", "lat": 51.4556, "lon":  7.0116, "radius_km": 10, "einwohner":   580_000},
    {"name": "Dresden",    "ags": "14612000", "lat": 51.0504, "lon": 13.7373, "radius_km": 12, "einwohner":   556_000},
    {"name": "Hannover",   "ags": "03241001", "lat": 52.3759, "lon":  9.7320, "radius_km": 12, "einwohner":   532_000},
    {"name": "Nürnberg",   "ags": "09564000", "lat": 49.4521, "lon": 11.0767, "radius_km": 12, "einwohner":   511_000},
    {"name": "Duisburg",   "ags": "05112000", "lat": 51.4344, "lon":  6.7623, "radius_km": 10, "einwohner":   495_000},
    {"name": "Bochum",     "ags": "05911000", "lat": 51.4818, "lon":  7.2162, "radius_km": 10, "einwohner":   365_000},
    {"name": "Wuppertal",  "ags": "05124000", "lat": 51.2562, "lon":  7.1508, "radius_km": 10, "einwohner":   355_000},
    {"name": "Bielefeld",  "ags": "05711000", "lat": 52.0302, "lon":  8.5325, "radius_km": 10, "einwohner":   333_000},
    {"name": "Bonn",       "ags": "05314000", "lat": 50.7374, "lon":  7.0982, "radius_km": 10, "einwohner":   329_000},
    {"name": "Münster",    "ags": "05515000", "lat": 51.9607, "lon":  7.6261, "radius_km": 10, "einwohner":   317_000},
]

# Schneller Name→Einwohner-Lookup für die Ranking-Berechnung
EINWOHNER: dict[str, int] = {s["name"]: s["einwohner"] for s in STAEDTE}


# ---------------------------------------------------------------------------
# Statische Rohdaten (jährlich manuell gepflegt)
# ---------------------------------------------------------------------------
# Quellen: Mietspiegel 2023/24, BKA PKS 2023, BA Arbeitsmarktreport 2023
# Diese Daten ändern sich selten – ein jährliches Update genügt.

MIETPREISE: dict[str, dict] = {
    "Berlin":     {"mietpreis_kalt_qm": 13.20, "anzahl_inserate": 0},
    "Hamburg":    {"mietpreis_kalt_qm": 14.80, "anzahl_inserate": 0},
    "München":    {"mietpreis_kalt_qm": 20.50, "anzahl_inserate": 0},
    "Köln":       {"mietpreis_kalt_qm": 13.00, "anzahl_inserate": 0},
    "Frankfurt":  {"mietpreis_kalt_qm": 15.30, "anzahl_inserate": 0},
    "Düsseldorf": {"mietpreis_kalt_qm": 13.50, "anzahl_inserate": 0},
    "Stuttgart":  {"mietpreis_kalt_qm": 15.80, "anzahl_inserate": 0},
    "Leipzig":    {"mietpreis_kalt_qm":  8.50, "anzahl_inserate": 0},
    "Dortmund":   {"mietpreis_kalt_qm":  9.20, "anzahl_inserate": 0},
    "Bremen":     {"mietpreis_kalt_qm":  9.80, "anzahl_inserate": 0},
    "Essen":      {"mietpreis_kalt_qm":  9.00, "anzahl_inserate": 0},
    "Dresden":    {"mietpreis_kalt_qm":  9.00, "anzahl_inserate": 0},
    "Hannover":   {"mietpreis_kalt_qm": 11.00, "anzahl_inserate": 0},
    "Nürnberg":   {"mietpreis_kalt_qm": 12.50, "anzahl_inserate": 0},
    "Duisburg":   {"mietpreis_kalt_qm":  8.20, "anzahl_inserate": 0},
    "Bochum":     {"mietpreis_kalt_qm":  9.10, "anzahl_inserate": 0},
    "Wuppertal":  {"mietpreis_kalt_qm":  8.00, "anzahl_inserate": 0},
    "Bielefeld":  {"mietpreis_kalt_qm":  9.30, "anzahl_inserate": 0},
    "Bonn":       {"mietpreis_kalt_qm": 12.80, "anzahl_inserate": 0},
    "Münster":    {"mietpreis_kalt_qm": 12.00, "anzahl_inserate": 0},
}

ARBEITSMARKT: dict[str, dict] = {
    "Berlin":     {"arbeitslosenquote":  9.4, "offene_stellen": None},
    "Hamburg":    {"arbeitslosenquote":  6.9, "offene_stellen": None},
    "München":    {"arbeitslosenquote":  3.8, "offene_stellen": None},
    "Köln":       {"arbeitslosenquote":  8.1, "offene_stellen": None},
    "Frankfurt":  {"arbeitslosenquote":  5.7, "offene_stellen": None},
    "Düsseldorf": {"arbeitslosenquote":  7.8, "offene_stellen": None},
    "Stuttgart":  {"arbeitslosenquote":  4.2, "offene_stellen": None},
    "Leipzig":    {"arbeitslosenquote":  7.5, "offene_stellen": None},
    "Dortmund":   {"arbeitslosenquote": 11.2, "offene_stellen": None},
    "Bremen":     {"arbeitslosenquote": 10.1, "offene_stellen": None},
    "Essen":      {"arbeitslosenquote": 11.8, "offene_stellen": None},
    "Dresden":    {"arbeitslosenquote":  6.8, "offene_stellen": None},
    "Hannover":   {"arbeitslosenquote":  8.3, "offene_stellen": None},
    "Nürnberg":   {"arbeitslosenquote":  5.9, "offene_stellen": None},
    "Duisburg":   {"arbeitslosenquote": 12.5, "offene_stellen": None},
    "Bochum":     {"arbeitslosenquote": 10.4, "offene_stellen": None},
    "Wuppertal":  {"arbeitslosenquote": 11.0, "offene_stellen": None},
    "Bielefeld":  {"arbeitslosenquote":  7.9, "offene_stellen": None},
    "Bonn":       {"arbeitslosenquote":  5.5, "offene_stellen": None},
    "Münster":    {"arbeitslosenquote":  5.1, "offene_stellen": None},
}

# Quelle: BKA Polizeiliche Kriminalstatistik (PKS) 2023
# Werte normiert auf 100.000 Einwohner für Städtevergleichbarkeit
KRIMINALITAET: dict[str, dict] = {
    "Berlin":     {"straftaten_je_100k": 15823, "gewaltdelikte_je_100k": 384},
    "Hamburg":    {"straftaten_je_100k": 14201, "gewaltdelikte_je_100k": 341},
    "München":    {"straftaten_je_100k":  9812, "gewaltdelikte_je_100k": 198},
    "Köln":       {"straftaten_je_100k": 13450, "gewaltdelikte_je_100k": 312},
    "Frankfurt":  {"straftaten_je_100k": 16234, "gewaltdelikte_je_100k": 398},
    "Düsseldorf": {"straftaten_je_100k": 12980, "gewaltdelikte_je_100k": 287},
    "Stuttgart":  {"straftaten_je_100k": 11203, "gewaltdelikte_je_100k": 245},
    "Leipzig":    {"straftaten_je_100k": 12801, "gewaltdelikte_je_100k": 298},
    "Dortmund":   {"straftaten_je_100k": 13920, "gewaltdelikte_je_100k": 356},
    "Bremen":     {"straftaten_je_100k": 13100, "gewaltdelikte_je_100k": 318},
    "Essen":      {"straftaten_je_100k": 12450, "gewaltdelikte_je_100k": 302},
    "Dresden":    {"straftaten_je_100k": 10980, "gewaltdelikte_je_100k": 231},
    "Hannover":   {"straftaten_je_100k": 13560, "gewaltdelikte_je_100k": 327},
    "Nürnberg":   {"straftaten_je_100k": 12100, "gewaltdelikte_je_100k": 276},
    "Duisburg":   {"straftaten_je_100k": 13780, "gewaltdelikte_je_100k": 348},
    "Bochum":     {"straftaten_je_100k": 11890, "gewaltdelikte_je_100k": 271},
    "Wuppertal":  {"straftaten_je_100k": 12340, "gewaltdelikte_je_100k": 289},
    "Bielefeld":  {"straftaten_je_100k": 11020, "gewaltdelikte_je_100k": 241},
    "Bonn":       {"straftaten_je_100k": 10450, "gewaltdelikte_je_100k": 219},
    "Münster":    {"straftaten_je_100k":  9230, "gewaltdelikte_je_100k": 187},
}


# ---------------------------------------------------------------------------
# Scoring & Dashboard-Konfiguration
# ---------------------------------------------------------------------------

# Mapping: Anzeigename → DB-Spaltenname im ranking-Table
SCORE_MAP: dict[str, str] = {
    "Klima":         "score_klima",
    "Wohnen":        "score_wohnen",
    "Wirtschaft":    "score_wirtschaft",
    "Infrastruktur": "score_infrastruktur",
    "Bildung":       "score_bildung",
    "Gesundheit":    "score_gesundheit",
    "Freizeit":      "score_freizeit",
    "Sicherheit":    "score_sicherheit",
}

# Gewichte für den Gesamt-Score in der ETL-Pipeline (müssen sich zu 1.0 summieren)
SCORE_GEWICHTE: dict[str, float] = {
    "score_klima":         0.10,
    "score_wohnen":        0.20,
    "score_wirtschaft":    0.20,
    "score_infrastruktur": 0.10,
    "score_bildung":       0.15,
    "score_gesundheit":    0.10,
    "score_freizeit":      0.05,
    "score_sicherheit":    0.10,
}

# Farben pro Dimension (konsistent in Ranking, Radar, Legende)
DIM_FARBEN: dict[str, str] = {
    "Klima":         "#4A9B84",
    "Wohnen":        "#3B7EC8",
    "Wirtschaft":    "#C8891F",
    "Infrastruktur": "#B84C2A",
    "Bildung":       "#7B52AB",
    "Gesundheit":    "#C0392B",
    "Freizeit":      "#27855A",
    "Sicherheit":    "#2C3E50",
}

# Bundesland-Kürzel für die Anzeige im Dashboard
BUNDESLAND_KUERZEL: dict[str, str] = {
    "Nordrhein-Westfalen":    "NW",
    "Bayern":                 "BY",
    "Baden-Württemberg":      "BW",
    "Sachsen":                "SN",
    "Berlin":                 "BE",
    "Hamburg":                "HH",
    "Bremen":                 "HB",
    "Hessen":                 "HE",
    "Niedersachsen":          "NI",
    "Brandenburg":            "BB",
    "Thüringen":              "TH",
    "Sachsen-Anhalt":         "ST",
    "Rheinland-Pfalz":        "RP",
    "Saarland":               "SL",
    "Schleswig-Holstein":     "SH",
    "Mecklenburg-Vorpommern": "MV",
}

# Persona-Profile für den personalisierten Score im Dashboard.
# Gewichte müssen sich auf 100 summieren. Sicherheit ist überall > 0,
# da sie ein Grundbedürfnis darstellt.
PERSONAS: dict[str, dict] = {
    "Familie": {
        "beschreibung": "Fokus auf Bildung, Wohnen und Sicherheit",
        "gewichte": {
            "Klima": 8, "Wohnen": 22, "Wirtschaft": 13, "Infrastruktur": 10,
            "Bildung": 22, "Gesundheit": 10, "Freizeit": 5, "Sicherheit": 10,
        },
    },
    "Freelancer": {
        "beschreibung": "Infrastruktur, Wirtschaft und Freizeit im Vordergrund",
        "gewichte": {
            "Klima": 12, "Wohnen": 18, "Wirtschaft": 18, "Infrastruktur": 20,
            "Bildung": 5, "Gesundheit": 7, "Freizeit": 12, "Sicherheit": 8,
        },
    },
    "Rentner": {
        "beschreibung": "Klima, Gesundheit und ruhiges Wohnen",
        "gewichte": {
            "Klima": 18, "Wohnen": 22, "Wirtschaft": 5, "Infrastruktur": 12,
            "Bildung": 3, "Gesundheit": 22, "Freizeit": 8, "Sicherheit": 10,
        },
    },
    "Student": {
        "beschreibung": "Günstiges Wohnen, Bildung und ÖPNV",
        "gewichte": {
            "Klima": 8, "Wohnen": 28, "Wirtschaft": 10, "Infrastruktur": 18,
            "Bildung": 20, "Gesundheit": 5, "Freizeit": 5, "Sicherheit": 6,
        },
    },
    "Individuell": {
        "beschreibung": "Eigene Gewichtung — Summe wird automatisch auf 100 % normiert",
        "gewichte": None,  # wird im Dashboard per Slider befüllt
    },
}
