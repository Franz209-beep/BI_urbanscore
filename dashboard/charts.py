"""
dashboard/charts.py — Visualisierungen
=======================================
Kapselt alle Chart-Rendering-Funktionen. Jede Funktion nimmt
aufbereitete DataFrames entgegen und rendert direkt via Streamlit.
Plotly, Altair und PyDeck werden nur bei Bedarf importiert.
"""

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt

import config


# ---------------------------------------------------------------------------
# Korrelationsanalyse
# ---------------------------------------------------------------------------

# Alle verfügbaren Metriken für die Achsenauswahl
KORR_METRIKEN: dict[str, str] = {
    "Gesamtscore":           "gesamtscore",
    "Personscore":           "personscore",
    "Kaltmiete (EUR/m²)":   "mietpreis_kalt_qm",
    "Arbeitslosenquote (%)": "arbeitslosenquote",
    "Sonnenstunden/Jahr":    "sonnenstunden_jahr",
    "Temperatur (°C)":       "durchschnittstemperatur",
    "POI-Dichte":            "poi_dichte",
    "Straftaten je 100k":    "straftaten_je_100k",
    "Gewaltdelikte je 100k": "gewaltdelikte_je_100k",
    "Bildungsdichte":        "bildungs_dichte",
    "Bildung je 100k EW":    "bildung_pro_100k",
    "Gesundheitsdichte":     "gesundheits_dichte",
    "Gesundheit je 100k EW": "gesundheit_pro_100k",
    "Freizeitdichte":        "freizeit_dichte",
    "Freizeit je 100k EW":   "freizeit_pro_100k",
    **{f"Score {k}": v for k, v in config.SCORE_MAP.items()},
}


def _pearson(df: pd.DataFrame, x_col: str, y_col: str,
             x_label: str, y_label: str) -> tuple[float | None, str, str]:
    """Berechnet Pearson-r und gibt (r, Stärke+Richtung, Interpretationssatz) zurück."""
    sub = df[[x_col, y_col]].dropna()
    if len(sub) < 4:
        return None, "Zu wenig Daten", ""

    r       = float(np.corrcoef(sub[x_col], sub[y_col])[0, 1])
    staerke = "stark" if abs(r) >= 0.7 else ("moderat" if abs(r) >= 0.4 else "schwach")
    richt   = "positiv" if r > 0 else "negativ"

    if abs(r) >= 0.7 and r > 0:
        satz = f"Starker positiver Zusammenhang: Steigt {x_label}, steigt tendenziell auch {y_label}."
    elif abs(r) >= 0.7:
        satz = f"Starker negativer Zusammenhang: Steigt {x_label}, sinkt tendenziell {y_label}."
    elif abs(r) >= 0.4 and r > 0:
        satz = "Moderater positiver Trend erkennbar, aber mit deutlicher Streuung."
    elif abs(r) >= 0.4:
        satz = "Moderater negativer Trend erkennbar, aber mit deutlicher Streuung."
    else:
        satz = "Kein klarer linearer Zusammenhang zwischen den beiden Variablen."

    return round(r, 3), f"{staerke} {richt}", satz


