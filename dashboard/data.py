"""
dashboard/data.py — Datenladen und Aufbereitung
================================================
Lädt alle Tabellen aus der SQLite-DB und merged sie zu einem
flachen DataFrame, den das Dashboard direkt verwenden kann.
Gecacht für 1 Stunde (Streamlit-Cache).
"""

import sqlite3

import numpy as np
import pandas as pd
import streamlit as st

import config


@st.cache_data(ttl=3600)
def lade_alle_tabellen() -> dict[str, pd.DataFrame | None]:
    """
    Lädt alle relevanten Tabellen aus der DB.
    Gibt ein Dict zurück – fehlende Tabellen liefern ein leeres DataFrame.
    """
    def safe_query(conn: sqlite3.Connection, query: str) -> pd.DataFrame:
        try:
            return pd.read_sql_query(query, conn)
        except Exception:
            return pd.DataFrame()

    try:
        conn = sqlite3.connect("urbanscore.db")
        tabellen = {
            "staedte":    pd.read_sql_query("SELECT * FROM stadt", conn),
            "zeit":       pd.read_sql_query("SELECT * FROM zeit ORDER BY jahr DESC", conn),
            "wetter":     safe_query(conn, "SELECT * FROM wetterdaten"),
            "miete":      safe_query(conn, "SELECT * FROM mietdaten"),
            "arbeit":     safe_query(conn, "SELECT * FROM arbeitsmarktdaten"),
            "infra":      safe_query(conn, "SELECT * FROM infrastruktur"),
            "ranking":    safe_query(conn, "SELECT * FROM ranking"),
            "bildung":    safe_query(conn, "SELECT * FROM bildungsdaten"),
            "gesundheit": safe_query(conn, "SELECT * FROM gesundheitsdaten"),
            "freizeit":   safe_query(conn, "SELECT * FROM freizeitdaten"),
            "sicherheit": safe_query(conn, "SELECT * FROM sicherheitsdaten"),
        }
        conn.close()
        return tabellen
    except Exception as exc:
        st.error(f"Datenbankfehler: {exc}")
        return {}


def filter_zeitraum(tabellen: dict, zeit_id: int) -> dict[str, pd.DataFrame]:
    """Filtert alle Zeitreihen-Tabellen auf eine bestimmte zeit_id."""
    zeitreihen = ["wetter", "miete", "arbeit", "infra", "ranking",
                  "bildung", "gesundheit", "freizeit", "sicherheit"]
    return {
        key: df[df["zeit_id"] == zeit_id] if not df.empty else pd.DataFrame()
        for key, df in tabellen.items()
        if key in zeitreihen
    }


def baue_hauptdataframe(
    staedte: pd.DataFrame, gefiltert: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """
    Merged alle gefilterten Tabellen mit dem Städte-Stammdatensatz.
    Doppelte Spalten (außer stadt_id) werden vor dem Merge entfernt.
    """
    df = staedte.copy()
    for tab in gefiltert.values():
        if tab.empty:
            continue
        doppelt = [c for c in tab.columns if c in df.columns and c != "stadt_id"]
        df = df.merge(tab.drop(columns=doppelt), on="stadt_id", how="left")
    return df


def berechne_personscore(df: pd.DataFrame, gewichte: dict[str, float]) -> pd.Series:
    """
    Berechnet den personalisierten Gesamt-Score für jede Stadt.
    Fehlende Einzel-Scores werden übersprungen (kein Abzug).
    Gewichte werden intern auf 1.0 normiert.
    """
    gesamt_gewicht = sum(gewichte.values()) or 1.0

    def _score(row: pd.Series) -> float:
        total = 0.0
        for dim, col in config.SCORE_MAP.items():
            v = row.get(col)
            if pd.notna(v):
                total += float(v) * (gewichte[dim] / gesamt_gewicht)
        return total

    return df.apply(_score, axis=1)
