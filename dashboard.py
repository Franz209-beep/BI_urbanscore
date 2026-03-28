"""
UrbanScore Deutschland — Dashboard
====================================
- Professionelles minimalistisches Design ohne Emojis
- Persona-Gewichte realistisch (Sicherheit > 0 überall)
- Individuell: Gewichte werden auf 100% normiert (kein Overflow)
- Detailansicht: Dimensionen untereinander mit Score-Zusammensetzung
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

.us-header {
    background: #111418;
    border-radius: 4px;
    padding: 2.2rem 2.5rem 2rem;
    margin-bottom: 1.8rem;
}
.us-header h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 2rem;
    font-weight: 400;
    color: #f0f2f5;
    margin: 0 0 0.25rem 0;
    letter-spacing: -0.01em;
}
.us-header p { color: #4a5568; font-size: 0.82rem; margin: 0; }

.us-section {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #a0aec0;
    margin: 2rem 0 0.9rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #f0f2f5;
}

.us-top3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1px;
           background: #edf2f7; border: 1px solid #edf2f7; border-radius: 4px;
           overflow: hidden; margin: 0.5rem 0 1.5rem 0; }
.us-top3-card { background: white; padding: 1.4rem 1.2rem; text-align: center; }
.us-top3-card.first { background: #fafafa; }
.us-top3-rank { font-size: 0.6rem; font-weight: 600; letter-spacing: 0.12em;
                text-transform: uppercase; color: #a0aec0; margin-bottom: 0.5rem; }
.us-top3-rank.first { color: #b7791f; }
.us-top3-city { font-family: 'DM Serif Display', serif; font-size: 1.1rem; font-weight: 400; color: #111418; }
.us-top3-card.first .us-top3-city { font-size: 1.25rem; }
.us-top3-state { font-size: 0.72rem; color: #a0aec0; margin-top: 3px; }
.us-top3-score { font-size: 0.78rem; color: #718096; margin-top: 8px; font-weight: 500; }

.us-rank-row { display: flex; align-items: center; padding: 7px 0;
               border-bottom: 1px solid #f7f8fa; font-size: 0.82rem; }
.us-rank-num { width: 28px; color: #cbd5e0; font-size: 0.75rem; font-variant-numeric: tabular-nums; }
.us-rank-name { flex: 1; font-weight: 500; color: #111418; }
.us-rank-state { font-size: 0.68rem; color: #cbd5e0; margin-left: 5px; font-weight: 400; }
.us-rank-bars { display: flex; align-items: center; gap: 2px; margin: 0 10px; }
.us-rank-score { width: 38px; text-align: right; font-weight: 500; color: #111418;
                 font-size: 0.8rem; font-variant-numeric: tabular-nums; }

.us-dim-row {
    display: grid;
    grid-template-columns: 110px 1fr 220px 55px;
    align-items: center;
    gap: 14px;
    padding: 11px 0;
    border-bottom: 1px solid #f7f8fa;
}
.us-dim-label { font-size: 0.75rem; font-weight: 600; color: #2d3748; }
.us-dim-gew { font-size: 0.65rem; color: #a0aec0; margin-top: 2px; }
.us-dim-bar-bg { background: #f0f2f5; border-radius: 2px; height: 7px; }
.us-dim-bar-fill { height: 7px; border-radius: 2px; }
.us-dim-details { font-size: 0.69rem; color: #718096; line-height: 1.7; }
.us-dim-score { font-family: 'DM Serif Display', serif; font-size: 1.05rem;
                font-weight: 400; color: #111418; text-align: right; }

.us-corr-stat { background: #fafafa; border: 1px solid #edf2f7; border-radius: 4px;
                padding: 1.2rem; margin-bottom: 0.8rem; }
.us-corr-label { font-size: 0.65rem; font-weight: 600; text-transform: uppercase;
                 letter-spacing: 0.1em; color: #a0aec0; margin-bottom: 6px; }
.us-corr-val { font-family: 'DM Serif Display', serif; font-size: 1.6rem; font-weight: 400; }
.us-corr-desc { font-size: 0.75rem; color: #718096; margin-top: 4px; line-height: 1.5; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Daten laden
# ---------------------------------------------------------------

@st.cache_data(ttl=3600)
def lade_daten():
    try:
        conn    = sqlite3.connect("urbanscore.db")
        staedte = pd.read_sql_query("SELECT * FROM stadt", conn)
        zeit    = pd.read_sql_query("SELECT * FROM zeit ORDER BY jahr DESC", conn)
        wetter  = pd.read_sql_query("SELECT * FROM wetterdaten", conn)
        miete   = pd.read_sql_query("SELECT * FROM mietdaten", conn)
        arbeit  = pd.read_sql_query("SELECT * FROM arbeitsmarktdaten", conn)
        infra   = pd.read_sql_query("SELECT * FROM infrastruktur", conn)
        ranking = pd.read_sql_query("SELECT * FROM ranking", conn)
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
<div class="us-header">
  <h1>UrbanScore Deutschland</h1>
  <p>Multidimensionales Städteranking &nbsp;·&nbsp;
     Klima · Wohnen · Wirtschaft · Infrastruktur · Bildung · Gesundheit · Freizeit · Sicherheit
     &nbsp;·&nbsp; Stand: {letzter_lauf}</p>
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

wetter_z     = fz(wetter);    miete_z      = fz(miete)
arbeit_z     = fz(arbeit);    infra_z      = fz(infra)
ranking_z    = fz(ranking);   bildung_z    = fz(bildung)
gesundheit_z = fz(gesundheit); freizeit_z  = fz(freizeit)
sicherheit_z = fz(sicherheit)

df = staedte.copy()
for tab in [wetter_z, miete_z, arbeit_z, infra_z, ranking_z,
            bildung_z, gesundheit_z, freizeit_z, sicherheit_z]:
    if not tab.empty:
        drop = [c for c in tab.columns if c in df.columns and c != "stadt_id"]
        df = df.merge(tab.drop(columns=drop), on="stadt_id", how="left")

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
# Konstanten
# ---------------------------------------------------------------

SCORE_MAP = {
    "Klima":         "score_klima",
    "Wohnen":        "score_wohnen",
    "Wirtschaft":    "score_wirtschaft",
    "Infrastruktur": "score_infrastruktur",
    "Bildung":       "score_bildung",
    "Gesundheit":    "score_gesundheit",
    "Freizeit":      "score_freizeit",
    "Sicherheit":    "score_sicherheit",
}

DIM_FARBEN = {
    "Klima":         "#4A9B84",
    "Wohnen":        "#3B7EC8",
    "Wirtschaft":    "#C8891F",
    "Infrastruktur": "#B84C2A",
    "Bildung":       "#7B52AB",
    "Gesundheit":    "#C0392B",
    "Freizeit":      "#27855A",
    "Sicherheit":    "#2C3E50",
}

BL = {"Nordrhein-Westfalen":"NW","Bayern":"BY","Baden-Württemberg":"BW",
      "Sachsen":"SN","Berlin":"BE","Hamburg":"HH","Bremen":"HB","Hessen":"HE",
      "Niedersachsen":"NI","Brandenburg":"BB","Thüringen":"TH",
      "Sachsen-Anhalt":"ST","Rheinland-Pfalz":"RP","Saarland":"SL",
      "Schleswig-Holstein":"SH","Mecklenburg-Vorpommern":"MV"}

# ---------------------------------------------------------------
# PERSONALISIERUNG
# Sicherheit überall > 0; alle Personas summieren auf 100
# ---------------------------------------------------------------

st.markdown('<div class="us-section">Profil</div>', unsafe_allow_html=True)

PERSONAS = {
    "Familie": {
        "beschreibung": "Fokus auf Bildung, Wohnen und Sicherheit",
        "gewichte": {"Klima": 8, "Wohnen": 22, "Wirtschaft": 13,
                     "Infrastruktur": 10, "Bildung": 22, "Gesundheit": 10,
                     "Freizeit": 5,  "Sicherheit": 10},
    },
    "Freelancer": {
        "beschreibung": "Infrastruktur, Wirtschaft und Freizeit im Vordergrund",
        "gewichte": {"Klima": 12, "Wohnen": 18, "Wirtschaft": 18,
                     "Infrastruktur": 20, "Bildung": 5, "Gesundheit": 7,
                     "Freizeit": 12, "Sicherheit": 8},
    },
    "Rentner": {
        "beschreibung": "Klima, Gesundheit und ruhiges Wohnen",
        "gewichte": {"Klima": 18, "Wohnen": 22, "Wirtschaft": 5,
                     "Infrastruktur": 12, "Bildung": 3, "Gesundheit": 22,
                     "Freizeit": 8,  "Sicherheit": 10},
    },
    "Student": {
        "beschreibung": "Günstiges Wohnen, Bildung und ÖPNV",
        "gewichte": {"Klima": 8, "Wohnen": 28, "Wirtschaft": 10,
                     "Infrastruktur": 18, "Bildung": 20, "Gesundheit": 5,
                     "Freizeit": 5,  "Sicherheit": 6},
    },
    "Individuell": {
        "beschreibung": "Eigene Gewichtung — Summe wird automatisch auf 100% normiert",
        "gewichte": None,
    },
}

if "aktive_persona" not in st.session_state:
    st.session_state.aktive_persona = "Familie"

pcols = st.columns(len(PERSONAS))
for col, name in zip(pcols, PERSONAS.keys()):
    with col:
        aktiv = st.session_state.aktive_persona == name
        if st.button(name, key=f"pb_{name}", use_container_width=True,
                     type="primary" if aktiv else "secondary"):
            st.session_state.aktive_persona = name
            st.rerun()

aktive_persona   = st.session_state.aktive_persona
persona_gewichte = PERSONAS[aktive_persona]["gewichte"]
st.caption(PERSONAS[aktive_persona]["beschreibung"])

# Gewichte bestimmen
if aktive_persona == "Individuell":
    st.markdown("<div style='margin-top:0.8rem'></div>", unsafe_allow_html=True)
    sl_cols = st.columns(4)
    raw = {}
    for idx, name in enumerate(SCORE_MAP.keys()):
        with sl_cols[idx % 4]:
            raw[name] = st.slider(name, 0, 40, 10, key=f"sl_{name}")
    # Normieren auf 100 — kein Overflow möglich
    gesamt_raw = sum(raw.values()) or 1
    gewichte_user = {k: round(v / gesamt_raw * 100, 1) for k, v in raw.items()}
    st.caption(f"Summe: {sum(gewichte_user.values()):.0f}% (automatisch normiert)")
else:
    gewichte_user = {k: float(v) for k, v in persona_gewichte.items()}

# Gewichtsverteilung immer anzeigen (horizontal gestapelter Balken)
st.markdown("<div style='margin-top:0.8rem'></div>", unsafe_allow_html=True)
total_w = sum(gewichte_user.values()) or 1
segments = "".join(
    f'<div title="{name}: {pct:.0f}%" style="flex:{pct};background:{DIM_FARBEN[name]};height:8px;opacity:0.85"></div>'
    for name, pct in gewichte_user.items() if pct > 0
)
labels = "&nbsp;&nbsp;".join(
    f'<span style="display:inline-flex;align-items:center;gap:4px;font-size:10px;color:#718096">'
    f'<span style="width:8px;height:8px;background:{DIM_FARBEN[name]};display:inline-block;border-radius:1px"></span>'
    f'{name} <b style="color:#2d3748">{pct:.0f}%</b></span>'
    for name, pct in gewichte_user.items()
)
st.markdown(f"""
<div style="display:flex;border-radius:3px;overflow:hidden;margin-bottom:8px">{segments}</div>
<div style="display:flex;flex-wrap:wrap;gap:8px 14px;margin-bottom:4px">{labels}</div>
""", unsafe_allow_html=True)

# Personscore (immer 0–1, normiert)
gesamt_gewicht = sum(gewichte_user.values()) or 1

def berechne_personscore(row):
    total = 0.0
    for dim, col in SCORE_MAP.items():
        v = row.get(col)
        if pd.notna(v):
            total += float(v) * (gewichte_user[dim] / gesamt_gewicht)
    return total

if hat_ranking:
    df["personscore"] = df.apply(berechne_personscore, axis=1)
else:
    df["personscore"] = np.nan

df_sorted = df.sort_values("personscore", ascending=False, na_position="last").reset_index(drop=True)
df_sorted["person_rang"] = range(1, len(df_sorted) + 1)

# ---------------------------------------------------------------
# Top 3
# ---------------------------------------------------------------

st.markdown(f'<div class="us-section">Top 3 — {aktive_persona}</div>', unsafe_allow_html=True)

def fmt_score(r, col="personscore"):
    v = r.get(col)
    return f"{float(v)*100:.1f} Pkt." if pd.notna(v) else "—"

if len(df_sorted) >= 3:
    r1, r2, r3 = df_sorted.iloc[0], df_sorted.iloc[1], df_sorted.iloc[2]
    bl = lambda r: BL.get(r["bundesland"], r["bundesland"][:2].upper())
    st.markdown(f"""
    <div class="us-top3">
      <div class="us-top3-card">
        <div class="us-top3-rank">2. Platz</div>
        <div style="font-size:2rem;margin-bottom:4px">&#x1F948;</div>
        <div class="us-top3-city">{r2['name']}</div>
        <div class="us-top3-state">{bl(r2)}</div>
        <div class="us-top3-score">{fmt_score(r2)}</div>
      </div>
      <div class="us-top3-card first">
        <div class="us-top3-rank first">1. Platz</div>
        <div style="font-size:2.4rem;margin-bottom:4px">&#x1F947;</div>
        <div class="us-top3-city">{r1['name']}</div>
        <div class="us-top3-state">{bl(r1)}</div>
        <div class="us-top3-score">{fmt_score(r1)}</div>
      </div>
      <div class="us-top3-card">
        <div class="us-top3-rank">3. Platz</div>
        <div style="font-size:1.8rem;margin-bottom:4px">&#x1F949;</div>
        <div class="us-top3-city">{r3['name']}</div>
        <div class="us-top3-state">{bl(r3)}</div>
        <div class="us-top3-score">{fmt_score(r3)}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------
