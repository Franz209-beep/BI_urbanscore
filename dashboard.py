"""
UrbanScore Deutschland — Dashboard
===================================
Vollständiges Dashboard mit Ranking, Balkendiagramm,
Detailansicht, Zeitreihe und Karte.
"""

import sqlite3
import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(
    page_title="UrbanScore Deutschland",
    page_icon="🏙️",
    layout="wide",
)

# ---------------------------------------------------------------
# Styling
# ---------------------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'DM Serif Display', serif !important; }
.header-block {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
    border-radius: 16px; padding: 2.5rem 2.5rem 2rem; margin-bottom: 2rem; color: white;
}
.header-block h1 { font-size: 2.8rem; margin: 0 0 0.3rem 0; color: white !important; }
.header-block p  { color: #a0aec0; font-size: 1rem; margin: 0; font-weight: 300; }
.metric-card { background: white; border: 1px solid #e8ecf0; border-radius: 12px; padding: 1.2rem 1.5rem; text-align: center; }
.metric-label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: #718096; margin-bottom: 0.4rem; font-weight: 500; }
.metric-value { font-size: 2rem; font-weight: 500; color: #1a1a2e; font-family: 'DM Serif Display', serif; }
.metric-sub   { font-size: 0.8rem; color: #a0aec0; margin-top: 0.2rem; }
.ranking-table { background: white; border: 1px solid #e8ecf0; border-radius: 16px; overflow: hidden; }
.rank-row { display: flex; align-items: center; padding: 1rem 1.5rem; border-bottom: 1px solid #f7fafc; transition: background 0.15s; }
.rank-row:last-child { border-bottom: none; }
.rank-row:hover { background: #f7fafc; }
.rank-number { font-family: 'DM Serif Display', serif; font-size: 1.4rem; color: #cbd5e0; width: 40px; flex-shrink: 0; }
.rank-number.top1 { color: #f6ad55; }
.rank-number.top2 { color: #a0aec0; }
.rank-number.top3 { color: #c05621; }
.rank-city   { flex: 1; font-size: 1rem; font-weight: 500; color: #2d3748; }
.rank-state  { font-size: 0.8rem; color: #a0aec0; font-weight: 300; margin-left: 0.5rem; }
.rank-score  { font-size: 0.9rem; font-weight: 500; color: #4a5568; width: 60px; text-align: right; flex-shrink: 0; }
.score-bar-wrap { width: 120px; background: #edf2f7; border-radius: 999px; height: 6px; margin-left: 1rem; flex-shrink: 0; }
.score-bar-fill { height: 6px; border-radius: 999px; background: linear-gradient(90deg, #0f3460, #e94560); }
.detail-card { background: white; border: 1px solid #e8ecf0; border-radius: 16px; padding: 1.5rem; }
.detail-card h4 { font-family: 'DM Serif Display', serif; font-size: 1rem; color: #1a1a2e; margin: 0 0 1rem 0; padding-bottom: 0.75rem; border-bottom: 1px solid #e8ecf0; }
.detail-row { display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid #f7fafc; font-size: 0.88rem; }
.detail-row:last-child { border-bottom: none; }
.detail-key { color: #718096; }
.detail-val { font-weight: 500; color: #2d3748; }
.badge-available { display: inline-block; background: #c6f6d5; color: #276749; font-size: 0.7rem; padding: 2px 8px; border-radius: 999px; font-weight: 500; margin-left: 0.5rem; }
.badge-missing   { display: inline-block; background: #fed7d7; color: #9b2c2c; font-size: 0.7rem; padding: 2px 8px; border-radius: 999px; font-weight: 500; margin-left: 0.5rem; }
.info-box { background: #ebf8ff; border: 1px solid #bee3f8; border-radius: 10px; padding: 1rem 1.25rem; font-size: 0.88rem; color: #2c5282; margin-bottom: 1.5rem; }
.section-title { font-family: 'DM Serif Display', serif; font-size: 1.4rem; color: #1a1a2e; margin: 2rem 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #e8ecf0; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Datenbankverbindung
# ---------------------------------------------------------------

@st.cache_data(ttl=3600)
def lade_daten():
    try:
        conn = sqlite3.connect("urbanscore.db")
        staedte = pd.read_sql_query("SELECT * FROM stadt", conn)
        zeit    = pd.read_sql_query("SELECT * FROM zeit ORDER BY jahr DESC", conn)
        wetter  = pd.read_sql_query("SELECT * FROM wetterdaten", conn)
        miete   = pd.read_sql_query("SELECT * FROM mietdaten", conn)
        arbeit  = pd.read_sql_query("SELECT * FROM arbeitsmarktdaten", conn)
        infra   = pd.read_sql_query("SELECT * FROM infrastruktur", conn)
        ranking = pd.read_sql_query("SELECT * FROM ranking", conn)
        conn.close()
        return staedte, zeit, wetter, miete, arbeit, infra, ranking
    except Exception as e:
        st.error(f"Datenbankfehler: {e}")
        return None, None, None, None, None, None, None


staedte, zeit, wetter, miete, arbeit, infra, ranking = lade_daten()
if staedte is None:
    st.stop()

# ---------------------------------------------------------------
# Header
# ---------------------------------------------------------------

st.markdown("""
<div class="header-block">
    <h1>UrbanScore Deutschland</h1>
    <p>Multidimensionales Städteranking auf Basis von Klima, Wohnungsmarkt, Wirtschaft und Infrastruktur</p>
</div>
""", unsafe_allow_html=True)

if zeit.empty:
    st.warning("Keine Zeiträume in der Datenbank.")
    st.stop()

zeitraum_optionen   = zeit["zeitraum_label"].tolist()
gewaehlter_zeitraum = st.selectbox("Zeitraum", zeitraum_optionen)
gewaehlte_zeit_id   = int(zeit[zeit["zeitraum_label"] == gewaehlter_zeitraum]["zeit_id"].values[0])

# ---------------------------------------------------------------
# Daten zusammenführen
# ---------------------------------------------------------------

def fz(df):
    return df[df["zeit_id"] == gewaehlte_zeit_id] if not df.empty else pd.DataFrame()

wetter_z  = fz(wetter)
miete_z   = fz(miete)
arbeit_z  = fz(arbeit)
infra_z   = fz(infra)
ranking_z = fz(ranking)

df = staedte.copy()
for tab, suf in [(wetter_z,"w"),(miete_z,"m"),(arbeit_z,"a"),(infra_z,"i"),(ranking_z,"r")]:
    if not tab.empty:
        df = df.merge(tab, on="stadt_id", how="left", suffixes=("", f"_{suf}"))

hat_wetter  = not wetter_z.empty
hat_miete   = not miete_z.empty
hat_arbeit  = not arbeit_z.empty
hat_infra   = not infra_z.empty
hat_ranking = not ranking_z.empty
apis_aktiv  = sum([hat_wetter, hat_miete, hat_arbeit, hat_infra])

df_sorted = df.sort_values("rang") if hat_ranking and "rang" in df.columns else df.copy()
if "rang" not in df_sorted.columns:
    df_sorted["rang"] = range(1, len(df_sorted) + 1)

# ---------------------------------------------------------------
# Info-Box
# ---------------------------------------------------------------

if apis_aktiv < 4:
    fehlende = [n for n, ok in [
        ("Mietspiegel", hat_miete),
        ("Arbeitsagentur", hat_arbeit),
        ("Overpass/OSM", hat_infra),
    ] if not ok]
    if fehlende:
        st.markdown(f'<div class="info-box"><strong>Datenstatus:</strong> {apis_aktiv} von 4 APIs aktiv. Noch nicht verbunden: {", ".join(fehlende)}.</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------
# Kennzahlen
# ---------------------------------------------------------------

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Städte analysiert</div><div class="metric-value">{len(staedte)}</div><div class="metric-sub">deutsche Großstädte</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-card"><div class="metric-label">APIs aktiv</div><div class="metric-value">{apis_aktiv} / 4</div><div class="metric-sub">Datenquellen verbunden</div></div>', unsafe_allow_html=True)
with m3:
    best_sonne = df.loc[df["sonnenstunden_jahr"].idxmax(), "name"] if hat_wetter and "sonnenstunden_jahr" in df.columns and df["sonnenstunden_jahr"].notna().any() else "—"
    st.markdown(f'<div class="metric-card"><div class="metric-label">Meiste Sonnenstunden</div><div class="metric-value" style="font-size:1.4rem">{best_sonne}</div><div class="metric-sub">{gewaehlter_zeitraum}</div></div>', unsafe_allow_html=True)
with m4:
    top_vals = df.loc[df["rang"] == 1, "name"].values if hat_ranking and "rang" in df.columns else []
    top_name = top_vals[0] if len(top_vals) > 0 else "—"
    st.markdown(f'<div class="metric-card"><div class="metric-label">Aktueller Spitzenreiter</div><div class="metric-value" style="font-size:1.4rem">{top_name}</div><div class="metric-sub">höchster Gesamtscore</div></div>', unsafe_allow_html=True)

st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Ranking-Tabelle + API-Status
# ---------------------------------------------------------------

st.markdown('<div class="section-title">Städteranking</div>', unsafe_allow_html=True)
col_l, col_r = st.columns([3, 2])

with col_l:
    st.markdown('<div class="ranking-table"><div style="padding:1.2rem 1.5rem;border-bottom:1px solid #e8ecf0"><h3 style="margin:0;font-size:1.1rem;color:#1a1a2e">Gesamtranking</h3></div>', unsafe_allow_html=True)
    for _, row in df_sorted.iterrows():
        rang = int(row.get("rang", 0)) if pd.notna(row.get("rang")) else "—"
        rang_class = {1:"top1",2:"top2",3:"top3"}.get(rang,"")
        score = row.get("gesamtscore")
        score_pct  = int(float(score)*100) if pd.notna(score) else 0
        score_text = f"{score_pct}%" if pd.notna(score) else "—"
        st.markdown(f"""<div class="rank-row">
            <div class="rank-number {rang_class}">{rang}</div>
            <div class="rank-city">{row['name']}<span class="rank-state">{row['bundesland']}</span></div>
            <div class="score-bar-wrap"><div class="score-bar-fill" style="width:{score_pct}%"></div></div>
            <div class="rank-score">{score_text}</div>
        </div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_r:
    st.markdown('<div class="detail-card">', unsafe_allow_html=True)
    bw = '<span class="badge-available">aktiv</span>' if hat_wetter else '<span class="badge-missing">fehlt</span>'
    st.markdown(f'<h4>Klima {bw}</h4>', unsafe_allow_html=True)
    if hat_wetter and "sonnenstunden_jahr" in df.columns:
        for _, row in df_sorted.iterrows():
            sonne = f"{row['sonnenstunden_jahr']:.0f} h" if pd.notna(row.get("sonnenstunden_jahr")) else "—"
            temp  = f"{row['durchschnittstemperatur']:.1f} °C" if pd.notna(row.get("durchschnittstemperatur")) else "—"
            st.markdown(f'<div class="detail-row"><span class="detail-key">{row["name"]}</span><span class="detail-val">{sonne} · {temp}</span></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="detail-card"><h4>API-Status</h4>', unsafe_allow_html=True)
    for api_name, aktiv in [("Open-Meteo (Klima)",hat_wetter),("Mietspiegel (Wohnen)",hat_miete),("Arbeitsagentur (Wirtschaft)",hat_arbeit),("Overpass/OSM (Infrastruktur)",hat_infra)]:
        b = '<span class="badge-available">aktiv</span>' if aktiv else '<span class="badge-missing">ausstehend</span>'
        st.markdown(f'<div class="detail-row"><span class="detail-key">{api_name}</span>{b}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Balkendiagramm
# ---------------------------------------------------------------

st.markdown('<div class="section-title">Vergleich nach Kategorie</div>', unsafe_allow_html=True)

kategorien = {
    "Gesamtscore":      ("gesamtscore",        False),
    "Klima":            ("score_klima",         False),
    "Wohnen":           ("score_wohnen",        False),
    "Wirtschaft":       ("score_wirtschaft",    False),
    "Infrastruktur":    ("score_infrastruktur", False),
    "Sonnenstunden":    ("sonnenstunden_jahr",   False),
    "Mietpreis €/m²":  ("mietpreis_kalt_qm",   True),
    "Arbeitslosigkeit": ("arbeitslosenquote",    True),
}

kat_auswahl = st.selectbox("Kennzahl auswählen", list(kategorien.keys()))
col_name, invertiert = kategorien[kat_auswahl]

if col_name in df_sorted.columns and df_sorted[col_name].notna().any():
    df_bar = df_sorted[["name", col_name]].dropna().sort_values(col_name, ascending=invertiert)
    chart = alt.Chart(df_bar).mark_bar(
        cornerRadiusTopLeft=4, cornerRadiusTopRight=4
    ).encode(
        x=alt.X("name:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(f"{col_name}:Q", title=kat_auswahl),
        color=alt.Color(f"{col_name}:Q", scale=alt.Scale(scheme="blues"), legend=None),
        tooltip=["name:N", alt.Tooltip(f"{col_name}:Q", title=kat_auswahl, format=".2f")],
    ).properties(height=320).configure_axis(grid=False, labelFontSize=13).configure_view(strokeWidth=0)
    st.altair_chart(chart, use_container_width=True)
else:
    st.info(f"Keine Daten für '{kat_auswahl}' vorhanden.")

# ---------------------------------------------------------------
# Detailansicht pro Stadt
# ---------------------------------------------------------------

st.markdown('<div class="section-title">Detailansicht pro Stadt</div>', unsafe_allow_html=True)

stadt_auswahl = st.selectbox("Stadt auswählen", df_sorted["name"].tolist())
row = df_sorted[df_sorted["name"] == stadt_auswahl].iloc[0]

def detail_karte(col, titel, wert, einheit, farbe):
    with col:
        st.markdown(f"""<div style="background:white;border:1px solid #e8ecf0;border-radius:12px;
            padding:1.2rem;text-align:center;border-top:4px solid {farbe}">
            <div style="font-size:0.75rem;text-transform:uppercase;letter-spacing:1px;color:#718096;margin-bottom:0.4rem">{titel}</div>
            <div style="font-size:1.6rem;font-weight:500;color:#1a1a2e;font-family:'DM Serif Display',serif">{wert}</div>
            <div style="font-size:0.8rem;color:#a0aec0">{einheit}</div>
        </div>""", unsafe_allow_html=True)

sonne_v = f"{row['sonnenstunden_jahr']:.0f}"     if pd.notna(row.get("sonnenstunden_jahr"))     else "—"
temp_v  = f"{row['durchschnittstemperatur']:.1f}" if pd.notna(row.get("durchschnittstemperatur")) else "—"
miete_v = f"{row['mietpreis_kalt_qm']:.2f}"      if pd.notna(row.get("mietpreis_kalt_qm"))      else "—"
alq_v   = f"{row['arbeitslosenquote']:.1f}"       if pd.notna(row.get("arbeitslosenquote"))       else "—"
halte_v = f"{int(row['haltestellen_anzahl'])}"    if pd.notna(row.get("haltestellen_anzahl"))     else "—"
poi_v   = f"{row['poi_dichte']:.1f}"              if pd.notna(row.get("poi_dichte"))              else "—"
rang_v  = f"#{int(row['rang'])}"                  if pd.notna(row.get("rang"))                    else "—"
score_v = f"{int(float(row['gesamtscore'])*100)}%" if pd.notna(row.get("gesamtscore"))            else "—"

d1, d2, d3, d4 = st.columns(4)
detail_karte(d1, "Gesamtrang",    rang_v,  "von 5 Städten",         "#0f3460")
detail_karte(d2, "Gesamtscore",   score_v, "gewichteter Wert",      "#e94560")
detail_karte(d3, "Sonnenstunden", sonne_v, "h/Jahr",                "#f6ad55")
detail_karte(d4, "Temperatur",    temp_v,  "°C Jahresdurchschnitt", "#68d391")

st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
d5, d6, d7, d8 = st.columns(4)
detail_karte(d5, "Kaltmiete",        miete_v, "€/m²",           "#9f7aea")
detail_karte(d6, "Arbeitslosigkeit", alq_v,   "%",              "#fc8181")
detail_karte(d7, "Haltestellen",     halte_v, "im Stadtgebiet", "#4fd1c5")
detail_karte(d8, "POI-Dichte",       poi_v,   "POIs/km²",       "#63b3ed")

score_cols = ["score_klima","score_wohnen","score_wirtschaft","score_infrastruktur"]
if hat_ranking and all(c in row.index for c in score_cols):
    st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)
    scores_df = pd.DataFrame({
        "Kategorie": ["Klima","Wohnen","Wirtschaft","Infrastruktur"],
        "Score": [round(float(row[c])*100,1) if pd.notna(row.get(c)) else 0 for c in score_cols]
    })
    sc = alt.Chart(scores_df).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("Kategorie:N", sort=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Score:Q", scale=alt.Scale(domain=[0,100]), title="Score (0–100)"),
        color=alt.Color("Kategorie:N", scale=alt.Scale(
            domain=["Klima","Wohnen","Wirtschaft","Infrastruktur"],
            range=["#f6ad55","#9f7aea","#fc8181","#4fd1c5"]
        ), legend=None),
        tooltip=["Kategorie:N", alt.Tooltip("Score:Q", format=".1f")],
    ).properties(height=260, title=f"Teilscores — {stadt_auswahl}").configure_axis(grid=False).configure_view(strokeWidth=0)
    st.altair_chart(sc, use_container_width=True)

# ---------------------------------------------------------------
# Karte
# ---------------------------------------------------------------

st.markdown('<div class="section-title">Karte der analysierten Städte</div>', unsafe_allow_html=True)

karte_df = df_sorted[["name","latitude","longitude","gesamtscore","rang"]].copy()
karte_df = karte_df.rename(columns={"latitude":"lat","longitude":"lon"})
karte_df["gesamtscore"] = karte_df["gesamtscore"].fillna(0)
st.map(karte_df, latitude="lat", longitude="lon", size=50000, zoom=5)

# ---------------------------------------------------------------
# Zeitreihe
# ---------------------------------------------------------------

st.markdown('<div class="section-title">Entwicklung über Zeit</div>', unsafe_allow_html=True)

if not ranking.empty and not zeit.empty:
    zeitreihe = ranking.merge(staedte[["stadt_id","name"]], on="stadt_id")
    zeitreihe = zeitreihe.merge(zeit[["zeit_id","jahr"]], on="zeit_id")

    if len(zeitreihe["jahr"].unique()) > 1:
        metrik_auswahl = st.selectbox("Metrik", ["gesamtscore","score_klima","score_wohnen","score_wirtschaft","score_infrastruktur"],
            format_func=lambda x: {"gesamtscore":"Gesamtscore","score_klima":"Klima","score_wohnen":"Wohnen","score_wirtschaft":"Wirtschaft","score_infrastruktur":"Infrastruktur"}[x])
        linie = alt.Chart(zeitreihe).mark_line(point=True).encode(
            x=alt.X("jahr:O", title="Jahr"),
            y=alt.Y(f"{metrik_auswahl}:Q", scale=alt.Scale(domain=[0,1]), title="Score (0–1)"),
            color=alt.Color("name:N", title="Stadt"),
            tooltip=["name:N","jahr:O", alt.Tooltip(f"{metrik_auswahl}:Q", format=".3f")],
        ).properties(height=320).configure_axis(grid=False).configure_view(strokeWidth=0)
        st.altair_chart(linie, use_container_width=True)
    else:
        st.info("Für eine Zeitreihe werden mindestens zwei Jahre Daten benötigt. Die ETL-Pipeline sammelt täglich Daten — im nächsten Jahr wird diese Ansicht automatisch befüllt.")
else:
    st.info("Noch keine Ranking-Daten vorhanden.")

# ---------------------------------------------------------------
# Footer
# ---------------------------------------------------------------

st.markdown("<div style='margin-top:2rem'></div>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align:center;color:#a0aec0;font-size:0.78rem;padding:1rem 0'>
    UrbanScore Deutschland · Datenquellen: Open-Meteo, Mietspiegel, Bundesagentur für Arbeit, OpenStreetMap
</div>
""", unsafe_allow_html=True)
