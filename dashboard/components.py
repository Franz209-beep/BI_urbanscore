"""
dashboard/components.py — Wiederverwendbare UI-Bausteine
=========================================================
Jede Funktion rendert einen abgeschlossenen UI-Abschnitt via
st.markdown(). Die Trennung von app.py hält den Einstiegspunkt
lesbar und macht einzelne Komponenten isoliert testbar.
"""

import pandas as pd
import streamlit as st

import config


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

def render_styles() -> None:
    """Lädt das globale CSS-Stylesheet (einmalig beim App-Start aufrufen)."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500&display=swap');

    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

    .us-header { background:#111418; border-radius:4px; padding:2.2rem 2.5rem 2rem; margin-bottom:1.8rem; }
    .us-header h1 { font-family:'DM Serif Display',serif; font-size:2rem; font-weight:400;
                    color:#f0f2f5; margin:0 0 0.25rem 0; letter-spacing:-0.01em; }
    .us-header p { color:#4a5568; font-size:0.82rem; margin:0; }

    .us-section { font-size:0.65rem; font-weight:600; text-transform:uppercase; letter-spacing:0.12em;
                  color:#a0aec0; margin:2rem 0 0.9rem 0; padding-bottom:0.5rem;
                  border-bottom:1px solid #f0f2f5; }

    .us-top3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:1px;
               background:#edf2f7; border:1px solid #edf2f7; border-radius:4px;
               overflow:hidden; margin:0.5rem 0 1.5rem 0; }
    .us-top3-card { background:white; padding:1.4rem 1.2rem; text-align:center; }
    .us-top3-card.first { background:#fafafa; }
    .us-top3-rank { font-size:0.6rem; font-weight:600; letter-spacing:0.12em;
                    text-transform:uppercase; color:#a0aec0; margin-bottom:0.5rem; }
    .us-top3-rank.first { color:#b7791f; }
    .us-top3-city { font-family:'DM Serif Display',serif; font-size:1.1rem; font-weight:400; color:#111418; }
    .us-top3-card.first .us-top3-city { font-size:1.25rem; }
    .us-top3-state { font-size:0.72rem; color:#a0aec0; margin-top:3px; }
    .us-top3-score { font-size:0.78rem; color:#718096; margin-top:8px; font-weight:500; }

    .us-rank-row { display:flex; align-items:center; padding:7px 0;
                   border-bottom:1px solid #f7f8fa; font-size:0.82rem; }
    .us-rank-num { width:28px; color:#cbd5e0; font-size:0.75rem; font-variant-numeric:tabular-nums; }
    .us-rank-name { flex:1; font-weight:500; color:#111418; }
    .us-rank-state { font-size:0.68rem; color:#cbd5e0; margin-left:5px; font-weight:400; }
    .us-rank-bars { display:flex; align-items:center; gap:2px; margin:0 10px; }
    .us-rank-score { width:38px; text-align:right; font-weight:500; color:#111418;
                     font-size:0.8rem; font-variant-numeric:tabular-nums; }

    .us-dim-row { display:grid; grid-template-columns:110px 1fr 220px 55px;
                  align-items:center; gap:14px; padding:11px 0; border-bottom:1px solid #f7f8fa; }
    .us-dim-label { font-size:0.75rem; font-weight:600; color:#2d3748; }
    .us-dim-gew { font-size:0.65rem; color:#a0aec0; margin-top:2px; }
    .us-dim-bar-bg { background:#f0f2f5; border-radius:2px; height:7px; }
    .us-dim-bar-fill { height:7px; border-radius:2px; }
    .us-dim-details { font-size:0.69rem; color:#718096; line-height:1.7; }
    .us-dim-score { font-family:'DM Serif Display',serif; font-size:1.05rem;
                    font-weight:400; color:#111418; text-align:right; }

    .us-corr-stat { background:#fafafa; border:1px solid #edf2f7; border-radius:4px;
                    padding:1.2rem; margin-bottom:0.8rem; }
    .us-corr-label { font-size:0.65rem; font-weight:600; text-transform:uppercase;
                     letter-spacing:0.1em; color:#a0aec0; margin-bottom:6px; }
    .us-corr-val { font-family:'DM Serif Display',serif; font-size:1.6rem; font-weight:400; }
    .us-corr-desc { font-size:0.75rem; color:#718096; margin-top:4px; line-height:1.5; }
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Header & Abschnitts-Trenner
# ---------------------------------------------------------------------------

def render_header(letzter_lauf: str) -> None:
    st.markdown(f"""
    <div class="us-header">
      <h1>UrbanScore Deutschland</h1>
      <p>Multidimensionales Städteranking &nbsp;·&nbsp;
         Klima · Wohnen · Wirtschaft · Infrastruktur · Bildung · Gesundheit · Freizeit · Sicherheit
         &nbsp;·&nbsp; Stand: {letzter_lauf}</p>
    </div>
    """, unsafe_allow_html=True)


def render_section(titel: str) -> None:
    st.markdown(f'<div class="us-section">{titel}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Profil / Persona-Auswahl
# ---------------------------------------------------------------------------

def render_gewichtsbalken(gewichte: dict[str, float]) -> None:
    """Horizontaler gestapelter Balken mit Legende für die aktiven Gewichte."""
    segments = "".join(
        f'<div title="{name}: {pct:.0f}%" '
        f'style="flex:{pct};background:{config.DIM_FARBEN[name]};height:8px;opacity:0.85"></div>'
        for name, pct in gewichte.items() if pct > 0
    )
    labels = "&nbsp;&nbsp;".join(
        f'<span style="display:inline-flex;align-items:center;gap:4px;font-size:10px;color:#718096">'
        f'<span style="width:8px;height:8px;background:{config.DIM_FARBEN[name]};'
        f'display:inline-block;border-radius:1px"></span>'
        f'{name} <b style="color:#2d3748">{pct:.0f}%</b></span>'
        for name, pct in gewichte.items()
    )
    st.markdown(f"""
    <div style="display:flex;border-radius:3px;overflow:hidden;margin-bottom:8px">{segments}</div>
    <div style="display:flex;flex-wrap:wrap;gap:8px 14px;margin-bottom:4px">{labels}</div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Top-3-Podest