# Gesamtranking
# ---------------------------------------------------------------

st.markdown('<div class="us-section">Gesamtranking</div>', unsafe_allow_html=True)

def ranking_zeile(row):
    rang      = int(row.get("person_rang", 0))
    score_v   = row.get("personscore")
    score_txt = f"{float(score_v)*100:.1f}" if pd.notna(score_v) else "—"
    bars = ""
    for dim, col in SCORE_MAP.items():
        v = row.get(col)
        w = max(2, int(float(v) * 28)) if pd.notna(v) else 2
        bars += f'<div style="width:{w}px;height:10px;border-radius:1px;background:{DIM_FARBEN[dim]};opacity:0.8"></div>'
    bl_k = BL.get(row["bundesland"], row["bundesland"][:2].upper())
    return f"""<div class="us-rank-row">
        <div class="us-rank-num">{rang}</div>
        <div class="us-rank-name">{row['name']}
            <span class="us-rank-state">{bl_k}</span></div>
        <div class="us-rank-bars">{bars}</div>
        <div class="us-rank-score">{score_txt}</div>
    </div>"""

col_l, col_r = st.columns(2)
with col_l:
    for _, row in df_sorted.iloc[:10].iterrows():
        st.markdown(ranking_zeile(row), unsafe_allow_html=True)