def render_korrelation(df: pd.DataFrame) -> None:
    """Interaktive Korrelationsanalyse mit frei wählbaren Achsen."""
    # Nur Spalten anbieten die tatsächlich Daten enthalten
    verfuegbar = {
        label: col for label, col in KORR_METRIKEN.items()
        if col in df.columns and df[col].notna().any()
    }
    labels = list(verfuegbar.keys())

    col1, col2 = st.columns(2)
    with col1:
        x_def   = labels.index("Kaltmiete (EUR/m²)") if "Kaltmiete (EUR/m²)" in labels else 0
        x_label = st.selectbox("X-Achse", labels, index=x_def, key="korr_x")
    with col2:
        y_def   = labels.index("Gesamtscore") if "Gesamtscore" in labels else 1
        y_label = st.selectbox("Y-Achse", labels, index=y_def, key="korr_y")

    x_col = verfuegbar[x_label]
    y_col = verfuegbar[y_label]
    r_val, interp, satz = _pearson(df, x_col, y_col, x_label, y_label)

    col_info, col_chart = st.columns([1, 3])
    with col_info:
        r_txt   = f"{r_val:+.3f}" if r_val is not None else "—"
        r_color = "#111418" if r_val is None else ("#276749" if abs(r_val) >= 0.5 else "#744210")
        st.markdown(f"""
        <div class="us-corr-stat">
            <div class="us-corr-label">Pearson r</div>
            <div class="us-corr-val" style="color:{r_color}">{r_txt}</div>
            <div class="us-corr-desc">{interp}</div>
        </div>
        <div class="us-corr-stat">
            <div class="us-corr-label">Interpretation</div>
            <div class="us-corr-desc">{satz}</div>
        </div>
        <div class="us-corr-stat">
            <div class="us-corr-label">Achsen</div>
            <div class="us-corr-desc"><b>X:</b> {x_label}<br/><b>Y:</b> {y_label}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_chart:
        if x_col != y_col and df[x_col].notna().any() and df[y_col].notna().any():
            sdf  = df[["name", x_col, y_col]].dropna()
            pts  = alt.Chart(sdf).mark_circle(size=80, opacity=0.85, color="#3B7EC8").encode(
                x=alt.X(f"{x_col}:Q", title=x_label),
                y=alt.Y(f"{y_col}:Q", title=y_label),
                tooltip=["name:N",
                         alt.Tooltip(f"{x_col}:Q", title=x_label, format=".2f"),
                         alt.Tooltip(f"{y_col}:Q", title=y_label, format=".2f")],
            )
            trend  = pts.transform_regression(x_col, y_col).mark_line(
                opacity=0.35, strokeDash=[5, 4], color="#3B7EC8")
            labels_chart = pts.mark_text(dy=-10, fontSize=9.5, color="#4a5568").encode(
                text="name:N"
            )
            st.altair_chart(
                (pts + trend + labels_chart)
                .properties(height=300)
                .configure_axis(grid=False, labelFontSize=11, labelColor="#718096",
                                titleFontSize=11, titleColor="#718096")
                .configure_view(strokeWidth=0),
                use_container_width=True,
            )
        else:
            st.info("Bitte zwei verschiedene Metriken wählen.")


# ---------------------------------------------------------------------------
# Radar-Diagramm (Städtevergleich)
# ---------------------------------------------------------------------------

STADT_FARBEN = ["#3B7EC8", "#C0392B", "#27855A", "#C8891F", "#7B52AB"]


def render_radar(df_sorted: pd.DataFrame) -> None:
    """FIFA-Style Radar für den Vergleich von 2–5 Städten."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.warning("Für das Radar-Diagramm: `pip install plotly` ausführen.")
        return

    alle = df_sorted["name"].tolist()
    auswahl = st.multiselect(
        "Städte auswählen (2–5)",
        options=alle,
        default=alle[:3],
        max_selections=5,
        key="radar_staedte",
        label_visibility="collapsed",
    )
    if len(auswahl) < 2:
        st.info("Bitte mindestens 2 Städte auswählen.")
        return

    dims   = list(config.SCORE_MAP.keys())
    cols   = list(config.SCORE_MAP.values())
    fig    = go.Figure()

    for i, stadt in enumerate(auswahl):
        row_s = df_sorted[df_sorted["name"] == stadt]
        if row_s.empty:
            continue
        werte        = [float(row_s.iloc[0].get(c) or 0) * 100 for c in cols]
        werte_closed = werte + [werte[0]]
        dims_closed  = dims  + [dims[0]]
        farbe        = STADT_FARBEN[i % len(STADT_FARBEN)]
        h            = farbe.lstrip("#")
        rgb          = tuple(int(h[j:j+2], 16) for j in (0, 2, 4))

        fig.add_trace(go.Scatterpolar(
            r=werte_closed, theta=dims_closed, fill="toself", name=stadt,
            line=dict(color=farbe, width=2),
            fillcolor=f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.12)",
            hovertemplate="%{theta}: %{r:.1f}<extra>" + stadt + "</extra>",
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100],
                            tickfont=dict(size=9, color="#a0aec0"),
                            gridcolor="#edf2f7", linecolor="#edf2f7",
                            tickvals=[25, 50, 75, 100]),
            angularaxis=dict(tickfont=dict(size=11, color="#2d3748"),
                             gridcolor="#edf2f7", linecolor="#edf2f7"),
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


# ---------------------------------------------------------------------------
# Karte
# ---------------------------------------------------------------------------

