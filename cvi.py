"""Pengiraan CVI / CVR / kappa* untuk kajian Delphi SJKP.
Modul tulen (pandas sahaja) — boleh diuji tanpa Streamlit / gspread.
"""
import math
import pandas as pd


def _icvi_row(vals):
    vals = [v for v in vals if pd.notna(v)]
    N = len(vals)
    if N == 0:
        return 0, 0, float("nan"), float("nan"), float("nan")
    n = sum(1 for v in vals if v >= 3)
    icvi = n / N
    pc = math.comb(N, n) * (0.5 ** N)
    kappa = (icvi - pc) / (1 - pc) if pc != 1 else float("nan")
    return N, n, icvi, pc, kappa


def decision(icvi):
    if pd.isna(icvi):
        return ""
    if icvi >= 0.78:
        return "Kekal"
    if icvi >= 0.70:
        return "Ubah"
    return "Buang"


def cvi_table(df_long, items_meta, value_col="relevance"):
    """df_long: rows with columns [item_code, expert_id, value_col].
    items_meta: dict code -> (construct, keyword, statement).
    Returns per-item dataframe of stats.
    """
    rows = []
    # keep only latest rating per (expert, item) if duplicates
    if "timestamp" in df_long.columns:
        df_long = (df_long.sort_values("timestamp")
                   .drop_duplicates(["expert_id", "item_code"], keep="last"))
    grouped = df_long.groupby("item_code")[value_col]
    for code, meta in items_meta.items():
        vals = grouped.get_group(code).tolist() if code in grouped.groups else []
        N, n, icvi, pc, kappa = _icvi_row(vals)
        rows.append({
            "Kod": code,
            "Construct": meta[0],
            "Kata Kunci": meta[1],
            "Pernyataan": meta[2],
            "N": N,
            "n(>=3)": n,
            "I-CVI": round(icvi, 3) if pd.notna(icvi) else None,
            "kappa*": round(kappa, 3) if pd.notna(kappa) else None,
            "Keputusan": decision(icvi),
        })
    return pd.DataFrame(rows)


def scvi_summary(cvi_df, targets):
    """Ringkasan setiap construct: bil calon, bil Kekal, S-CVI/Ave, sasaran."""
    out = []
    for con, g in cvi_df.groupby("Construct"):
        vals = g["I-CVI"].dropna()
        out.append({
            "Construct": con,
            "Bil. calon": len(g),
            "Bil. Kekal": int((g["Keputusan"] == "Kekal").sum()),
            "S-CVI/Ave": round(vals.mean(), 3) if len(vals) else None,
            "Sasaran": targets.get(con, ""),
        })
    return pd.DataFrame(out)


def cvr_table(df_long, items_meta):
    """CVR daripada penilaian 'Penting' (column 'essential' == 'Penting')."""
    if "timestamp" in df_long.columns:
        df_long = (df_long.sort_values("timestamp")
                   .drop_duplicates(["expert_id", "item_code"], keep="last"))
    rows = []
    for code, meta in items_meta.items():
        sub = df_long[df_long["item_code"] == code]
        vals = sub["essential"].dropna()
        N = len(vals)
        ne = int((vals == "Penting").sum())
        cvr = ((ne - N / 2) / (N / 2)) if N else float("nan")
        rows.append({
            "Kod": code, "Construct": meta[0], "Kata Kunci": meta[1],
            "N": N, "Bil. Penting": ne,
            "CVR": round(cvr, 3) if pd.notna(cvr) else None,
        })
    return pd.DataFrame(rows)


# Nilai kritikal CVR (Lawshe 1975, satu-hujung .05)
CVR_CRITICAL = {5: .99, 6: .99, 7: .99, 8: .75, 9: .78, 10: .62, 11: .59,
                12: .56, 13: .54, 14: .51, 15: .49, 20: .42, 25: .37}