with col_r:
    for _, row in df_sorted.iloc[10:].iterrows():
        st.markdown(ranking_zeile(row), unsafe_allow_html=True)

leg = '<div style="display:flex;gap:14px;margin-top:10px;flex-wrap:wrap;">'
for dim, farbe in DIM_FARBEN.items():
    leg += f'<span style="display:flex;align-items:center;gap:5px;font-size:10px;color:#a0aec0"><span style="width:8px;height:8px;background:{farbe};display:inline-block;border-radius:1px"></span>{dim}</span>'
leg += '</div>'
st.markdown(leg, unsafe_allow_html=True)

# ---------------------------------------------------------------
# DETAILANSICHT — alle Dimensionen untereinander
# ---------------------------------------------------------------

st.markdown('<div class="us-section">Detailansicht</div>', unsafe_allow_html=True)

stadt_auswahl = st.selectbox("Stadt wählen", df_sorted["name"].tolist(),
                              label_visibility="collapsed")
row = df_sorted[df_sorted["name"] == stadt_auswahl].iloc[0]

def val(r, col, fmt="{:.1f}", fallback="—"):
    v = r.get(col)
    return fmt.format(float(v)) if pd.notna(v) else fallback

rang_v = f"Rang {int(row['person_rang'])} von {len(staedte)}"
ps     = row.get("personscore")
ps_txt = f"{float(ps)*100:.1f} Punkte" if pd.notna(ps) else "—"

