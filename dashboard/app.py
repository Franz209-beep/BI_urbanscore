"""
dashboard/app.py — Einstiegspunkt des Streamlit-Dashboards
===========================================================
Starten mit:  streamlit run dashboard/app.py

Diese Datei orchestriert nur den UI-Aufbau. Die eigentliche Logik
ist in data.py (Datenladen), components.py (UI-Bausteine) und
charts.py (Visualisierungen) gekapselt.
"""

import datetime
import os
import sys

# Stellt sicher, dass das Projekt-Root (wo config.py liegt) im Python-Pfad ist.
# Nötig wenn app.py aus einem Unterordner heraus gestartet wird (z.B. Streamlit Cloud).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import streamlit as st

import config
from dashboard.data import (
    lade_alle_tabellen,
    filter_zeitraum,
    baue_hauptdataframe,
    berechne_personscore,
)
from dashboard.components import (
    render_styles,
    render_header,
    render_section,
    render_gewichtsbalken,
    render_top3,
    render_ranking_zeile,
    render_ranking_legende,
    render_detail_header,
    render_detail_dimension,
    render_api_status,
    render_footer,
    DETAIL_DIMENSIONEN,
)
from dashboard.charts import render_korrelation, render_radar, render_karte, render_zeitreihe

# ---------------------------------------------------------------------------
# Seitenconfig & CSS
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="UrbanScore Deutschland",
    page_icon="🏙️",
    layout="wide",
)
render_styles()

# ---------------------------------------------------------------------------
# Daten laden
# ---------------------------------------------------------------------------

tabellen = lade_alle_tabellen()
if not tabellen:
    st.stop()

staedte = tabellen["staedte"]
zeit    = tabellen["zeit"]

if staedte is None or staedte.empty or zeit is None or zeit.empty:
    st.warning("Keine Daten in der Datenbank.")
    st.stop()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

letzter_lauf = "—"
try:
    ts           = os.path.getmtime("urbanscore.db")
    letzter_lauf = datetime.datetime.fromtimestamp(ts).strftime("%d.%m.%Y")
except Exception:
    pass

render_header(letzter_lauf)

# ---------------------------------------------------------------------------
# Zeitraum-Auswahl
# ---------------------------------------------------------------------------

col_z, _ = st.columns([2, 5])
with col_z:
    zeitraum = st.selectbox(
        "Zeitraum", zeit["zeitraum_label"].tolist(), label_visibility="collapsed"
    )
zeit_id = int(zeit[zeit["zeitraum_label"] == zeitraum]["zeit_id"].values[0])

gefiltert = filter_zeitraum(tabellen, zeit_id)
df        = baue_hauptdataframe(staedte, gefiltert)

# Welche Datenquellen sind verfügbar?
hat = {
    "Open-Meteo":    not gefiltert["wetter"].empty,
    "Mietspiegel":   not gefiltert["miete"].empty,
    "Arbeitsagentur":not gefiltert["arbeit"].empty,
    "OSM Infra":     not gefiltert["infra"].empty,
    "OSM Bildung":   not gefiltert["bildung"].empty,
    "OSM Gesundheit":not gefiltert["gesundheit"].empty,
    "OSM Freizeit":  not gefiltert["freizeit"].empty,
    "BKA PKS":       not gefiltert["sicherheit"].empty,
}

# ---------------------------------------------------------------------------
# Profil / Persona
# ---------------------------------------------------------------------------

render_section("Profil")

if "aktive_persona" not in st.session_state:
    st.session_state.aktive_persona = "Familie"

pcols = st.columns(len(config.PERSONAS))
for col, name in zip(pcols, config.PERSONAS.keys()):
    with col:
        aktiv = st.session_state.aktive_persona == name
        if st.button(name, key=f"pb_{name}", use_container_width=True,
                     type="primary" if aktiv else "secondary"):
            st.session_state.aktive_persona = name
            st.rerun()

aktive_persona   = st.session_state.aktive_persona
persona_data     = config.PERSONAS[aktive_persona]
st.caption(persona_data["beschreibung"])

