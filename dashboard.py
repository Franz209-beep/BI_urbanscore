"""
UrbanScore Deutschland — Dashboard (Redesign)
===============================================
Übersichtliches Layout mit Siegerpodest, Ranking-Tabelle
mit farbigen Teilscores, Detailansicht und Vergleichsdiagramm.
"""

import sqlite3
import os
import datetime
import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(
    page_title="UrbanScore Deutschland",
    page_icon="🏙️",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.header {
    background: #0f1923;
    border-radius: 16px;
    padding: 2rem 2.5rem 1.8rem;
    margin-bottom: 1.5rem;
    overflow: hidden;
    position: relative;
}
.header h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 2.4rem;
    color: white;
    margin: 0 0 0.3rem 0;
    position: relative;
    z-index: 2;
}
.header p { color: #7a9ab5; font-size: 0.95rem; margin: 0; font-weight: 300; position: relative; z-index: 2; }
.skyline { position: absolute; bottom: 0; right: 0; opacity: 0.12; z-index: 1; }

.stat { background: #f7f8fa; border-radius: 10px; padding: 1rem 1.2rem; text-align: center; }
.stat-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1.2px; color: #8a9ab0; margin-bottom: 5px; }
.stat-value { font-family: 'DM Serif Display', serif; font-size: 1.6rem; color: #0f1923; }

.podest-wrap { display: flex; align-items: flex-end; gap: 12px; margin: 1.5rem 0; }
.podest-card { flex: 1; background: white; border: 0.5px solid #e2e8f0; border-radius: 14px; padding: 1.2rem; text-align: center; }
.podest-card.gold { border: 2px solid #f6ad55; }
.podest-city { font-size: 1rem; font-weight: 500; color: #0f1923; }
.podest-city.gold { font-size: 1.2rem; }
.podest-state { font-size: 0.75rem; color: #9aabba; margin-top: 2px; }
.podest-score { font-size: 0.85rem; color: #5a7a96; margin-top: 6px; }

.section-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1.5px; color: #9aabba; margin: 1.5rem 0 0.8rem 0; }

.detail-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 12px; }
.detail-kachel { background: #f7f8fa; border-radius: 10px; padding: 12px 14px; text-align: center; border-top: 3px solid transparent; }
.detail-kachel-label { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 1px; color: #9aabba; margin-bottom: 6px; }
.detail-kachel-val { font-family: 'DM Serif Display', serif; font-size: 1.5rem; color: #0f1923; }
.detail-kachel-unit { font-size: 0.72rem; color: #b0bec8; margin-top: 2px; }

.info-pill { display: inline-block; font-size: 0.7rem; padding: 3px 10px; border-radius: 999px; margin-bottom: 1rem; background: #ebf8ff; color: #2c5282; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Daten laden
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
        return [None] * 7

staedte, zeit, wetter, miete, arbeit, infra, ranking = lade_daten()
if staedte is None:
    st.stop()

# ---------------------------------------------------------------
# Header mit Stadtsilhouette und letztem Update-Datum
# ---------------------------------------------------------------

letzter_lauf = "—"
try:
    ts = os.path.getmtime("urbanscore.db")
    letzter_lauf = datetime.datetime.fromtimestamp(ts).strftime("%d.%m.%Y")
except:
    pass

st.markdown(f"""
<div class="header">
  <svg class="skyline" width="420" height="120" viewBox="0 0 420 120" xmlns="http://www.w3.org/2000/svg">
    <rect x="10"  y="60" width="18" height="60" fill="white"/>
    <rect x="14"  y="50" width="10" height="12" fill="white"/>
    <rect x="16"  y="40" width="6"  height="12" fill="white"/>
    <rect x="35"  y="40" width="22" height="80" fill="white"/>
    <rect x="41"  y="30" width="10" height="12" fill="white"/>
    <rect x="63"  y="70" width="14" height="50" fill="white"/>
    <rect x="83"  y="30" width="26" height="90" fill="white"/>
    <rect x="87"  y="20" width="8"  height="12" fill="white"/>
    <rect x="91"  y="10" width="2"  height="12" fill="white"/>
    <rect x="115" y="55" width="20" height="65" fill="white"/>
    <rect x="121" y="45" width="8"  height="12" fill="white"/>
    <rect x="141" y="45" width="30" height="75" fill="white"/>
    <rect x="148" y="35" width="16" height="12" fill="white"/>
    <rect x="153" y="25" width="6"  height="12" fill="white"/>
    <rect x="177" y="65" width="16" height="55" fill="white"/>
    <rect x="199" y="35" width="24" height="85" fill="white"/>
    <rect x="205" y="25" width="12" height="12" fill="white"/>
    <rect x="229" y="50" width="18" height="70" fill="white"/>
    <rect x="253" y="40" width="28" height="80" fill="white"/>
    <rect x="259" y="28" width="16" height="14" fill="white"/>
    <rect x="264" y="18" width="6"  height="12" fill="white"/>
    <rect x="287" y="60" width="16" height="60" fill="white"/>
    <rect x="309" y="38" width="22" height="82" fill="white"/>
    <rect x="314" y="26" width="12" height="14" fill="white"/>
    <rect x="337" y="55" width="18" height="65" fill="white"/>
    <rect x="361" y="42" width="26" height="78" fill="white"/>
    <rect x="367" y="30" width="14" height="14" fill="white"/>
    <rect x="393" y="62" width="20" height="58" fill="white"/>
    <rect x="0"   y="118" width="420" height="4" fill="white"/>
  </svg>
  <h1>UrbanScore Deutschland</h1>
  <p>Multidimensionales Städteranking · Klima, Wohnen, Wirtschaft, Infrastruktur · Letzte Aktualisierung: {letzter_lauf}</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Zeitraum
# ---------------------------------------------------------------

if zeit.empty:
    st.warning("Keine Zeiträume vorhanden.")
    st.stop()

col_z, _ = st.columns([2, 5])
with col_z:
    zeitraum = st.selectbox("Zeitraum", zeit["zeitraum_label"].tolist(), label_visibility="collapsed")
zeit_id = int(zeit[zeit["zeitraum_label"] == zeitraum]["zeit_id"].values[0])

def fz(df):
    return df[df["zeit_id"] == zeit_id] if not df.empty else pd.DataFrame()

wetter_z  = fz(wetter)
miete_z   = fz(miete)
arbeit_z  = fz(arbeit)
infra_z   = fz(infra)
ranking_z = fz(ranking)

df = staedte.copy()
for tab, suf in [(wetter_z,"w"),(miete_z,"m"),(arbeit_z,"a"),(infra_z,"i"),(ranking_z,"r")]:
    if not tab.empty:
        df = df.merge(tab, on="stadt_id", how="left", suffixes=("", f"_{suf}"))

hat_ranking = not ranking_z.empty
hat_wetter  = not wetter_z.empty
hat_miete   = not miete_z.empty
hat_arbeit  = not arbeit_z.empty
hat_infra   = not infra_z.empty
apis_aktiv  = sum([hat_wetter, hat_miete, hat_arbeit, hat_infra])

if hat_ranking and "rang" in df.columns:
    df_sorted = df.sort_values("rang")
else:
    df_sorted = df.copy()
    df_sorted["rang"] = range(1, len(df_sorted) + 1)

# ---------------------------------------------------------------
# Info-Pill
# ---------------------------------------------------------------

if apis_aktiv < 4:
    fehlende = [n for n, ok in [("Miete", hat_miete), ("Arbeitsmarkt", hat_arbeit), ("Infrastruktur", hat_infra)] if not ok]
    st.markdown(f'<div class="info-pill">{apis_aktiv}/4 APIs aktiv · fehlend: {", ".join(fehlende)}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------
# Kennzahlen
# ---------------------------------------------------------------

top_name = df_sorted.iloc[0]["name"] if len(df_sorted) > 0 else "—"
s1, s2, s3, s4 = st.columns(4)

def stat_card(col, label, value):
    with col:
        st.markdown(f'<div class="stat"><div class="stat-label">{label}</div><div class="stat-value">{value}</div></div>', unsafe_allow_html=True)

stat_card(s1, "Spitzenreiter", top_name)
stat_card(s2, "Städte", str(len(staedte)))
stat_card(s3, "APIs aktiv", f"{apis_aktiv} / 4")
best_sonne = df.loc[df["sonnenstunden_jahr"].idxmax(), "name"] if hat_wetter and "sonnenstunden_jahr" in df.columns and df["sonnenstunden_jahr"].notna().any() else "—"
stat_card(s4, "Meiste Sonne", best_sonne)

# ---------------------------------------------------------------
# API-Status
# ---------------------------------------------------------------

st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
api_html = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:0.5rem">'
for api_name, aktiv in [
    ("Open-Meteo (Klima)",          hat_wetter),
    ("Mietspiegel (Wohnen)",         hat_miete),
    ("Arbeitsagentur (Wirtschaft)",  hat_arbeit),
    ("Overpass/OSM (Infrastruktur)", hat_infra),
]:
    farbe  = "#c6f6d5" if aktiv else "#fed7d7"
    txt    = "#276749" if aktiv else "#9b2c2c"
    status = "aktiv"   if aktiv else "ausstehend"
    api_html += f'<div style="background:{farbe};color:{txt};font-size:0.72rem;padding:4px 12px;border-radius:999px;font-weight:500">{api_name} · {status}</div>'
api_html += '</div>'
st.markdown(api_html, unsafe_allow_html=True)

# ---------------------------------------------------------------
# Siegerpodest mit Medaillen
# ---------------------------------------------------------------

st.markdown('<div class="section-label">Siegerpodest</div>', unsafe_allow_html=True)

top3 = df_sorted.head(3).reset_index(drop=True)

def podest_score(row):
    s = row.get("gesamtscore")
    return f"{int(float(s)*100)} Punkte" if pd.notna(s) else "—"

if len(top3) >= 3:
    pod_html = '<div class="podest-wrap">'

    r2 = top3.iloc[1]
    pod_html += f"""
    <div class="podest-card" style="margin-top: 40px;">
        <div style="font-size:32px;margin-bottom:6px">&#x1F948;</div>
        <div class="podest-city">{r2['name']}</div>
        <div class="podest-state">{r2['bundesland']}</div>
        <div class="podest-score">{podest_score(r2)}</div>
    </div>"""

    r1 = top3.iloc[0]
    pod_html += f"""
    <div class="podest-card gold" style="margin-top: 0px;">
        <div style="font-size:40px;margin-bottom:6px">&#x1F947;</div>
        <div class="podest-city gold">{r1['name']}</div>
        <div class="podest-state">{r1['bundesland']}</div>
        <div class="podest-score">{podest_score(r1)}</div>
    </div>"""

    r3 = top3.iloc[2]
    pod_html += f"""
    <div class="podest-card" style="margin-top: 60px;">
        <div style="font-size:28px;margin-bottom:6px">&#x1F949;</div>
        <div class="podest-city">{r3['name']}</div>
        <div class="podest-state">{r3['bundesland']}</div>
        <div class="podest-score">{podest_score(r3)}</div>
    </div>"""

    pod_html += '</div>'
    st.markdown(pod_html, unsafe_allow_html=True)

# ---------------------------------------------------------------
# Ranking-Tabelle (2 Spalten)
# ---------------------------------------------------------------

st.markdown('<div class="section-label">Gesamtranking</div>', unsafe_allow_html=True)

FARBEN = {
    "score_klima":         "#5DCAA5",
    "score_wohnen":        "#378ADD",
    "score_wirtschaft":    "#EF9F27",
    "score_infrastruktur": "#D85A30",
}

BL = {"Nordrhein-Westfalen":"NW","Bayern":"BY","Baden-Württemberg":"BW",
      "Sachsen":"SN","Berlin":"BE","Hamburg":"HH","Bremen":"HB","Hessen":"HE",
      "Niedersachsen":"NI","Brandenburg":"BB","Thüringen":"TH",
      "Sachsen-Anhalt":"ST","Rheinland-Pfalz":"RP","Saarland":"SL",
      "Schleswig-Holstein":"SH","Mecklenburg-Vorpommern":"MV"}

def ranking_zeile(row):
    rang  = int(row.get("rang", 0)) if pd.notna(row.get("rang")) else "—"
    score = row.get("gesamtscore")
    score_txt = f"{int(float(score)*100)}%" if pd.notna(score) else "—"
    bars = ""
    for col, farbe in FARBEN.items():
        v = row.get(col)
        w = max(3, int(float(v) * 40)) if pd.notna(v) else 3
        bars += f'<div style="width:{w}px;height:14px;border-radius:3px;background:{farbe};opacity:0.85;display:inline-block;margin-right:3px"></div>'
    bl_kuerzel = BL.get(row["bundesland"], row["bundesland"][:2].upper())
    return f"""<div style="display:flex;align-items:center;padding:8px 10px;
        border-bottom:0.5px solid #f3f5f7;font-size:0.88rem;">
        <div style="width:28px;color:#c0cdd8;font-size:0.8rem">{rang}</div>
        <div style="flex:1;font-weight:500;color:#0f1923">{row['name']}
            <span style="font-size:0.72rem;color:#b0bec8;margin-left:4px">{bl_kuerzel}</span>
        </div>
        <div style="display:flex;align-items:center;margin-right:12px">{bars}</div>
        <div style="font-weight:500;color:#0f1923;width:36px;text-align:right">{score_txt}</div>
    </div>"""

col_links, col_rechts = st.columns(2)
with col_links:
    for _, row in df_sorted.iloc[:10].iterrows():
        st.markdown(ranking_zeile(row), unsafe_allow_html=True)
with col_rechts:
    for _, row in df_sorted.iloc[10:].iterrows():
        st.markdown(ranking_zeile(row), unsafe_allow_html=True)

st.markdown("""<div style="display:flex;gap:16px;margin-top:10px;flex-wrap:wrap;">
    <span style="display:flex;align-items:center;gap:5px;font-size:11px;color:#9aabba"><span style="width:10px;height:10px;border-radius:2px;background:#5DCAA5;display:inline-block"></span>Klima</span>
    <span style="display:flex;align-items:center;gap:5px;font-size:11px;color:#9aabba"><span style="width:10px;height:10px;border-radius:2px;background:#378ADD;display:inline-block"></span>Wohnen</span>
    <span style="display:flex;align-items:center;gap:5px;font-size:11px;color:#9aabba"><span style="width:10px;height:10px;border-radius:2px;background:#EF9F27;display:inline-block"></span>Wirtschaft</span>
    <span style="display:flex;align-items:center;gap:5px;font-size:11px;color:#9aabba"><span style="width:10px;height:10px;border-radius:2px;background:#D85A30;display:inline-block"></span>Infrastruktur</span>
</div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Detailansicht
# ---------------------------------------------------------------

st.markdown('<div class="section-label">Detailansicht</div>', unsafe_allow_html=True)

stadt_auswahl = st.selectbox("Stadt", df_sorted["name"].tolist(), label_visibility="collapsed")
row = df_sorted[df_sorted["name"] == stadt_auswahl].iloc[0]

def kachel(label, wert, einheit, farbe):
    return f"""<div class="detail-kachel" style="border-top-color:{farbe}">
        <div class="detail-kachel-label">{label}</div>
        <div class="detail-kachel-val">{wert}</div>
        <div class="detail-kachel-unit">{einheit}</div>
    </div>"""

def val(r, col, fmt="{:.1f}", fallback="—"):
    v = r.get(col)
    return fmt.format(float(v)) if pd.notna(v) else fallback

rang_v  = f"#{int(row['rang'])}" if pd.notna(row.get("rang")) else "—"
score_v = f"{int(float(row['gesamtscore'])*100)}%" if pd.notna(row.get("gesamtscore")) else "—"

detail = '<div class="detail-grid">'
detail += kachel("Rang",             rang_v,                                f"von {len(staedte)} Städten", "#0f3460")
detail += kachel("Gesamtscore",      score_v,                               "gewichtet",                   "#e94560")
detail += kachel("Sonnenstunden",    val(row,"sonnenstunden_jahr","{:.0f}"),  "h / Jahr",                   "#5DCAA5")
detail += kachel("Temperatur",       val(row,"durchschnittstemperatur"),      "°C",                         "#5DCAA5")
detail += kachel("Kaltmiete",        val(row,"mietpreis_kalt_qm","{:.2f}"),  "€/m²",                       "#378ADD")
detail += kachel("Arbeitslosigkeit", val(row,"arbeitslosenquote"),            "%",                          "#EF9F27")
detail += kachel("Haltestellen",     val(row,"haltestellen_anzahl","{:.0f}"), "im Stadtgebiet",             "#D85A30")
detail += kachel("POI-Dichte",       val(row,"poi_dichte"),                   "POIs/km²",                   "#D85A30")
detail += '</div>'
st.markdown(detail, unsafe_allow_html=True)

# ---------------------------------------------------------------
# Vergleichsdiagramm
# ---------------------------------------------------------------

st.markdown('<div class="section-label">Städtevergleich</div>', unsafe_allow_html=True)

kategorien = {
    "Gesamtscore":          ("gesamtscore",        False, "#378ADD"),
    "Klima":                ("score_klima",         False, "#5DCAA5"),
    "Wohnen":               ("score_wohnen",        False, "#378ADD"),
    "Wirtschaft":           ("score_wirtschaft",    False, "#EF9F27"),
    "Infrastruktur":        ("score_infrastruktur", False, "#D85A30"),
    "Sonnenstunden (h)":    ("sonnenstunden_jahr",  False, "#5DCAA5"),
    "Mietpreis (Euro/m2)":  ("mietpreis_kalt_qm",  True,  "#378ADD"),
    "Arbeitslosigkeit (%)": ("arbeitslosenquote",   True,  "#EF9F27"),
}

kat = st.selectbox("Kennzahl", list(kategorien.keys()), label_visibility="collapsed")
col_name, invertiert, farbe = kategorien[kat]

if col_name in df_sorted.columns and df_sorted[col_name].notna().any():
    df_bar = df_sorted[["name", col_name]].dropna().sort_values(col_name, ascending=invertiert)
    chart = alt.Chart(df_bar).mark_bar(
        cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color=farbe
    ).encode(
        x=alt.X("name:N", sort=None, title=None, axis=alt.Axis(labelAngle=-30, labelFontSize=12)),
        y=alt.Y(f"{col_name}:Q", title=kat, axis=alt.Axis(labelFontSize=11)),
        opacity=alt.condition(
            alt.datum["name"] == stadt_auswahl,
            alt.value(1.0), alt.value(0.55)
        ),
        tooltip=["name:N", alt.Tooltip(f"{col_name}:Q", title=kat, format=".2f")],
    ).properties(height=280).configure_axis(
        grid=False, labelFontSize=12
    ).configure_view(strokeWidth=0)
    st.altair_chart(chart, width='stretch')
else:
    st.info(f"Keine Daten fuer '{kat}' vorhanden.")

# ---------------------------------------------------------------
# Karte
# ---------------------------------------------------------------

st.markdown('<div class="section-label">Karte</div>', unsafe_allow_html=True)
karte_df = df_sorted[["name","latitude","longitude","gesamtscore"]].copy()
karte_df = karte_df.rename(columns={"latitude":"lat","longitude":"lon"})
karte_df["gesamtscore"] = karte_df["gesamtscore"].fillna(0)
st.map(karte_df, latitude="lat", longitude="lon", size=40000, zoom=5)

# ---------------------------------------------------------------
# Zeitreihe
# ---------------------------------------------------------------

if not ranking.empty and not zeit.empty:
    zr = ranking.merge(staedte[["stadt_id","name"]], on="stadt_id")
    zr = zr.merge(zeit[["zeit_id","jahr"]], on="zeit_id")
    if len(zr["jahr"].unique()) > 1:
        st.markdown('<div class="section-label">Entwicklung über Zeit</div>', unsafe_allow_html=True)
        metrik = st.selectbox("Metrik", ["gesamtscore","score_klima","score_wohnen","score_wirtschaft","score_infrastruktur"],
            format_func=lambda x: {"gesamtscore":"Gesamtscore","score_klima":"Klima","score_wohnen":"Wohnen","score_wirtschaft":"Wirtschaft","score_infrastruktur":"Infrastruktur"}[x],
            label_visibility="collapsed")
        linie = alt.Chart(zr).mark_line(point=True).encode(
            x=alt.X("jahr:O", title="Jahr"),
            y=alt.Y(f"{metrik}:Q", scale=alt.Scale(domain=[0,1]), title="Score"),
            color=alt.Color("name:N", title="Stadt"),
            tooltip=["name:N","jahr:O", alt.Tooltip(f"{metrik}:Q", format=".3f")],
        ).properties(height=280).configure_axis(grid=False).configure_view(strokeWidth=0)
        st.altair_chart(linie, width='stretch')

# ---------------------------------------------------------------
# Footer
# ---------------------------------------------------------------

st.markdown("<div style='margin-top:2.5rem;text-align:center;color:#b0bec8;font-size:0.75rem;padding:1rem 0'>UrbanScore Deutschland · Open-Meteo · Mietspiegel · Bundesagentur für Arbeit · OpenStreetMap</div>", unsafe_allow_html=True)