st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:baseline;
            padding:14px 0 8px 0;border-bottom:2px solid #111418;margin-bottom:6px">
  <div>
    <span style="font-family:'DM Serif Display',serif;font-size:1.35rem;color:#111418">
        {stadt_auswahl}</span>
    <span style="font-size:0.75rem;color:#a0aec0;margin-left:10px">{row.get('bundesland','')}</span>
  </div>
  <div style="text-align:right">
    <div style="font-family:'DM Serif Display',serif;font-size:1.5rem;color:#111418">{ps_txt}</div>
    <div style="font-size:0.68rem;color:#a0aec0">{rang_v} &nbsp;·&nbsp; Profil: {aktive_persona}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# Spalten-Header
st.markdown("""
<div style="display:grid;grid-template-columns:110px 1fr 220px 55px;gap:14px;
            padding:5px 0 5px 0;font-size:0.6rem;font-weight:600;text-transform:uppercase;
            letter-spacing:0.1em;color:#a0aec0;border-bottom:1px solid #edf2f7;margin-bottom:2px">
  <div>Dimension</div><div>Score (0–100)</div><div>Rohdaten</div><div style="text-align:right">Wert</div>
</div>
""", unsafe_allow_html=True)

DIMENSIONEN = [
    {
        "key": "Klima", "score_col": "score_klima",
        "roh": [
            ("Sonnenstunden/Jahr", val(row, "sonnenstunden_jahr", "{:.0f}"), "h"),
            ("Ø Temperatur",       val(row, "durchschnittstemperatur", "{:.1f}"), "°C"),
            ("Ø Niederschlag",     val(row, "niederschlag_avg", "{:.1f}"), "mm/Tag"),
        ],
    },
    {
        "key": "Wohnen", "score_col": "score_wohnen",
        "roh": [
            ("Kaltmiete", val(row, "mietpreis_kalt_qm", "{:.2f}"), "€/m²"),
        ],
    },
    {
        "key": "Wirtschaft", "score_col": "score_wirtschaft",
        "roh": [
            ("Arbeitslosenquote", val(row, "arbeitslosenquote", "{:.1f}"), "%"),
        ],
    },
    {
        "key": "Infrastruktur", "score_col": "score_infrastruktur",
        "roh": [
            ("Haltestellen", val(row, "haltestellen_anzahl", "{:.0f}"), "Stk."),
            ("POI-Dichte",   val(row, "poi_dichte", "{:.1f}"), "/km²"),
        ],
    },
    {
        "key": "Bildung", "score_col": "score_bildung",
        "roh": [
            ("Schulen",          val(row, "schulen_anzahl", "{:.0f}"), "Stk."),
            ("Kitas",            val(row, "kitas_anzahl", "{:.0f}"), "Stk."),
            ("Unis/Hochschulen", val(row, "unis_anzahl", "{:.0f}"), "Stk."),
            ("Dichte",           val(row, "bildungs_dichte", "{:.2f}"), "/km²"),
            ("je 100k EW",       val(row, "bildung_pro_100k", "{:.1f}"), "Einr."),
        ],
    },
    {
        "key": "Gesundheit", "score_col": "score_gesundheit",
        "roh": [
            ("Arztpraxen",     val(row, "aerzte_anzahl", "{:.0f}"), "Stk."),
            ("Krankenhäuser",  val(row, "krankenhaeuser_anzahl", "{:.0f}"), "Stk."),
            ("Apotheken",      val(row, "apotheken_anzahl", "{:.0f}"), "Stk."),
            ("Dichte",         val(row, "gesundheits_dichte", "{:.2f}"), "/km²"),
            ("je 100k EW",     val(row, "gesundheit_pro_100k", "{:.1f}"), "Einr."),
        ],
    },
    {
        "key": "Freizeit", "score_col": "score_freizeit",
        "roh": [
            ("Parks",      val(row, "parks_anzahl", "{:.0f}"), "Stk."),
            ("Kultur",     val(row, "kultur_anzahl", "{:.0f}"), "Einr."),
            ("Sport",      val(row, "sport_anzahl", "{:.0f}"), "Einr."),
            ("Dichte",     val(row, "freizeit_dichte", "{:.2f}"), "/km²"),
            ("je 100k EW", val(row, "freizeit_pro_100k", "{:.1f}"), "Einr."),
        ],
    },
    {
        "key": "Sicherheit", "score_col": "score_sicherheit",
        "roh": [
            ("Straftaten",    val(row, "straftaten_je_100k", "{:.0f}"), "je 100k EW"),
            ("Gewaltdelikte", val(row, "gewaltdelikte_je_100k", "{:.0f}"), "je 100k EW"),
        ],
    },
]

