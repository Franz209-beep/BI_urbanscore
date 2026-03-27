"""
UrbanScore Deutschland — Dashboard (Erweitert)
===============================================
Neu:
- 4 neue Kategorien: Bildung, Gesundheit, Freizeit, Sicherheit
- Personalisierung: Persona-Profile + individuelle Gewichtung
- Korrelationsanalysen: 4 vordefinierte Paare mit Scatter-Plot
"""

import sqlite3
import os
import datetime
import numpy as np
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
.header h1 { font-family: 'DM Serif Display', serif; font-size: 2.4rem; color: white; margin: 0 0 0.3rem 0; position: relative; z-index: 2; }
.header p  { color: #7a9ab5; font-size: 0.95rem; margin: 0; font-weight: 300; position: relative; z-index: 2; }
.skyline   { position: absolute; bottom: 0; right: 0; opacity: 0.12; z-index: 1; }

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

.persona-card { border: 2px solid transparent; border-radius: 12px; padding: 10px 14px; cursor: pointer; background: #f7f8fa; text-align: center; transition: all 0.2s; }
.persona-card.active { border-color: #378ADD; background: #ebf8ff; }
.persona-emoji { font-size: 1.8rem; }
.persona-label { font-size: 0.78rem; font-weight: 500; color: #0f1923; margin-top: 4px; }

.detail-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 12px; }
.detail-kachel { background: #f7f8fa; border-radius: 10px; padding: 12px 14px; text-align: center; border-top: 3px solid transparent; }
.detail-kachel-label { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 1px; color: #9aabba; margin-bottom: 6px; }
.detail-kachel-val { font-family: 'DM Serif Display', serif; font-size: 1.5rem; color: #0f1923; }
.detail-kachel-unit { font-size: 0.72rem; color: #b0bec8; margin-top: 2px; }

.corr-box { background: #f7f8fa; border-radius: 12px; padding: 14px 16px; margin-bottom: 12px; }
.corr-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 1px; color: #9aabba; margin-bottom: 4px; }
.corr-value { font-family: 'DM Serif Display', serif; font-size: 1.4rem; }
.corr-interp { font-size: 0.8rem; color: #7a9ab5; margin-top: 4px; }

.info-pill { display: inline-block; font-size: 0.7rem; padding: 3px 10px; border-radius: 999px; margin-bottom: 1rem; background: #ebf8ff; color: #2c5282; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Daten laden
# ---------------------------------------------------------------

@st.cache_data(ttl=3600)
def lade_daten():
    try:
        conn     = sqlite3.connect("urbanscore.db")
        staedte  = pd.read_sql_query("SELECT * FROM stadt", conn)
        zeit     = pd.read_sql_query("SELECT * FROM zeit ORDER BY jahr DESC", conn)
        wetter   = pd.read_sql_query("SELECT * FROM wetterdaten", conn)
        miete    = pd.read_sql_query("SELECT * FROM mietdaten", conn)
        arbeit   = pd.read_sql_query("SELECT * FROM arbeitsmarktdaten", conn)
        infra    = pd.read_sql_query("SELECT * FROM infrastruktur", conn)
        ranking  = pd.read_sql_query("SELECT * FROM ranking", conn)

        # Neue Tabellen (mit Fallback falls noch nicht vorhanden)
        def safe(q):
            try:    return pd.read_sql_query(q, conn)
            except: return pd.DataFrame()

        bildung    = safe("SELECT * FROM bildungsdaten")
        gesundheit = safe("SELECT * FROM gesundheitsdaten")
        freizeit   = safe("SELECT * FROM freizeitdaten")
        sicherheit = safe("SELECT * FROM sicherheitsdaten")

        conn.close()
        return staedte, zeit, wetter, miete, arbeit, infra, ranking, bildung, gesundheit, freizeit, sicherheit
    except Exception as e:
        st.error(f"Datenbankfehler: {e}")
        return [None] * 11

(staedte, zeit, wetter, miete, arbeit, infra,
 ranking, bildung, gesundheit, freizeit, sicherheit) = lade_daten()

if staedte is None:
    st.stop()

# ---------------------------------------------------------------
# Header
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
    <rect x="141" y="45" width="30" height="75" fill="white"/>
    <rect x="148" y="35" width="16" height="12" fill="white"/>
    <rect x="177" y="65" width="16" height="55" fill="white"/>
    <rect x="199" y="35" width="24" height="85" fill="white"/>
    <rect x="229" y="50" width="18" height="70" fill="white"/>
    <rect x="253" y="40" width="28" height="80" fill="white"/>
    <rect x="309" y="38" width="22" height="82" fill="white"/>
    <rect x="361" y="42" width="26" height="78" fill="white"/>
    <rect x="0"   y="118" width="420" height="4" fill="white"/>
  </svg>
  <h1>UrbanScore Deutschland</h1>
  <p>Klima · Wohnen · Wirtschaft · Infrastruktur · Bildung · Gesundheit · Freizeit · Sicherheit · Letzte Aktualisierung: {letzter_lauf}</p>
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

wetter_z    = fz(wetter)
miete_z     = fz(miete)
arbeit_z    = fz(arbeit)
infra_z     = fz(infra)
ranking_z   = fz(ranking)
bildung_z   = fz(bildung)
gesundheit_z = fz(gesundheit)
freizeit_z  = fz(freizeit)
sicherheit_z = fz(sicherheit)

# Alles zusammenführen
df = staedte.copy()
for tab in [wetter_z, miete_z, arbeit_z, infra_z, ranking_z,
            bildung_z, gesundheit_z, freizeit_z, sicherheit_z]:
    if not tab.empty:
        cols_to_drop = [c for c in tab.columns if c in df.columns and c != "stadt_id"]
        tab_clean = tab.drop(columns=cols_to_drop)
        df = df.merge(tab_clean, on="stadt_id", how="left")

hat_ranking    = not ranking_z.empty
hat_wetter     = not wetter_z.empty
hat_miete      = not miete_z.empty
hat_arbeit     = not arbeit_z.empty
hat_infra      = not infra_z.empty
hat_bildung    = not bildung_z.empty
hat_gesundheit = not gesundheit_z.empty
hat_freizeit   = not freizeit_z.empty
hat_sicherheit = not sicherheit_z.empty

# ---------------------------------------------------------------
# ═══════════════════════════════════════════════════════════════
# PERSONALISIERUNG
# Kombiniert: Persona-Profile + individuelle Schieberegler
# ═══════════════════════════════════════════════════════════════
# ---------------------------------------------------------------

st.markdown('<div class="section-label">🎯 Mein Profil — Personalisiertes Ranking</div>', unsafe_allow_html=True)

PERSONAS = {
    "Familie":    {"emoji": "👨‍👩‍👧", "gewichte": {"Klima": 10, "Wohnen": 25, "Wirtschaft": 15, "Infrastruktur": 10, "Bildung": 25, "Gesundheit": 10, "Freizeit": 5, "Sicherheit": 0}},
    "Freelancer": {"emoji": "💻", "gewichte": {"Klima": 15, "Wohnen": 20, "Wirtschaft": 20, "Infrastruktur": 20, "Bildung": 5,  "Gesundheit": 5,  "Freizeit": 15, "Sicherheit": 0}},
    "Rentner":    {"emoji": "🌿", "gewichte": {"Klima": 20, "Wohnen": 25, "Wirtschaft": 5,  "Infrastruktur": 15, "Bildung": 0,  "Gesundheit": 25, "Freizeit": 10, "Sicherheit": 0}},
    "Student":    {"emoji": "🎓", "gewichte": {"Klima": 10, "Wohnen": 30, "Wirtschaft": 10, "Infrastruktur": 20, "Bildung": 20, "Gesundheit": 5,  "Freizeit": 5,  "Sicherheit": 0}},
    "Individuell":{"emoji": "⚙️", "gewichte": None},
}

# Persona-Auswahl
persona_cols = st.columns(len(PERSONAS))
if "aktive_persona" not in st.session_state:
    st.session_state.aktive_persona = "Familie"

for col, (name, info) in zip(persona_cols, PERSONAS.items()):
    with col:
        aktiv = st.session_state.aktive_persona == name
        style = "background:#ebf8ff;border:2px solid #378ADD;" if aktiv else "background:#f7f8fa;border:2px solid transparent;"
        if st.button(f"{info['emoji']}\n{name}", key=f"persona_{name}", use_container_width=True):
            st.session_state.aktive_persona = name

aktive_persona   = st.session_state.aktive_persona
persona_gewichte = PERSONAS[aktive_persona]["gewichte"]

# Schieberegler (bei Individuell immer editierbar, sonst vorbelegt)
st.markdown("<div style='margin-top:0.8rem'></div>", unsafe_allow_html=True)
slider_cols = st.columns(4)

SCORE_MAP = {
    "Klima":         "score_klima",
    "Wohnen":        "score_wohnen",
    "Wirtschaft":    "score_wirtschaft",
    "Infrastruktur": "score_infrastruktur",
    "Bildung":        "score_bildung",
    "Gesundheit":     "score_gesundheit",
    "Freizeit":       "score_freizeit",
    "Sicherheit":     "score_sicherheit",
}

SLIDER_FARBEN = {
    "Klima": "#5DCAA5", "Wohnen": "#378ADD", "Wirtschaft": "#EF9F27",
    "Infrastruktur": "#D85A30", "Bildung": "#9B59B6", "Gesundheit": "#E74C3C",
    "Freizeit": "#27AE60", "Sicherheit": "#2C3E50",
}

gewichte_user = {}
slider_namen  = list(SCORE_MAP.keys())

for idx, name in enumerate(slider_namen):
    col = slider_cols[idx % 4]
    with col:
        vorwert = persona_gewichte[name] if (persona_gewichte and aktive_persona != "Individuell") else 10
        disabled = (aktive_persona != "Individuell") and (persona_gewichte is not None)
        val = st.slider(
            name,
            min_value=0, max_value=40,
            value=vorwert,
            disabled=disabled,
            key=f"slider_{name}_{aktive_persona}",
        )
        gewichte_user[name] = val

gesamt_gewicht = sum(gewichte_user.values())
if gesamt_gewicht == 0:
    gesamt_gewicht = 1

# Personalisierten Score berechnen
def berechne_personscore(row):
    total = 0.0
    for name, col in SCORE_MAP.items():
        v = row.get(col)
        if pd.notna(v):
            total += float(v) * (gewichte_user[name] / gesamt_gewicht)
    return total

if hat_ranking:
    df["personscore"] = df.apply(berechne_personscore, axis=1)
    df_person = df.sort_values("personscore", ascending=False).reset_index(drop=True)
    df_person["person_rang"] = range(1, len(df_person) + 1)
else:
    df_person = df.copy()
    df_person["person_rang"] = range(1, len(df_person) + 1)

# Personalisiertes Podest
st.markdown(f'<div class="section-label">Ergebnis für Profil: {PERSONAS[aktive_persona]["emoji"]} {aktive_persona}</div>', unsafe_allow_html=True)

top3p = df_person.head(3)
if len(top3p) >= 3:
    pod_html = '<div class="podest-wrap">'
    def pscore(r):
        s = r.get("personscore")
        return f"{int(float(s)*100)} Punkte" if pd.notna(s) else "—"

    r2 = top3p.iloc[1]
    pod_html += f'<div class="podest-card" style="margin-top:40px"><div style="font-size:32px;margin-bottom:6px">🥈</div><div class="podest-city">{r2["name"]}</div><div class="podest-state">{r2["bundesland"]}</div><div class="podest-score">{pscore(r2)}</div></div>'
    r1 = top3p.iloc[0]
    pod_html += f'<div class="podest-card gold" style="margin-top:0px"><div style="font-size:40px;margin-bottom:6px">🥇</div><div class="podest-city gold">{r1["name"]}</div><div class="podest-state">{r1["bundesland"]}</div><div class="podest-score">{pscore(r1)}</div></div>'
    r3 = top3p.iloc[2]
    pod_html += f'<div class="podest-card" style="margin-top:60px"><div style="font-size:28px;margin-bottom:6px">🥉</div><div class="podest-city">{r3["name"]}</div><div class="podest-state">{r3["bundesland"]}</div><div class="podest-score">{pscore(r3)}</div></div>'
    pod_html += '</div>'
    st.markdown(pod_html, unsafe_allow_html=True)

# ---------------------------------------------------------------
# Gesamtranking (Standard)
# ---------------------------------------------------------------

df_sorted = df_person  # Für den Rest des Dashboards nach Personscore sortieren

st.markdown('<div class="section-label">Gesamtranking</div>', unsafe_allow_html=True)

FARBEN = {
    "score_klima":         "#5DCAA5",
    "score_wohnen":        "#378ADD",
    "score_wirtschaft":    "#EF9F27",
    "score_infrastruktur": "#D85A30",
    "score_bildung":       "#9B59B6",
    "score_gesundheit":    "#E74C3C",
    "score_freizeit":      "#27AE60",
    "score_sicherheit":    "#2C3E50",
}

BL = {"Nordrhein-Westfalen":"NW","Bayern":"BY","Baden-Württemberg":"BW",
      "Sachsen":"SN","Berlin":"BE","Hamburg":"HH","Bremen":"HB","Hessen":"HE",
      "Niedersachsen":"NI","Brandenburg":"BB","Thüringen":"TH",
      "Sachsen-Anhalt":"ST","Rheinland-Pfalz":"RP","Saarland":"SL",
      "Schleswig-Holstein":"SH","Mecklenburg-Vorpommern":"MV"}

def ranking_zeile(row):
    rang      = int(row.get("person_rang", 0))
    score     = row.get("personscore") if hat_ranking else None
    score_txt = f"{int(float(score)*100)}%" if pd.notna(score) else "—"
    bars = ""
    for col, farbe in FARBEN.items():
        v = row.get(col)
        w = max(3, int(float(v) * 30)) if pd.notna(v) else 3
        bars += f'<div style="width:{w}px;height:12px;border-radius:3px;background:{farbe};opacity:0.85;display:inline-block;margin-right:2px"></div>'
    bl_kuerzel = BL.get(row["bundesland"], row["bundesland"][:2].upper())
    return f"""<div style="display:flex;align-items:center;padding:7px 10px;
        border-bottom:0.5px solid #f3f5f7;font-size:0.88rem;">
        <div style="width:28px;color:#c0cdd8;font-size:0.8rem">{rang}</div>
        <div style="flex:1;font-weight:500;color:#0f1923">{row['name']}
            <span style="font-size:0.72rem;color:#b0bec8;margin-left:4px">{bl_kuerzel}</span>
        </div>
        <div style="display:flex;align-items:center;margin-right:10px">{bars}</div>
        <div style="font-weight:500;color:#0f1923;width:36px;text-align:right">{score_txt}</div>
    </div>"""

col_links, col_rechts = st.columns(2)
with col_links:
    for _, row in df_sorted.iloc[:10].iterrows():
        st.markdown(ranking_zeile(row), unsafe_allow_html=True)
with col_rechts:
    for _, row in df_sorted.iloc[10:].iterrows():
        st.markdown(ranking_zeile(row), unsafe_allow_html=True)

# Legende (alle 8 Kategorien)
legend_items = [
    ("#5DCAA5","Klima"), ("#378ADD","Wohnen"), ("#EF9F27","Wirtschaft"),
    ("#D85A30","Infra"), ("#9B59B6","Bildung"), ("#E74C3C","Gesundheit"),
    ("#27AE60","Freizeit"), ("#2C3E50","Sicherheit"),
]
legend_html = '<div style="display:flex;gap:14px;margin-top:10px;flex-wrap:wrap;">'
for farbe, label in legend_items:
    legend_html += f'<span style="display:flex;align-items:center;gap:5px;font-size:11px;color:#9aabba"><span style="width:10px;height:10px;border-radius:2px;background:{farbe};display:inline-block"></span>{label}</span>'
legend_html += '</div>'
st.markdown(legend_html, unsafe_allow_html=True)

# ---------------------------------------------------------------
# ═══════════════════════════════════════════════════════════════
# KORRELATIONSANALYSEN
# ═══════════════════════════════════════════════════════════════
# ---------------------------------------------------------------

st.markdown('<div class="section-label">📊 Korrelationsanalysen</div>', unsafe_allow_html=True)

KORRELATIONEN = {
    "Miete vs. Lebensqualität": {
        "x": "mietpreis_kalt_qm",
        "y": "gesamtscore",
        "x_label": "Kaltmiete (€/m²)",
        "y_label": "Gesamtscore",
        "beschreibung": "Zahlt man in teureren Städten wirklich für mehr Lebensqualität?",
        "farbe": "#378ADD",
    },
    "Arbeitslosigkeit vs. Kriminalität": {
        "x": "arbeitslosenquote",
        "y": "straftaten_je_100k",
        "x_label": "Arbeitslosenquote (%)",
        "y_label": "Straftaten je 100.000 EW",
        "beschreibung": "Besteht ein Zusammenhang zwischen wirtschaftlicher Not und Kriminalität?",
        "farbe": "#D85A30",
    },
    "Infrastruktur vs. Mietpreis": {
        "x": "poi_dichte",
        "y": "mietpreis_kalt_qm",
        "x_label": "POI-Dichte (POIs/km²)",
        "y_label": "Kaltmiete (€/m²)",
        "beschreibung": "Treibt bessere Infrastruktur die Mietpreise nach oben?",
        "farbe": "#EF9F27",
    },
    "Klima vs. Zufriedenheit": {
        "x": "sonnenstunden_jahr",
        "y": "gesamtscore",
        "x_label": "Sonnenstunden / Jahr",
        "y_label": "Gesamtscore",
        "beschreibung": "Profitieren sonnige Städte beim Gesamtranking?",
        "farbe": "#5DCAA5",
    },
}

def korrelation_berechnen(df, x_col, y_col):
    """Pearson-Korrelation mit Interpretation."""
    sub = df[[x_col, y_col]].dropna()
    if len(sub) < 4:
        return None, "Zu wenig Daten", "#9aabba"
    r = float(np.corrcoef(sub[x_col], sub[y_col])[0, 1])
    abs_r = abs(r)
    if abs_r >= 0.7:
        staerke = "stark"
    elif abs_r >= 0.4:
        staerke = "moderat"
    else:
        staerke = "schwach"
    richtung = "positiv" if r > 0 else "negativ"
    interp = f"{staerke} {richtung}er Zusammenhang"
    farbe = "#276749" if abs_r >= 0.7 else ("#744210" if abs_r >= 0.4 else "#2a4365")
    return round(r, 3), interp, farbe

kat_auswahl = st.selectbox(
    "Korrelation wählen",
    list(KORRELATIONEN.keys()),
    label_visibility="collapsed",
)
kdef = KORRELATIONEN[kat_auswahl]
x_col, y_col = kdef["x"], kdef["y"]

col_info, col_chart = st.columns([1, 3])

with col_info:
    r_val, interp, r_farbe = korrelation_berechnen(df, x_col, y_col)
    r_txt = f"{r_val:.3f}" if r_val is not None else "—"
    st.markdown(f"""
    <div class="corr-box">
        <div class="corr-label">Pearson r</div>
        <div class="corr-value" style="color:{r_farbe}">{r_txt}</div>
        <div class="corr-interp">{interp}</div>
    </div>
    <div style="font-size:0.82rem;color:#5a7a96;line-height:1.5;margin-top:8px">
        {kdef['beschreibung']}
    </div>
    """, unsafe_allow_html=True)

with col_chart:
    if x_col in df.columns and y_col in df.columns and df[x_col].notna().any():
        scatter_df = df[["name", x_col, y_col]].dropna()
        chart = alt.Chart(scatter_df).mark_circle(size=90, opacity=0.8).encode(
            x=alt.X(f"{x_col}:Q", title=kdef["x_label"]),
            y=alt.Y(f"{y_col}:Q", title=kdef["y_label"]),
            color=alt.value(kdef["farbe"]),
            tooltip=["name:N",
                     alt.Tooltip(f"{x_col}:Q", title=kdef["x_label"], format=".2f"),
                     alt.Tooltip(f"{y_col}:Q", title=kdef["y_label"], format=".2f")],
        )
        # Trendlinie
        trend = chart.transform_regression(x_col, y_col).mark_line(
            opacity=0.4, strokeDash=[6, 4], color=kdef["farbe"]
        )
        labels = chart.mark_text(dy=-10, fontSize=10, color="#0f1923").encode(
            text="name:N"
        )
        final = (chart + trend + labels).properties(height=320).configure_axis(
            grid=False, labelFontSize=11
        ).configure_view(strokeWidth=0)
        st.altair_chart(final, use_container_width=True)
    else:
        st.info(f"Keine ausreichenden Daten für diese Korrelation.")

# ---------------------------------------------------------------
# Detailansicht (erweitert auf 12 Kacheln)
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

rang_v  = f"#{int(row['person_rang'])}" if pd.notna(row.get("person_rang")) else "—"
score_v = f"{int(float(row['personscore'])*100)}%" if pd.notna(row.get("personscore")) else "—"

detail = '<div class="detail-grid">'
# Zeile 1: Allgemein
detail += kachel("Rang (Profil)", rang_v, f"von {len(staedte)} Städten", "#0f3460")
detail += kachel("Personscore",   score_v, aktive_persona, "#e94560")
detail += kachel("Sonnenstunden", val(row,"sonnenstunden_jahr","{:.0f}"), "h / Jahr", "#5DCAA5")
detail += kachel("Temperatur",    val(row,"durchschnittstemperatur"), "°C", "#5DCAA5")
# Zeile 2: Wohnen & Wirtschaft
detail += kachel("Kaltmiete",        val(row,"mietpreis_kalt_qm","{:.2f}"), "€/m²",    "#378ADD")
detail += kachel("Arbeitslosigkeit", val(row,"arbeitslosenquote"),          "%",        "#EF9F27")
detail += kachel("Haltestellen",     val(row,"haltestellen_anzahl","{:.0f}"), "im Stadtgebiet", "#D85A30")
detail += kachel("POI-Dichte",       val(row,"poi_dichte"), "POIs/km²",                "#D85A30")
# Zeile 3: Neue Kategorien
detail += kachel("Schulen+Kitas",    val(row,"schulen_anzahl","{:.0f}"), "+ " + val(row,"kitas_anzahl","{:.0f}"),  "#9B59B6")
detail += kachel("Bildungsdichte",   val(row,"bildungs_dichte","{:.2f}"), "Einricht./km²",                         "#9B59B6")
detail += kachel("Ärzte+Apotheken",  val(row,"aerzte_anzahl","{:.0f}"),  "+ " + val(row,"apotheken_anzahl","{:.0f}"), "#E74C3C")
detail += kachel("Gesundheitsdichte",val(row,"gesundheits_dichte","{:.2f}"), "Einricht./km²",                      "#E74C3C")
detail += kachel("Parks",            val(row,"parks_anzahl","{:.0f}"),   "im Stadtgebiet",                         "#27AE60")
detail += kachel("Kulturdichte",     val(row,"kultur_anzahl","{:.0f}"),  "Museen+Theater+Kino",                    "#27AE60")
detail += kachel("Straftaten",       val(row,"straftaten_je_100k","{:.0f}"), "je 100.000 EW",                      "#2C3E50")
detail += kachel("Gewaltdelikte",    val(row,"gewaltdelikte_je_100k","{:.0f}"), "je 100.000 EW",                   "#2C3E50")
detail += '</div>'
st.markdown(detail, unsafe_allow_html=True)

# ---------------------------------------------------------------
# Städtevergleich (Balkendiagramm)
# ---------------------------------------------------------------

st.markdown('<div class="section-label">Städtevergleich</div>', unsafe_allow_html=True)

kategorien = {
    "Gesamtscore (Standard)":    ("gesamtscore",            False, "#378ADD"),
    "Personscore (mein Profil)": ("personscore",            False, "#9B59B6"),
    "Klima":                     ("score_klima",            False, "#5DCAA5"),
    "Wohnen":                    ("score_wohnen",           False, "#378ADD"),
    "Wirtschaft":                ("score_wirtschaft",       False, "#EF9F27"),
    "Infrastruktur":             ("score_infrastruktur",    False, "#D85A30"),
    "Bildung":                   ("score_bildung",          False, "#9B59B6"),
    "Gesundheit":                ("score_gesundheit",       False, "#E74C3C"),
    "Freizeit":                  ("score_freizeit",         False, "#27AE60"),
    "Sicherheit":                ("score_sicherheit",       False, "#2C3E50"),
    "Sonnenstunden (h)":         ("sonnenstunden_jahr",     False, "#5DCAA5"),
    "Mietpreis (€/m²)":         ("mietpreis_kalt_qm",      True,  "#378ADD"),
    "Arbeitslosigkeit (%)":      ("arbeitslosenquote",      True,  "#EF9F27"),
    "Straftaten je 100k":        ("straftaten_je_100k",     True,  "#2C3E50"),
    "Bildungsdichte":            ("bildungs_dichte",        False, "#9B59B6"),
    "Gesundheitsdichte":         ("gesundheits_dichte",     False, "#E74C3C"),
    "Freizeitdichte":            ("freizeit_dichte",        False, "#27AE60"),
}

kat = st.selectbox("Kennzahl", list(kategorien.keys()), label_visibility="collapsed")
col_name, invertiert, farbe = kategorien[kat]

if col_name in df_sorted.columns and df_sorted[col_name].notna().any():
    df_bar = df_sorted[["name", col_name]].dropna().sort_values(col_name, ascending=invertiert)
    chart = alt.Chart(df_bar).mark_bar(
        cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color=farbe
    ).encode(
        x=alt.X("name:N", sort=None, title=None,
                axis=alt.Axis(labelAngle=-30, labelFontSize=12)),
        y=alt.Y(f"{col_name}:Q", title=kat,
                axis=alt.Axis(labelFontSize=11)),
        opacity=alt.condition(
            alt.datum["name"] == stadt_auswahl,
            alt.value(1.0), alt.value(0.55)
        ),
        tooltip=["name:N", alt.Tooltip(f"{col_name}:Q", title=kat, format=".2f")],
    ).properties(height=280).configure_axis(
        grid=False, labelFontSize=12
    ).configure_view(strokeWidth=0)
    st.altair_chart(chart, use_container_width=True)
else:
    st.info(f"Keine Daten für '{kat}' vorhanden.")

# ---------------------------------------------------------------
# Karte
# ---------------------------------------------------------------

st.markdown('<div class="section-label">Karte</div>', unsafe_allow_html=True)
karte_df = df_sorted[["name", "latitude", "longitude", "personscore"]].copy()
karte_df = karte_df.rename(columns={"latitude": "lat", "longitude": "lon"})
karte_df["personscore"] = karte_df["personscore"].fillna(0)
st.map(karte_df, latitude="lat", longitude="lon", size=40000, zoom=5)

# ---------------------------------------------------------------
# Zeitreihe
# ---------------------------------------------------------------

if not ranking.empty and not zeit.empty:
    zr = ranking.merge(staedte[["stadt_id", "name"]], on="stadt_id")
    zr = zr.merge(zeit[["zeit_id", "jahr"]], on="zeit_id")
    if len(zr["jahr"].unique()) > 1:
        st.markdown('<div class="section-label">Entwicklung über Zeit</div>', unsafe_allow_html=True)
        metrik_optionen = {
            "gesamtscore": "Gesamtscore", "score_klima": "Klima", "score_wohnen": "Wohnen",
            "score_wirtschaft": "Wirtschaft", "score_infrastruktur": "Infrastruktur",
            "score_bildung": "Bildung", "score_gesundheit": "Gesundheit",
            "score_freizeit": "Freizeit", "score_sicherheit": "Sicherheit",
        }
        verfuegbare = {k: v for k, v in metrik_optionen.items() if k in zr.columns}
        metrik = st.selectbox("Metrik", list(verfuegbare.keys()),
            format_func=lambda x: verfuegbare[x], label_visibility="collapsed")
        linie = alt.Chart(zr).mark_line(point=True).encode(
            x=alt.X("jahr:O", title="Jahr"),
            y=alt.Y(f"{metrik}:Q", scale=alt.Scale(domain=[0, 1]), title="Score"),
            color=alt.Color("name:N", title="Stadt"),
            tooltip=["name:N", "jahr:O", alt.Tooltip(f"{metrik}:Q", format=".3f")],
        ).properties(height=280).configure_axis(grid=False).configure_view(strokeWidth=0)
        st.altair_chart(linie, use_container_width=True)

# ---------------------------------------------------------------
# API-Status
# ---------------------------------------------------------------

st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
api_html = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:0.5rem">'
for api_name, aktiv in [
    ("Open-Meteo (Klima)",          hat_wetter),
    ("Mietspiegel (Wohnen)",        hat_miete),
    ("Arbeitsagentur (Wirtschaft)", hat_arbeit),
    ("Overpass/OSM (Infra)",        hat_infra),
    ("Overpass/OSM (Bildung)",      hat_bildung),
    ("Overpass/OSM (Gesundheit)",   hat_gesundheit),
    ("Overpass/OSM (Freizeit)",     hat_freizeit),
    ("BKA PKS (Sicherheit)",        hat_sicherheit),
]:
    farbe  = "#c6f6d5" if aktiv else "#fed7d7"
    txt    = "#276749" if aktiv else "#9b2c2c"
    status = "aktiv"   if aktiv else "ausstehend"
    api_html += f'<div style="background:{farbe};color:{txt};font-size:0.72rem;padding:4px 12px;border-radius:999px;font-weight:500">{api_name} · {status}</div>'
api_html += '</div>'
st.markdown(api_html, unsafe_allow_html=True)

# Footer
st.markdown(
    "<div style='margin-top:2.5rem;text-align:center;color:#b0bec8;font-size:0.75rem;padding:1rem 0'>"
    "UrbanScore Deutschland · Open-Meteo · Mietspiegel · Bundesagentur für Arbeit · "
    "OpenStreetMap · BKA PKS 2023</div>",
    unsafe_allow_html=True
)
