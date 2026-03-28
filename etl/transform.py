"""
etl/transform.py — Score-Berechnung und Ranking
================================================
Liest alle Rohdaten für einen Zeitraum aus der DB, normiert sie mit
MinMaxScaler auf [0, 1] und schreibt die gewichteten Scores zurück.

Score-Philosophie:
  - score_hoch:      höherer Rohwert = besser (z.B. Sonnenstunden)
  - score_niedrig:   niedrigerer Rohwert = besser (z.B. Miete, Arbeitslosigkeit)
  - score_kombiniert: Mittelwert aus Dichte-Score und Pro-Kopf-Score,
                      damit weder Stadtgröße noch -fläche bevorzugt wird
"""

import sqlite3

import pandas as pd
from sklearn.preprocessing import MinMaxScaler

import config


def berechne_ranking(conn: sqlite3.Connection, zeit_id: int) -> None:
    """Berechnet und speichert alle Dimension-Scores und den Gesamt-Score."""

    df = pd.read_sql_query("""
        SELECT s.stadt_id, s.name,
            w.sonnenstunden_jahr,
            m.mietpreis_kalt_qm,
            a.arbeitslosenquote,
            i.poi_dichte,
            b.bildungs_dichte,    b.bildung_pro_100k,
            g.gesundheits_dichte, g.gesundheit_pro_100k,
            f.freizeit_dichte,    f.freizeit_pro_100k,
            si.straftaten_je_100k
        FROM stadt s
        LEFT JOIN wetterdaten       w  ON w.stadt_id  = s.stadt_id AND w.zeit_id  = ?
        LEFT JOIN mietdaten         m  ON m.stadt_id  = s.stadt_id AND m.zeit_id  = ?
        LEFT JOIN arbeitsmarktdaten a  ON a.stadt_id  = s.stadt_id AND a.zeit_id  = ?
        LEFT JOIN infrastruktur     i  ON i.stadt_id  = s.stadt_id AND i.zeit_id  = ?
        LEFT JOIN bildungsdaten     b  ON b.stadt_id  = s.stadt_id AND b.zeit_id  = ?
        LEFT JOIN gesundheitsdaten  g  ON g.stadt_id  = s.stadt_id AND g.zeit_id  = ?
        LEFT JOIN freizeitdaten     f  ON f.stadt_id  = s.stadt_id AND f.zeit_id  = ?
        LEFT JOIN sicherheitsdaten  si ON si.stadt_id = s.stadt_id AND si.zeit_id = ?
    """, conn, params=(zeit_id,) * 8)

    if df.empty:
        print("  [Ranking] Keine Daten vorhanden.")
        return

    scaler = MinMaxScaler()

    def score_hoch(col: str) -> pd.Series:
        """Höherer Rohwert → höherer Score. Fehlende Werte → 0.5 (neutral)."""
        if col not in df.columns or not df[col].notna().any():
            return pd.Series([0.5] * len(df), index=df.index)
        filled = df[[col]].fillna(df[col].mean())
        return pd.Series(scaler.fit_transform(filled).flatten(), index=df.index)

    def score_niedrig(col: str) -> pd.Series:
        """Niedrigerer Rohwert → höherer Score (invertiert)."""
        if col not in df.columns or not df[col].notna().any():
            return pd.Series([0.5] * len(df), index=df.index)
        filled = df[[col]].fillna(df[col].mean())
        return pd.Series(
            (1 - scaler.fit_transform(filled)).flatten(), index=df.index
        )

    def score_kombiniert(col_dichte: str, col_pro_100k: str) -> pd.Series:
        """
        Mittelwert aus Dichte-Score und Pro-Kopf-Score.
        Verhindert, dass große oder dicht besiedelte Städte systematisch
        bevorzugt werden. Ist nur eine Spalte vorhanden, wird sie allein verwendet.
        """
        hat_dichte   = col_dichte   in df.columns and df[col_dichte].notna().any()
        hat_pro_kopf = col_pro_100k in df.columns and df[col_pro_100k].notna().any()

        if hat_dichte and hat_pro_kopf:
            return (score_hoch(col_dichte) + score_hoch(col_pro_100k)) / 2
        elif hat_dichte:
            return score_hoch(col_dichte)
        elif hat_pro_kopf:
            return score_hoch(col_pro_100k)
        return pd.Series([0.5] * len(df), index=df.index)

    # Scores berechnen
    df["score_klima"]         = score_hoch("sonnenstunden_jahr")
    df["score_wohnen"]        = score_niedrig("mietpreis_kalt_qm")
    df["score_wirtschaft"]    = score_niedrig("arbeitslosenquote")
    df["score_infrastruktur"] = score_hoch("poi_dichte")
    df["score_bildung"]       = score_kombiniert("bildungs_dichte",    "bildung_pro_100k")
    df["score_gesundheit"]    = score_kombiniert("gesundheits_dichte", "gesundheit_pro_100k")
    df["score_freizeit"]      = score_kombiniert("freizeit_dichte",    "freizeit_pro_100k")
    df["score_sicherheit"]    = score_niedrig("straftaten_je_100k")

    # Gewichteter Gesamt-Score aus config.SCORE_GEWICHTE
    df["gesamtscore"] = sum(
        df[col] * gewicht for col, gewicht in config.SCORE_GEWICHTE.items()
    )
    df["rang"] = df["gesamtscore"].rank(ascending=False, method="min").astype(int)

    # Scores in DB schreiben
    for _, row in df.iterrows():
        conn.execute("""
            INSERT INTO ranking
                (stadt_id, zeit_id,
                 score_klima, score_wohnen, score_wirtschaft, score_infrastruktur,
                 score_bildung, score_gesundheit, score_freizeit, score_sicherheit,
                 gesamtscore, rang)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(stadt_id, zeit_id) DO UPDATE SET
                score_klima         = excluded.score_klima,
                score_wohnen        = excluded.score_wohnen,
                score_wirtschaft    = excluded.score_wirtschaft,
                score_infrastruktur = excluded.score_infrastruktur,
                score_bildung       = excluded.score_bildung,
                score_gesundheit    = excluded.score_gesundheit,
                score_freizeit      = excluded.score_freizeit,
                score_sicherheit    = excluded.score_sicherheit,
                gesamtscore         = excluded.gesamtscore,
                rang                = excluded.rang
        """, (
            int(row["stadt_id"]), zeit_id,
            round(float(row["score_klima"]),         4),
            round(float(row["score_wohnen"]),        4),
            round(float(row["score_wirtschaft"]),    4),
            round(float(row["score_infrastruktur"]), 4),
            round(float(row["score_bildung"]),       4),
            round(float(row["score_gesundheit"]),    4),
            round(float(row["score_freizeit"]),      4),
            round(float(row["score_sicherheit"]),    4),
            round(float(row["gesamtscore"]),         4),
            int(row["rang"]),
        ))

    conn.commit()
    print("\n  [Ranking] Top 5:")
    print(
        df[["name", "gesamtscore", "rang"]]
        .sort_values("rang")
        .head(5)
        .to_string(index=False)
    )
