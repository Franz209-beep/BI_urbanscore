"""
UrbanScore Deutschland — Dashboard
===================================
Streamlit-Dashboard zur Visualisierung des Städterankings.
Liest direkt aus urbanscore.db im selben Verzeichnis.
"""

import sqlite3
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------
# Seitenkonfiguration
# ---------------------------------------------------------------

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

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

h1, h2, h3 {
    font-family: 'DM Serif Display', serif !important;
}

.header-block {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
    border-radius: 16px;
    padding: 2.5rem 2.5rem 2rem;
    margin-bottom: 2rem;
    color: white;
}

.header-block h1 {
    font-size: 2.8rem;
    margin: 0 0 0.3rem 0;
    color: white !important;
    letter-spacing: -0.5px;
}

.header-block p {
    color: #a0aec0;
    font-size: 1rem;
    margin: 0;
    font-weight: 300;
}

.metric-card {
    background: white;
    border: 1px solid #e8ecf0;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    text-align: center;
}

.metric-card .metric-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #718096;
    margin-bottom: 0.4rem;
    font-weight: 500;
}

.metric-card .metric-value {
    font-size: 2rem;
    font-weight: 500;
    color: #1a1a2e;
    font-family: 'DM Serif Display', serif;
}

.metric-card .metric-sub {
    font-size: 0.8rem;
    color: #a0aec0;
    margin-top: 0.2rem;
}

.ranking-table {
    background: white;
    border: 1px solid #e8ecf0;
    border-radius: 16px;
    overflow: hidden;
}

.ranking-header {
    display: flex;
    align-items: center;
    padding: 1.2rem 1.5rem;
    border-bottom: 1px solid #e8ecf0;
}

.ranking-header h3 {
    margin: 0;
    font-size: 1.1rem;
    color: #1a1a2e;
}

.rank-row {
    display: flex;
    align-items: center;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #f7fafc;
    transition: background 0.15s;
}