# Gewichte bestimmen (Individuell: Slider, sonst: aus config)
if aktive_persona == "Individuell":
    st.markdown("<div style='margin-top:0.8rem'></div>", unsafe_allow_html=True)
    sl_cols = st.columns(4)
    raw = {}
    for idx, dim_name in enumerate(config.SCORE_MAP.keys()):
        with sl_cols[idx % 4]:
            raw[dim_name] = st.slider(dim_name, 0, 40, 10, key=f"sl_{dim_name}")
    gesamt_raw  = sum(raw.values()) or 1
    gewichte    = {k: round(v / gesamt_raw * 100, 1) for k, v in raw.items()}
    st.caption(f"Summe: {sum(gewichte.values()):.0f} % (automatisch normiert)")
else:
    gewichte = {k: float(v) for k, v in persona_data["gewichte"].items()}

render_gewichtsbalken(gewichte)

# Personalisierter Score
df["personscore"]  = berechne_personscore(df, gewichte)
df_sorted          = df.sort_values("personscore", ascending=False, na_position="last").reset_index(drop=True)
df_sorted["person_rang"] = range(1, len(df_sorted) + 1)

# ---------------------------------------------------------------------------
# Top 3
# ---------------------------------------------------------------------------

render_section(f"Top 3 — {aktive_persona}")
render_top3(df_sorted)

# ---------------------------------------------------------------------------
# Gesamtranking
# ---------------------------------------------------------------------------

render_section("Gesamtranking")
col_l, col_r = st.columns(2)
for col, teil in [(col_l, df_sorted.iloc[:10]), (col_r, df_sorted.iloc[10:])]:
    with col:
        for _, row in teil.iterrows():
            render_ranking_zeile(row)
render_ranking_legende()

# ---------------------------------------------------------------------------
# Detailansicht
# ---------------------------------------------------------------------------

render_section("Detailansicht")
stadt_auswahl = st.selectbox(
    "Stadt wählen", df_sorted["name"].tolist(), label_visibility="collapsed"
)
row = df_sorted[df_sorted["name"] == stadt_auswahl].iloc[0]

render_detail_header(row, aktive_persona, len(staedte))

# Spalten-Header
st.markdown("""
<div style="display:grid;grid-template-columns:110px 1fr 220px 55px;gap:14px;
            padding:5px 0;font-size:0.6rem;font-weight:600;text-transform:uppercase;
            letter-spacing:0.1em;color:#a0aec0;border-bottom:1px solid #edf2f7;margin-bottom:2px">
  <div>Dimension</div><div>Score (0–100)</div><div>Rohdaten</div>
  <div style="text-align:right">Wert</div>
</div>
""", unsafe_allow_html=True)

for dim in DETAIL_DIMENSIONEN:
    render_detail_dimension(row, dim, gewichte.get(dim["key"], 0))

# ---------------------------------------------------------------------------
# Korrelationsanalyse
# ---------------------------------------------------------------------------

render_section("Korrelationsanalyse")
render_korrelation(df)

# ---------------------------------------------------------------------------
# Städtevergleich – Radar
# ---------------------------------------------------------------------------

render_section("Städtevergleich — Radar")
render_radar(df_sorted)

# ---------------------------------------------------------------------------
# Karte
# ---------------------------------------------------------------------------

render_section("Karte")
render_karte(df_sorted)

# ---------------------------------------------------------------------------
# Zeitreihe (nur wenn mehrere Jahre in der DB)
# ---------------------------------------------------------------------------

if not tabellen["ranking"].empty and not zeit.empty:
    render_section("Entwicklung über Zeit")
    render_zeitreihe(tabellen["ranking"], staedte, zeit)

# ---------------------------------------------------------------------------
# API-Status & Footer
# ---------------------------------------------------------------------------

st.markdown("<div style='margin-top:2rem'></div>", unsafe_allow_html=True)
render_api_status(hat)
render_footer()