for dim in DIMENSIONEN:
    farbe   = DIM_FARBEN[dim["key"]]
    gewicht = gewichte_user.get(dim["key"], 0)
    s_val   = row.get(dim["score_col"])
    s_pct   = float(s_val) * 100 if pd.notna(s_val) else 0
    s_txt   = f"{s_pct:.0f}" if pd.notna(s_val) else "—"
    bar_w   = max(0, min(100, s_pct))

    roh_lines = "".join(
        f"<div><span style='color:#a0aec0'>{label}:</span> <b style='color:#2d3748'>{wert}</b> <span style='color:#cbd5e0'>{einheit}</span></div>"
        for label, wert, einheit in dim["roh"]
    )

    st.markdown(f"""
    <div class="us-dim-row">
      <div>
        <div class="us-dim-label">{dim['key']}</div>
        <div class="us-dim-gew">Gewicht: {gewicht:.0f}%</div>
      </div>
      <div>
        <div style="display:flex;justify-content:space-between;
                    font-size:0.65rem;color:#a0aec0;margin-bottom:4px">
          <span>0</span><span>50</span><span>100</span>
        </div>
        <div class="us-dim-bar-bg">
          <div class="us-dim-bar-fill" style="width:{bar_w}%;background:{farbe}"></div>
        </div>
      </div>
      <div class="us-dim-details">{roh_lines}</div>
      <div class="us-dim-score">{s_txt}</div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------
# Korrelationsanalysen — frei wählbare Achsen
# ---------------------------------------------------------------

st.markdown('<div class="us-section">Korrelationsanalysen</div>', unsafe_allow_html=True)

KORR_METRIKEN = {
    "Gesamtscore":            "gesamtscore",
    "Personscore":            "personscore",
    "Kaltmiete (EUR/m2)":    "mietpreis_kalt_qm",
    "Arbeitslosenquote (%)":  "arbeitslosenquote",
    "Sonnenstunden/Jahr":     "sonnenstunden_jahr",
    "Temperatur (C)":         "durchschnittstemperatur",
    "POI-Dichte":             "poi_dichte",
    "Straftaten je 100k":     "straftaten_je_100k",
    "Gewaltdelikte je 100k":  "gewaltdelikte_je_100k",
    "Bildungsdichte":         "bildungs_dichte",
    "Bildung je 100k EW":     "bildung_pro_100k",
    "Gesundheitsdichte":      "gesundheits_dichte",
    "Gesundheit je 100k EW":  "gesundheit_pro_100k",
    "Freizeitdichte":         "freizeit_dichte",
    "Freizeit je 100k EW":    "freizeit_pro_100k",
    "Score Klima":            "score_klima",
    "Score Wohnen":           "score_wohnen",
    "Score Wirtschaft":       "score_wirtschaft",
    "Score Infrastruktur":    "score_infrastruktur",
    "Score Bildung":          "score_bildung",
    "Score Gesundheit":       "score_gesundheit",
    "Score Freizeit":         "score_freizeit",
    "Score Sicherheit":       "score_sicherheit",
}

verfuegbare_metriken = {
    label: col for label, col in KORR_METRIKEN.items()
    if col in df.columns and df[col].notna().any()
}
metrik_labels = list(verfuegbare_metriken.keys())

korr_col1, korr_col2 = st.columns(2)
with korr_col1:
    x_idx = metrik_labels.index("Kaltmiete (EUR/m2)") if "Kaltmiete (EUR/m2)" in metrik_labels else 0
    x_label = st.selectbox("X-Achse", metrik_labels, index=x_idx, key="korr_x")
with korr_col2:
    y_idx = metrik_labels.index("Gesamtscore") if "Gesamtscore" in metrik_labels else 1
    y_label = st.selectbox("Y-Achse", metrik_labels, index=y_idx, key="korr_y")

x_col = verfuegbare_metriken[x_label]
y_col = verfuegbare_metriken[y_label]

def pearson(df_in, x, y):
    sub = df_in[[x, y]].dropna()
    if len(sub) < 4:
        return None, "Zu wenig Daten"
    r     = float(np.corrcoef(sub[x], sub[y])[0, 1])
    staerke = "stark" if abs(r) >= 0.7 else ("moderat" if abs(r) >= 0.4 else "schwach")
    richt   = "positiv" if r > 0 else "negativ"
    return round(r, 3), f"{staerke} {richt}"

col_info, col_chart = st.columns([1, 3])
with col_info:
    r_val, interp = pearson(df, x_col, y_col)
    r_txt   = f"{r_val:+.3f}" if r_val is not None else "—"
    r_color = "#111418" if r_val is None else ("#276749" if abs(r_val) >= 0.5 else "#744210")
    st.markdown(f"""
    <div class="us-corr-stat">
        <div class="us-corr-label">Pearson r</div>
        <div class="us-corr-val" style="color:{r_color}">{r_txt}</div>
        <div class="us-corr-desc">{interp}</div>
    </div>
    <div class="us-corr-stat">
        <div class="us-corr-label">Achsen</div>
        <div class="us-corr-desc">
            <b>X:</b> {x_label}<br/>
            <b>Y:</b> {y_label}
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_chart:
    if x_col != y_col and df[x_col].notna().any() and df[y_col].notna().any():
        sdf = df[["name", x_col, y_col]].dropna()
        pts = alt.Chart(sdf).mark_circle(size=80, opacity=0.85, color="#3B7EC8").encode(
            x=alt.X(f"{x_col}:Q", title=x_label),
            y=alt.Y(f"{y_col}:Q", title=y_label),
            tooltip=["name:N",
                     alt.Tooltip(f"{x_col}:Q", title=x_label, format=".2f"),
                     alt.Tooltip(f"{y_col}:Q", title=y_label, format=".2f")],
        )
        trend  = pts.transform_regression(x_col, y_col).mark_line(
            opacity=0.35, strokeDash=[5, 4], color="#3B7EC8")
        labels = pts.mark_text(dy=-10, fontSize=9.5, color="#4a5568").encode(text="name:N")
        st.altair_chart(
            (pts + trend + labels).properties(height=300)
            .configure_axis(grid=False, labelFontSize=11, labelColor="#718096",
                            titleFontSize=11, titleColor="#718096")
            .configure_view(strokeWidth=0),
            use_container_width=True
        )
    else:
        st.info("Bitte zwei verschiedene Metriken waehlen.")

# ---------------------------------------------------------------
# Städtevergleich — Radar-Diagramm (FIFA-Style)
# ---------------------------------------------------------------

st.markdown('<div class="us-section">Staedtevergleich — Radar</div>', unsafe_allow_html=True)

alle_staedte = df_sorted["name"].tolist()
vergleich_staedte = st.multiselect(
    "Staedte auswaehlen (2-5)",
    options=alle_staedte,
    default=alle_staedte[:3],
    max_selections=5,
    key="radar_staedte",
    label_visibility="collapsed",
)

if len(vergleich_staedte) < 2:
    st.info("Bitte mindestens 2 Staedte auswaehlen.")
else:
    RADAR_DIMS = list(SCORE_MAP.keys())
    RADAR_COLS = list(SCORE_MAP.values())
    STADT_FARBEN = ["#3B7EC8", "#C0392B", "#27855A", "#C8891F", "#7B52AB"]

    try:
        import plotly.graph_objects as go

        fig = go.Figure()
        for i, stadt in enumerate(vergleich_staedte):
            row_s = df_sorted[df_sorted["name"] == stadt]
            if row_s.empty:
                continue
            werte = [float(row_s.iloc[0].get(col) or 0) * 100 for col in RADAR_COLS]
            werte_closed = werte + [werte[0]]
            dims_closed  = RADAR_DIMS + [RADAR_DIMS[0]]
            farbe = STADT_FARBEN[i % len(STADT_FARBEN)]
            h = farbe.lstrip("#")
            rgb = tuple(int(h[j:j+2], 16) for j in (0, 2, 4))
            fig.add_trace(go.Scatterpolar(
                r=werte_closed,
                theta=dims_closed,
                fill="toself",
                name=stadt,
                line=dict(color=farbe, width=2),
                fillcolor=f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.12)",
                hovertemplate="%{theta}: %{r:.1f}<extra>" + stadt + "</extra>",
            ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True, range=[0, 100],
                    tickfont=dict(size=9, color="#a0aec0"),
                    gridcolor="#edf2f7", linecolor="#edf2f7",
                    tickvals=[25, 50, 75, 100],
                ),
                angularaxis=dict(
                    tickfont=dict(size=11, color="#2d3748"),
                    gridcolor="#edf2f7", linecolor="#edf2f7",
                ),
                bgcolor="white",
            ),
            showlegend=True,
            legend=dict(font=dict(size=11, color="#2d3748"),
                        bgcolor="white", bordercolor="#edf2f7", borderwidth=1),
            paper_bgcolor="white",
            margin=dict(t=40, b=40, l=60, r=60),
            height=450,
        )
        st.plotly_chart(fig, use_container_width=True)

    except ImportError:
        st.warning("Fuer das Radar-Diagramm: `pip install plotly` ausfuehren.")