.rank-row:last-child { border-bottom: none; }
.rank-row:hover { background: #f7fafc; }

.rank-number {
    font-family: 'DM Serif Display', serif;
    font-size: 1.4rem;
    color: #cbd5e0;
    width: 40px;
    flex-shrink: 0;
}

.rank-number.top1 { color: #f6ad55; }
.rank-number.top2 { color: #a0aec0; }
.rank-number.top3 { color: #c05621; }

.rank-city {
    flex: 1;
    font-size: 1rem;
    font-weight: 500;
    color: #2d3748;
}

.rank-state {
    font-size: 0.8rem;
    color: #a0aec0;
    font-weight: 300;
    margin-left: 0.5rem;
}

.rank-score {
    font-size: 0.9rem;
    font-weight: 500;
    color: #4a5568;
    width: 60px;
    text-align: right;
    flex-shrink: 0;
}

.score-bar-wrap {
    width: 120px;
    background: #edf2f7;
    border-radius: 999px;
    height: 6px;
    margin-left: 1rem;
    flex-shrink: 0;
}

.score-bar-fill {
    height: 6px;
    border-radius: 999px;
    background: linear-gradient(90deg, #0f3460, #e94560);
}

.badge-available {
    display: inline-block;
    background: #c6f6d5;
    color: #276749;
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 999px;
    font-weight: 500;
    margin-left: 0.5rem;
}

.badge-missing {
    display: inline-block;
    background: #fed7d7;
    color: #9b2c2c;
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 999px;
    font-weight: 500;
    margin-left: 0.5rem;
}

.detail-card {
    background: white;
    border: 1px solid #e8ecf0;
    border-radius: 16px;
    padding: 1.5rem;
    height: 100%;
}

.detail-card h4 {
    font-family: 'DM Serif Display', serif;
    font-size: 1rem;
    color: #1a1a2e;
    margin: 0 0 1rem 0;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid #e8ecf0;
}

.detail-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0;
    border-bottom: 1px solid #f7fafc;
    font-size: 0.88rem;
}

.detail-row:last-child { border-bottom: none; }
.detail-key { color: #718096; }
.detail-val { font-weight: 500; color: #2d3748; }
.detail-val.missing { color: #cbd5e0; font-style: italic; font-weight: 300; }

.info-box {
    background: #ebf8ff;
    border: 1px solid #bee3f8;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    font-size: 0.88rem;
    color: #2c5282;
    margin-bottom: 1.5rem;
}

.stSelectbox label { font-size: 0.85rem !important; color: #718096 !important; }
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

# ---------------------------------------------------------------
# Zeitraum-Auswahl
# ---------------------------------------------------------------

col_filter, col_info = st.columns([2, 5])

with col_filter:
    if not zeit.empty:
        zeitraum_optionen = zeit["zeitraum_label"].tolist()
        gewaehlter_zeitraum = st.selectbox("Zeitraum", zeitraum_optionen)
        gewaehlte_zeit_id = int(
            zeit[zeit["zeitraum_label"] == gewaehlter_zeitraum]["zeit_id"].values[0]
        )
    else:
        st.warning("Keine Zeiträume in der Datenbank.")
        st.stop()

# ---------------------------------------------------------------
# Daten für gewählten Zeitraum zusammenführen
# ---------------------------------------------------------------

wetter_z  = wetter[wetter["zeit_id"] == gewaehlte_zeit_id] if not wetter.empty else pd.DataFrame()
miete_z   = miete[miete["zeit_id"]   == gewaehlte_zeit_id] if not miete.empty else pd.DataFrame()
arbeit_z  = arbeit[arbeit["zeit_id"] == gewaehlte_zeit_id] if not arbeit.empty else pd.DataFrame()
infra_z   = infra[infra["zeit_id"]   == gewaehlte_zeit_id] if not infra.empty else pd.DataFrame()
ranking_z = ranking[ranking["zeit_id"] == gewaehlte_zeit_id] if not ranking.empty else pd.DataFrame()

df = staedte.copy()

for tabelle, prefix in [
    (wetter_z,  "w"),
    (miete_z,   "m"),
    (arbeit_z,  "a"),
    (infra_z,   "i"),
    (ranking_z, "r"),
]:
    if not tabelle.empty:
        df = df.merge(tabelle, on="stadt_id", how="left", suffixes=("", f"_{prefix}"))

# ---------------------------------------------------------------
# Status: welche APIs sind befüllt?
# ---------------------------------------------------------------

hat_wetter  = not wetter_z.empty
hat_miete   = not miete_z.empty
hat_arbeit  = not arbeit_z.empty
hat_infra   = not infra_z.empty
hat_ranking = not ranking_z.empty

apis_aktiv = sum([hat_wetter, hat_miete, hat_arbeit, hat_infra])

# ---------------------------------------------------------------
# Info-Box Datenstatus
# ---------------------------------------------------------------

if apis_aktiv < 4:
    fehlende = []
    if not hat_miete:  fehlende.append("ImmoScout24 (Mietdaten)")
    if not hat_arbeit: fehlende.append("Arbeitsagentur (Arbeitsmarkt)")
    if not hat_infra:  fehlende.append("Overpass/OSM (Infrastruktur)")

    st.markdown(f"""
    <div class="info-box">
        <strong>Datenstatus:</strong> {apis_aktiv} von 4 APIs aktiv.
        Noch nicht verbunden: {", ".join(fehlende)}.
        Der Gesamtscore basiert aktuell nur auf den verfügbaren Daten.
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------
# Kennzahlen-Zeile
# ---------------------------------------------------------------

m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Städte analysiert</div>
        <div class="metric-value">{len(staedte)}</div>
        <div class="metric-sub">deutsche Großstädte</div>
    </div>""", unsafe_allow_html=True)

with m2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">APIs aktiv</div>
        <div class="metric-value">{apis_aktiv} / 4</div>
        <div class="metric-sub">Datenquellen verbunden</div>
    </div>""", unsafe_allow_html=True)

with m3:
    if hat_wetter and "sonnenstunden_jahr" in df.columns:
        best_sonne = df.loc[df["sonnenstunden_jahr"].idxmax(), "name"] if df["sonnenstunden_jahr"].notna().any() else "—"
    else:
        best_sonne = "—"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Meiste Sonnenstunden</div>
        <div class="metric-value" style="font-size:1.4rem">{best_sonne}</div>
        <div class="metric-sub">im Zeitraum {gewaehlter_zeitraum}</div>
    </div>""", unsafe_allow_html=True)

with m4:
    if hat_ranking and "rang" in df.columns:
        top_stadt = df.loc[df["rang"] == 1, "name"].values
        top_name = top_stadt[0] if len(top_stadt) > 0 else "—"
    else:
        top_name = "—"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Aktueller Spitzenreiter</div>
        <div class="metric-value" style="font-size:1.4rem">{top_name}</div>
        <div class="metric-sub">höchster Gesamtscore</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<div style='margin-top: 1.5rem'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Ranking-Tabelle
# ---------------------------------------------------------------

linke_col, rechte_col = st.columns([3, 2])

with linke_col:
    st.markdown('<div class="ranking-table">', unsafe_allow_html=True)
    st.markdown("""
    <div class="ranking-header">
        <h3>Städteranking</h3>
    </div>""", unsafe_allow_html=True)

    if hat_ranking and "rang" in df.columns:
        df_sorted = df.sort_values("rang")
    elif hat_wetter and "sonnenstunden_jahr" in df.columns:
        df_sorted = df.sort_values("sonnenstunden_jahr", ascending=False)
        df_sorted["rang"] = range(1, len(df_sorted) + 1)
    else:
        df_sorted = df.copy()
        df_sorted["rang"] = range(1, len(df_sorted) + 1)

    for _, row in df_sorted.iterrows():
        rang = int(row.get("rang", 0)) if pd.notna(row.get("rang")) else "—"
        rang_class = ""
        if rang == 1: rang_class = "top1"
        elif rang == 2: rang_class = "top2"
        elif rang == 3: rang_class = "top3"

        score = row.get("gesamtscore")
        score_pct = int(float(score) * 100) if pd.notna(score) else 0
        score_text = f"{score_pct}%" if pd.notna(score) else "—"

        st.markdown(f"""
        <div class="rank-row">
            <div class="rank-number {rang_class}">{rang}</div>
            <div class="rank-city">
                {row['name']}
                <span class="rank-state">{row['bundesland']}</span>
            </div>
            <div class="score-bar-wrap">
                <div class="score-bar-fill" style="width: {score_pct}%"></div>
            </div>
            <div class="rank-score">{score_text}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Detail-Karten rechts
# ---------------------------------------------------------------

with rechte_col:

    # Wetterdaten
    st.markdown('<div class="detail-card">', unsafe_allow_html=True)
    badge_w = '<span class="badge-available">aktiv</span>' if hat_wetter else '<span class="badge-missing">fehlt</span>'
    st.markdown(f'<h4>Klima {badge_w}</h4>', unsafe_allow_html=True)

    if hat_wetter and "sonnenstunden_jahr" in df.columns:
        for _, row in df_sorted.iterrows():
            sonne = f"{row['sonnenstunden_jahr']:.0f} h" if pd.notna(row.get("sonnenstunden_jahr")) else "—"
            temp  = f"{row['durchschnittstemperatur']:.1f} °C" if pd.notna(row.get("durchschnittstemperatur")) else "—"
            st.markdown(f"""
            <div class="detail-row">
                <span class="detail-key">{row['name']}</span>
                <span class="detail-val">{sonne} · {temp}</span>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div class="detail-row"><span class="detail-val missing">Noch keine Daten</span></div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='margin-top: 1rem'></div>", unsafe_allow_html=True)

    # Datenstatus aller APIs
    st.markdown('<div class="detail-card">', unsafe_allow_html=True)
    st.markdown('<h4>API-Status</h4>', unsafe_allow_html=True)

    apis = [
        ("Open-Meteo (Klima)",          hat_wetter),
        ("ImmoScout24 (Wohnen)",         hat_miete),
        ("Arbeitsagentur (Wirtschaft)",  hat_arbeit),
        ("Overpass/OSM (Infrastruktur)", hat_infra),
    ]
    for api_name, aktiv in apis:
        badge = '<span class="badge-available">aktiv</span>' if aktiv else '<span class="badge-missing">ausstehend</span>'
        st.markdown(f"""
        <div class="detail-row">
            <span class="detail-key">{api_name}</span>
            {badge}
        </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Footer
# ---------------------------------------------------------------

st.markdown("<div style='margin-top: 2rem'></div>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; color: #a0aec0; font-size: 0.78rem; padding: 1rem 0'>
    UrbanScore Deutschland · Datenquellen: Open-Meteo, ImmoScout24, Bundesagentur für Arbeit, OpenStreetMap
</div>
""", unsafe_allow_html=True)
