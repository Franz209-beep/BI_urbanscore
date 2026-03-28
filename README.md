# UrbanScore Deutschland

Multidimensionales Städteranking für die 20 größten deutschen Städte.
Bewertet werden 8 Dimensionen: Klima, Wohnen, Wirtschaft, Infrastruktur, Bildung, Gesundheit, Freizeit und Sicherheit.

## Projektstruktur

```
BI_urbanscore/
├── config.py                      # Zentrale Konfiguration (Städte, Gewichte, Farben, Personas)
│
├── etl/
│   ├── pipeline.py                # Einstiegspunkt der ETL-Pipeline (python -m etl.pipeline)
│   ├── extractors.py              # Datenbeschaffung: Open-Meteo, Overpass, statische Daten
│   ├── loaders.py                 # DB-Inserts (UPSERT) pro Dimension
│   ├── transform.py               # Score-Berechnung und Ranking
│   └── db.py                      # Verbindung, Cache-Check, Zeitraum-Verwaltung
│
├── dashboard/
│   ├── app.py                     # Streamlit-Einstiegspunkt
│   ├── data.py                    # Datenladen und DataFrame-Aufbereitung
│   ├── components.py              # Wiederverwendbare UI-Bausteine
│   └── charts.py                  # Radar, Korrelation, Karte, Zeitreihe
│
├── requirements.txt
└── .github/workflows/daily_etl.yml
```

## Datenquellen

| Dimension     | Quelle                        | Update     |
|---------------|-------------------------------|------------|
| Klima         | Open-Meteo Archive API        | täglich    |
| Wohnen        | Statisch (Mietspiegel 2023)   | jährlich   |
| Wirtschaft    | BA Statistik-API / statisch   | täglich    |
| Infrastruktur | OpenStreetMap (Overpass)      | montags    |
| Bildung       | OpenStreetMap (Overpass)      | montags    |
| Gesundheit    | OpenStreetMap (Overpass)      | montags    |
| Freizeit      | OpenStreetMap (Overpass)      | montags    |
| Sicherheit    | Statisch (BKA PKS 2023)       | jährlich   |

## Quickstart (lokal)

```bash
pip install -r requirements.txt
streamlit run dashboard/app.py
```

## ETL manuell ausführen

```bash
python -m etl.pipeline
```

## GitHub Actions

Die Pipeline läuft täglich um 02:00 UTC automatisch und pusht die aktualisierte
`urbanscore.db` zurück ins Repository. Overpass-Abfragen (OSM) laufen nur montags,
um das Rate-Limit der API zu schonen.