# ---------------------------------------------------------------
# Karte — farbige Kreisflaechen, Umlaute korrekt
# ---------------------------------------------------------------

st.markdown('<div class="us-section">Karte</div>', unsafe_allow_html=True)

try:
    import pydeck as pdk

    karte_df = df_sorted[["name", "latitude", "longitude", "personscore"]].copy()
    karte_df = karte_df.rename(columns={"latitude": "lat", "longitude": "lon"})
    karte_df["personscore"] = karte_df["personscore"].fillna(0)

    def score_to_rgb(s):
        s = max(0.0, min(1.0, float(s)))
        r = int((1 - s) * 200 + 30)
        g = int(s * 180 + 40)
        return [r, g, 80, 160]

    karte_df["fill_color"] = karte_df["personscore"].apply(score_to_rgb)
    karte_df["radius"]     = karte_df["personscore"].apply(lambda s: int(6000 + float(s) * 8000))
    # Umlaute ersetzen — pydeck TextLayer hat Probleme mit UTF-8-Sonderzeichen
    karte_df["label"] = (karte_df["name"]
        .str.replace("ue", "ue").str.replace("oe", "oe")   # bereits ASCII
        .str.replace("\u00fc", "ue").str.replace("\u00f6", "oe").str.replace("\u00e4", "ae")
        .str.replace("\u00dc", "Ue").str.replace("\u00d6", "Oe").str.replace("\u00c4", "Ae")
        .str.replace("\u00df", "ss")
    )

    layer = pdk.Layer("ScatterplotLayer", data=karte_df,
        get_position=["lon", "lat"], get_fill_color="fill_color",
        get_radius="radius", pickable=True, stroked=True,
        get_line_color=[255, 255, 255, 80], line_width_min_pixels=1)
    text_layer = pdk.Layer("TextLayer", data=karte_df,
        get_position=["lon", "lat"], get_text="label",
        get_size=12, get_color=[30, 30, 30, 220],
        get_alignment_baseline="'bottom'")

    st.pydeck_chart(pdk.Deck(
        layers=[layer, text_layer],
        initial_view_state=pdk.ViewState(latitude=51.2, longitude=10.4, zoom=5.2),
        tooltip={"html": "<b>{name}</b><br/>Score: {personscore:.2f}",
                 "style": {"background": "white", "color": "#111418",
                           "font-size": "12px", "padding": "8px 12px"}},
        map_style="light",
    ))
    st.markdown("""
    <div style="display:flex;align-items:center;gap:14px;margin-top:6px;font-size:0.72rem;color:#718096">
        <span>Score niedrig</span>
        <div style="display:flex;gap:3px">
            <div style="width:14px;height:8px;background:rgb(230,40,80);border-radius:2px"></div>
            <div style="width:14px;height:8px;background:rgb(190,110,80);border-radius:2px"></div>
            <div style="width:14px;height:8px;background:rgb(140,150,80);border-radius:2px"></div>
            <div style="width:14px;height:8px;background:rgb(70,185,80);border-radius:2px"></div>
            <div style="width:14px;height:8px;background:rgb(30,220,100);border-radius:2px"></div>
        </div>
        <span>Score hoch &nbsp;·&nbsp; Radius proportional zum Score</span>
    </div>
    """, unsafe_allow_html=True)