def render_karte(df_sorted: pd.DataFrame) -> None:
    """Interaktive PyDeck-Karte mit farbigen Score-Kreisen."""
    karte_df = df_sorted[["name", "latitude", "longitude", "personscore"]].copy()
    karte_df = karte_df.rename(columns={"latitude": "lat", "longitude": "lon"})
    karte_df["personscore"] = karte_df["personscore"].fillna(0)

    def score_to_rgb(s: float) -> list[int]:
        s = max(0.0, min(1.0, float(s)))
        return [int((1 - s) * 200 + 30), int(s * 180 + 40), 80, 160]

    # PyDeck TextLayer hat Probleme mit UTF-8-Umlauten → ASCII-Ersatz
    def ascii_label(name: str) -> str:
        return (name
            .replace("ü", "ue").replace("ö", "oe").replace("ä", "ae")
            .replace("Ü", "Ue").replace("Ö", "Oe").replace("Ä", "Ae")
            .replace("ß", "ss"))

    karte_df["fill_color"] = karte_df["personscore"].apply(score_to_rgb)
    karte_df["radius"]     = karte_df["personscore"].apply(lambda s: int(6000 + float(s) * 8000))
    karte_df["label"]      = karte_df["name"].apply(ascii_label)

    try:
        import pydeck as pdk

        layer = pdk.Layer(
            "ScatterplotLayer", data=karte_df,
            get_position=["lon", "lat"], get_fill_color="fill_color",
            get_radius="radius", pickable=True, stroked=True,
            get_line_color=[255, 255, 255, 80], line_width_min_pixels=1,
        )
        text_layer = pdk.Layer(
            "TextLayer", data=karte_df,
            get_position=["lon", "lat"], get_text="label",
            get_size=12, get_color=[30, 30, 30, 220],
            get_alignment_baseline="'bottom'",
        )
        st.pydeck_chart(pdk.Deck(
            layers=[layer, text_layer],
            initial_view_state=pdk.ViewState(latitude=51.2, longitude=10.4, zoom=5.2),
            tooltip={"html": "<b>{name}</b><br/>Score: {personscore:.2f}",
                     "style": {"background": "white", "color": "#111418",
                               "font-size": "12px", "padding": "8px 12px"}},
            map_style="light",
        ))

    except ImportError:
        # Fallback: einfache Streamlit-Karte ohne Farbkodierung
        st.map(karte_df, latitude="lat", longitude="lon", size=40000, zoom=5)

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


# ---------------------------------------------------------------------------
# Zeitreihe
# ---------------------------------------------------------------------------

def render_zeitreihe(ranking: pd.DataFrame, staedte: pd.DataFrame, zeit: pd.DataFrame) -> None:
    """Liniendiagramm der Score-Entwicklung über mehrere Jahre."""
    zr = (ranking
          .merge(staedte[["stadt_id", "name"]], on="stadt_id")
          .merge(zeit[["zeit_id", "jahr"]], on="zeit_id"))

    if len(zr["jahr"].unique()) <= 1:
        return  # Zeitreihe nur anzeigen wenn mehrere Jahre vorhanden

    metrik_opt = {
        col: label for col, label in {
            "gesamtscore":       "Gesamtscore",
            "score_klima":       "Klima",
            "score_wohnen":      "Wohnen",
            "score_wirtschaft":  "Wirtschaft",
            "score_infrastruktur": "Infrastruktur",
            "score_bildung":     "Bildung",
            "score_gesundheit":  "Gesundheit",
            "score_freizeit":    "Freizeit",
            "score_sicherheit":  "Sicherheit",
        }.items() if col in zr.columns
    }

    metrik = st.selectbox(
        "Metrik", list(metrik_opt.keys()),
        format_func=lambda x: metrik_opt[x],
        label_visibility="collapsed",
    )
    linie = (
        alt.Chart(zr)
        .mark_line(point=True)
        .encode(
            x=alt.X("jahr:O", title="Jahr"),
            y=alt.Y(f"{metrik}:Q", scale=alt.Scale(domain=[0, 1]), title="Score"),
            color=alt.Color("name:N", title="Stadt"),
            tooltip=["name:N", "jahr:O", alt.Tooltip(f"{metrik}:Q", format=".3f")],
        )
        .properties(height=280)
        .configure_axis(grid=False)
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(linie, use_container_width=True)