# ---------------------------------------------------------------------------

def render_top3(df_sorted: pd.DataFrame) -> None:
    """Rendert das Podest mit den drei bestplatzierten Städten."""
    if len(df_sorted) < 3:
        return

    def bl(row: pd.Series) -> str:
        return config.BUNDESLAND_KUERZEL.get(row["bundesland"], row["bundesland"][:2].upper())

    def score_txt(row: pd.Series) -> str:
        v = row.get("personscore")
        return f"{float(v) * 100:.1f} Pkt." if pd.notna(v) else "—"

    r1, r2, r3 = df_sorted.iloc[0], df_sorted.iloc[1], df_sorted.iloc[2]
    st.markdown(f"""
    <div class="us-top3">
      <div class="us-top3-card">
        <div class="us-top3-rank">2. Platz</div>
        <div style="font-size:2rem;margin-bottom:4px">&#x1F948;</div>
        <div class="us-top3-city">{r2['name']}</div>
        <div class="us-top3-state">{bl(r2)}</div>
        <div class="us-top3-score">{score_txt(r2)}</div>
      </div>
      <div class="us-top3-card first">
        <div class="us-top3-rank first">1. Platz</div>
        <div style="font-size:2.4rem;margin-bottom:4px">&#x1F947;</div>
        <div class="us-top3-city">{r1['name']}</div>
        <div class="us-top3-state">{bl(r1)}</div>
        <div class="us-top3-score">{score_txt(r1)}</div>
      </div>
      <div class="us-top3-card">
        <div class="us-top3-rank">3. Platz</div>
        <div style="font-size:1.8rem;margin-bottom:4px">&#x1F949;</div>
        <div class="us-top3-city">{r3['name']}</div>
        <div class="us-top3-state">{bl(r3)}</div>
        <div class="us-top3-score">{score_txt(r3)}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Gesamtranking-Zeile
# ---------------------------------------------------------------------------

def render_ranking_zeile(row: pd.Series) -> None:
    """Rendert eine einzelne Zeile im Gesamtranking."""
    rang      = int(row.get("person_rang", 0))
    score_v   = row.get("personscore")
    score_txt = f"{float(score_v) * 100:.1f}" if pd.notna(score_v) else "—"

    bars = "".join(
        f'<div style="width:{max(2, int(float(row.get(col) or 0) * 28))}px;'
        f'height:10px;border-radius:1px;background:{farbe};opacity:0.8"></div>'
        for farbe, col in zip(
            config.DIM_FARBEN.values(), config.SCORE_MAP.values()
        )
    )
    bl = config.BUNDESLAND_KUERZEL.get(row["bundesland"], row["bundesland"][:2].upper())

    st.markdown(f"""
    <div class="us-rank-row">
      <div class="us-rank-num">{rang}</div>
      <div class="us-rank-name">{row['name']}
        <span class="us-rank-state">{bl}</span></div>
      <div class="us-rank-bars">{bars}</div>
      <div class="us-rank-score">{score_txt}</div>
    </div>
    """, unsafe_allow_html=True)


def render_ranking_legende() -> None:
    """Farbige Legende unterhalb des Rankings."""
    items = "".join(
        f'<span style="display:flex;align-items:center;gap:5px;font-size:10px;color:#a0aec0">'
        f'<span style="width:8px;height:8px;background:{farbe};display:inline-block;'
        f'border-radius:1px"></span>{dim}</span>'
        for dim, farbe in config.DIM_FARBEN.items()
    )
    st.markdown(
        f'<div style="display:flex;gap:14px;margin-top:10px;flex-wrap:wrap;">{items}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Detailansicht – Dimensionen
# ---------------------------------------------------------------------------

# Konfiguration der Detailansicht:
# Jeder Eintrag enthält den Dimensionsschlüssel, den Score-Spaltennamen
# und eine Liste von (Anzeigelabel, DB-Spalte, Formatstring, Einheit).
DETAIL_DIMENSIONEN = [
    {
        "key": "Klima", "score_col": "score_klima",
        "roh": [
            ("Sonnenstunden/Jahr", "sonnenstunden_jahr",      "{:.0f}", "h"),
            ("Ø Temperatur",       "durchschnittstemperatur", "{:.1f}", "°C"),
            ("Ø Niederschlag",     "niederschlag_avg",        "{:.1f}", "mm/Tag"),
        ],
    },
    {
        "key": "Wohnen", "score_col": "score_wohnen",
        "roh": [("Kaltmiete", "mietpreis_kalt_qm", "{:.2f}", "€/m²")],
    },
    {
        "key": "Wirtschaft", "score_col": "score_wirtschaft",
        "roh": [("Arbeitslosenquote", "arbeitslosenquote", "{:.1f}", "%")],
    },
    {
        "key": "Infrastruktur", "score_col": "score_infrastruktur",
        "roh": [
            ("Haltestellen", "haltestellen_anzahl", "{:.0f}", "Stk."),
            ("POI-Dichte",   "poi_dichte",          "{:.1f}", "/km²"),
        ],
    },
    {
        "key": "Bildung", "score_col": "score_bildung",
        "roh": [
            ("Schulen",          "schulen_anzahl",    "{:.0f}", "Stk."),
            ("Kitas",            "kitas_anzahl",      "{:.0f}", "Stk."),
            ("Unis/Hochschulen", "unis_anzahl",       "{:.0f}", "Stk."),
            ("Dichte",           "bildungs_dichte",   "{:.2f}", "/km²"),
            ("je 100k EW",       "bildung_pro_100k",  "{:.1f}", "Einr."),
        ],
    },
    {
        "key": "Gesundheit", "score_col": "score_gesundheit",
        "roh": [
            ("Arztpraxen",    "aerzte_anzahl",         "{:.0f}", "Stk."),
            ("Krankenhäuser", "krankenhaeuser_anzahl", "{:.0f}", "Stk."),
            ("Apotheken",     "apotheken_anzahl",      "{:.0f}", "Stk."),
            ("Dichte",        "gesundheits_dichte",    "{:.2f}", "/km²"),
            ("je 100k EW",    "gesundheit_pro_100k",   "{:.1f}", "Einr."),
        ],
    },
    {
        "key": "Freizeit", "score_col": "score_freizeit",
        "roh": [
            ("Parks",      "parks_anzahl",      "{:.0f}", "Stk."),
            ("Kultur",     "kultur_anzahl",     "{:.0f}", "Einr."),
            ("Sport",      "sport_anzahl",      "{:.0f}", "Einr."),
            ("Dichte",     "freizeit_dichte",   "{:.2f}", "/km²"),
            ("je 100k EW", "freizeit_pro_100k", "{:.1f}", "Einr."),
        ],
    },
    {
        "key": "Sicherheit", "score_col": "score_sicherheit",
        "roh": [
            ("Straftaten",    "straftaten_je_100k",    "{:.0f}", "je 100k EW"),
            ("Gewaltdelikte", "gewaltdelikte_je_100k", "{:.0f}", "je 100k EW"),
        ],
    },
]


def _fmt(row: pd.Series, col: str, fmt: str) -> str:
    """Formatiert einen Spaltenwert oder gibt '—' zurück."""
    v = row.get(col)
    return fmt.format(float(v)) if pd.notna(v) else "—"


def render_detail_header(row: pd.Series, aktive_persona: str, n_staedte: int) -> None:
    """Kopfzeile der Detailansicht mit Stadtname, Score und Rang."""
    ps     = row.get("personscore")
    ps_txt = f"{float(ps) * 100:.1f} Punkte" if pd.notna(ps) else "—"
    rang   = f"Rang {int(row['person_rang'])} von {n_staedte}"

    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:baseline;
                padding:14px 0 8px 0;border-bottom:2px solid #111418;margin-bottom:6px">
      <div>
        <span style="font-family:'DM Serif Display',serif;font-size:1.35rem;color:#111418">
            {row['name']}</span>
        <span style="font-size:0.75rem;color:#a0aec0;margin-left:10px">{row.get('bundesland','')}</span>
      </div>
      <div style="text-align:right">
        <div style="font-family:'DM Serif Display',serif;font-size:1.5rem;color:#111418">{ps_txt}</div>
        <div style="font-size:0.68rem;color:#a0aec0">{rang} &nbsp;·&nbsp; Profil: {aktive_persona}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_detail_dimension(row: pd.Series, dim: dict, gewicht: float) -> None:
    """Rendert eine einzelne Dimensions-Zeile in der Detailansicht."""
    farbe  = config.DIM_FARBEN[dim["key"]]
    s_val  = row.get(dim["score_col"])
    s_pct  = float(s_val) * 100 if pd.notna(s_val) else 0
    s_txt  = f"{s_pct:.0f}" if pd.notna(s_val) else "—"

    roh_lines = "".join(
        f"<div><span style='color:#a0aec0'>{label}:</span> "
        f"<b style='color:#2d3748'>{_fmt(row, col, fmt)}</b> "
        f"<span style='color:#cbd5e0'>{einheit}</span></div>"
        for label, col, fmt, einheit in dim["roh"]
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
          <div class="us-dim-bar-fill" style="width:{max(0, min(100, s_pct))}%;background:{farbe}"></div>
        </div>
      </div>
      <div class="us-dim-details">{roh_lines}</div>
      <div class="us-dim-score">{s_txt}</div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# API-Status & Footer
# ---------------------------------------------------------------------------

def render_api_status(hat: dict[str, bool]) -> None:
    """Zeigt farbige Status-Badges für jede Datenquelle."""
    badges = "".join(
        f'<div style="background:{"#f0fff4" if aktiv else "#fff5f5"};'
        f'color:{"#276749" if aktiv else "#9b2c2c"};'
        f'font-size:0.68rem;padding:3px 10px;border-radius:3px;font-weight:500">'
        f'{"●" if aktiv else "○"} {name}</div>'
        for name, aktiv in hat.items()
    )
    st.markdown(
        f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:1.5rem">{badges}</div>',
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        "<div style='text-align:center;color:#cbd5e0;font-size:0.72rem;"
        "padding:1rem 0;border-top:1px solid #f0f2f5'>"
        "UrbanScore Deutschland &nbsp;·&nbsp; "
        "Open-Meteo · Mietspiegel · Bundesagentur für Arbeit · OpenStreetMap · BKA PKS 2023"
        "</div>",
        unsafe_allow_html=True,
    )