except ImportError:
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
        st.markdown('<div class="us-section">Entwicklung über Zeit</div>', unsafe_allow_html=True)
        metrik_opt = {k: v for k, v in {
            "gesamtscore": "Gesamtscore", "score_klima": "Klima",
            "score_wohnen": "Wohnen", "score_wirtschaft": "Wirtschaft",
            "score_infrastruktur": "Infrastruktur", "score_bildung": "Bildung",
            "score_gesundheit": "Gesundheit", "score_freizeit": "Freizeit",
            "score_sicherheit": "Sicherheit",
        }.items() if k in zr.columns}
        metrik = st.selectbox("Metrik", list(metrik_opt.keys()),
            format_func=lambda x: metrik_opt[x], label_visibility="collapsed")
        linie = alt.Chart(zr).mark_line(point=True).encode(
            x=alt.X("jahr:O", title="Jahr"),
            y=alt.Y(f"{metrik}:Q", scale=alt.Scale(domain=[0, 1]), title="Score"),
            color=alt.Color("name:N", title="Stadt"),
            tooltip=["name:N", "jahr:O", alt.Tooltip(f"{metrik}:Q", format=".3f")],
        ).properties(height=280).configure_axis(grid=False).configure_view(strokeWidth=0)
        st.altair_chart(linie, use_container_width=True)

# ---------------------------------------------------------------
# API-Status & Footer
# ---------------------------------------------------------------

st.markdown("<div style='margin-top:2rem'></div>", unsafe_allow_html=True)
api_html = '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:1.5rem">'
for api_name, aktiv in [
    ("Open-Meteo", hat_wetter), ("Mietspiegel", hat_miete),
    ("Arbeitsagentur", hat_arbeit), ("OSM Infra", hat_infra),
    ("OSM Bildung", hat_bildung), ("OSM Gesundheit", hat_gesundheit),
    ("OSM Freizeit", hat_freizeit), ("BKA PKS", hat_sicherheit),
]:
    bg  = "#f0fff4" if aktiv else "#fff5f5"
    txt = "#276749" if aktiv else "#9b2c2c"
    dot = "●" if aktiv else "○"
    api_html += f'<div style="background:{bg};color:{txt};font-size:0.68rem;padding:3px 10px;border-radius:3px;font-weight:500">{dot} {api_name}</div>'
api_html += '</div>'
st.markdown(api_html, unsafe_allow_html=True)

st.markdown(
    "<div style='text-align:center;color:#cbd5e0;font-size:0.72rem;padding:1rem 0;"
    "border-top:1px solid #f0f2f5'>UrbanScore Deutschland &nbsp;·&nbsp; "
    "Open-Meteo · Mietspiegel · Bundesagentur für Arbeit · OpenStreetMap · BKA PKS 2023</div>",
    unsafe_allow_html=True
)
