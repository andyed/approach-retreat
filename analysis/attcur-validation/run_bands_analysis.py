#!/usr/bin/env python3
"""
ACD band port — tests whether viewport-band dwell adds signal over the
11-feature retreat set for ad_clicked prediction on the native-ad subset.

Rationale: on AdSERP (LAB, NB28) viewport-band dwell (AUC 0.799) is
equivalent to cursor retreat geometry (0.792) and combines to 0.837.
This script tests whether the equivalent WILD-compatible signal ports
to the Attentive Cursor Dataset.

WILD constraint: ACD scroll events fire but don't carry scrollY — viewport
reconstruction is not available. The cursor-only analog is cursor-in-
viewport-third dwell (where *the cursor* is in viewport, not where the AOI
is). It's a lower-fidelity analog than LAB bands but is honestly cursor-
only and matches the WILD regime.

Protocol mirrors run_analysis.py: 60/10/30 stratified split, 5 seeds,
native-ad subset (filtered via participants.tsv ad_type == 'native').

Run:
    python3 run_bands_analysis.py
"""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

DATA = Path("/tmp/attcur/the-attentive-cursor-dataset-master")
MOUSE_EVENTS = {"mousemove", "mouseover", "mouseout", "mousedown", "mouseup", "click"}


def parse_log(log_path: Path):
    """Return (events, viewport_h). Events include scroll for band timing."""
    rows = []
    try:
        with open(log_path) as f:
            f.readline()  # header
            for line in f:
                parts = line.rstrip("\n").split(" ", 7)
                if len(parts) < 8:
                    continue
                _cursor, ts, xpos, ypos, event, _xpath, _attrs, extras = parts
                # Only keep mouse events + scroll (for band interval closure)
                if event not in MOUSE_EVENTS and event != "scroll":
                    continue
                try:
                    ts_i = int(ts)
                    x = float(xpos)
                    y = float(ypos)
                except ValueError:
                    continue
                if event in MOUSE_EVENTS and x == 0.0 and y == 0.0:
                    continue
                middle = None
                in_target = False
                if event in MOUSE_EVENTS:
                    try:
                        d = json.loads(extras)
                        if isinstance(d, dict):
                            m = d.get("middle")
                            if m is not None:
                                middle = float(m)
                            in_target = bool(d.get("inTarget", False))
                    except Exception:
                        pass
                rows.append((ts_i, x, y, event, middle, in_target))
    except OSError:
        return [], None

    # Viewport height from sibling .xml
    vh = None
    try:
        xml_path = log_path.with_suffix(".xml")
        if xml_path.exists():
            tree = ET.parse(xml_path)
            window = tree.find("window")
            if window is not None:
                vh = int(window.text.split("x")[1])
    except Exception:
        pass
    return rows, vh


def compute_retreat_features(events):
    """Reproduces the 11-feature set in run_analysis.py.compute_features."""
    if len(events) < 3:
        return None
    mouse_events = [e for e in events if e[3] in MOUSE_EVENTS]
    if len(mouse_events) < 3:
        return None
    ts = np.array([e[0] for e in mouse_events], dtype=np.int64)
    xs = np.array([e[1] for e in mouse_events], dtype=np.float64)
    ys = np.array([e[2] for e in mouse_events], dtype=np.float64)
    middles = np.array(
        [e[4] if e[4] is not None else np.nan for e in mouse_events], dtype=np.float64
    )
    in_targets = np.array([e[5] for e in mouse_events], dtype=bool)

    valid = ~np.isnan(middles)
    if valid.sum() < 3:
        return None

    mv_valid = middles[valid]
    min_dist = float(np.min(mv_valid))
    max_dist = float(np.max(mv_valid))

    valid_idx = np.where(valid)[0]
    min_pos_in_valid = int(np.argmin(mv_valid))
    min_idx = int(valid_idx[min_pos_in_valid])

    post_valid = middles[min_idx + 1 :]
    post_valid = post_valid[~np.isnan(post_valid)]
    retreat_dist = float(post_valid.max() - min_dist) if len(post_valid) > 0 else 0.0

    if len(xs) >= 2:
        d = np.hypot(np.diff(xs), np.diff(ys))
        total_length = float(d.sum())
    else:
        total_length = 0.0

    if min_idx < len(xs) - 1:
        rxs = xs[min_idx:]
        rys = ys[min_idx:]
        rpath = float(np.hypot(np.diff(rxs), np.diff(rys)).sum())
        post_mid_slice = middles[min_idx:]
        post_mid_valid = ~np.isnan(post_mid_slice)
        if post_mid_valid.sum() >= 2:
            far_rel = int(np.argmax(np.where(post_mid_valid, post_mid_slice, -np.inf)))
            straight = float(np.hypot(rxs[far_rel] - rxs[0], rys[far_rel] - rys[0]))
            arc_ratio = rpath / straight if straight > 1.0 else 1.0
        else:
            arc_ratio = 1.0
    else:
        rpath = 0.0
        arc_ratio = 1.0

    dt = np.diff(ts)
    both = in_targets[:-1] & in_targets[1:]
    dwell = float(dt[both].sum()) if dt.size > 0 else 0.0

    trans = np.diff(in_targets.astype(np.int8))
    n_entries = int((trans > 0).sum())
    if in_targets[0]:
        n_entries += 1

    session_ms = float(ts[-1] - ts[0]) if len(ts) > 1 else 0.0

    return {
        "min_dist": min_dist,
        "max_dist": max_dist,
        "retreat_dist": retreat_dist,
        "retreat_path": rpath,
        "retreat_arc_ratio": arc_ratio,
        "total_mouse_length": total_length,
        "dwell_in_target_ms": dwell,
        "ever_in_target": int(in_targets.any()),
        "n_target_entries": n_entries,
        "n_events": len(mouse_events),
        "session_ms": session_ms,
    }


def compute_band_features(events, vh):
    """Cursor-in-viewport-third dwell per session.

    Piecewise-constant: interval between consecutive events is attributed to
    the band the cursor was in at the START of the interval. Mirrors
    `computeViewportBandsPure` semantics from the JS library.

    For ACD's single-AOI session, we also compute in-target versions —
    cursor dwell per band while inside the ad bbox.
    """
    if vh is None or vh <= 0 or len(events) < 2:
        return {k: 0.0 for k in ["vp_cursor_top_ms", "vp_cursor_mid_ms", "vp_cursor_bot_ms",
                                  "vp_cursor_top_in_ms", "vp_cursor_mid_in_ms", "vp_cursor_bot_in_ms"]}
    third = vh / 3.0
    out = {
        "vp_cursor_top_ms": 0.0,
        "vp_cursor_mid_ms": 0.0,
        "vp_cursor_bot_ms": 0.0,
        "vp_cursor_top_in_ms": 0.0,
        "vp_cursor_mid_in_ms": 0.0,
        "vp_cursor_bot_in_ms": 0.0,
    }
    # Cap inter-event gaps to filter session-boundary artifacts (idle tabs,
    # pre-task setup, post-task timing leaks). 10 s is already 5× the typical
    # inter-event gap during active cursor use; anything above that is not a
    # legitimate dwell interval.
    MAX_INTERVAL_MS = 10_000
    last_cursor_y = None
    last_in = False
    last_t = events[0][0]
    for e in events:
        t, _, y, ev_type, _, in_t = e
        if last_cursor_y is not None and t > last_t and (t - last_t) <= MAX_INTERVAL_MS:
            dt = float(t - last_t)
            cy = last_cursor_y
            if 0 <= cy < third:
                out["vp_cursor_top_ms"] += dt
                if last_in:
                    out["vp_cursor_top_in_ms"] += dt
            elif third <= cy < 2 * third:
                out["vp_cursor_mid_ms"] += dt
                if last_in:
                    out["vp_cursor_mid_in_ms"] += dt
            elif 2 * third <= cy <= vh:
                out["vp_cursor_bot_ms"] += dt
                if last_in:
                    out["vp_cursor_bot_in_ms"] += dt
        # Only mouse events (not scroll) update the cursor position — scroll
        # records (0, 0) and would reset cursor to top-left.
        if ev_type in MOUSE_EVENTS:
            last_cursor_y = y
            last_in = in_t
        last_t = t
    return out


RETREAT_FEATURES = [
    "min_dist", "max_dist", "retreat_dist", "retreat_path", "retreat_arc_ratio",
    "total_mouse_length", "dwell_in_target_ms", "ever_in_target",
    "n_target_entries", "n_events", "session_ms",
]
BAND_FEATURES = [
    "vp_cursor_top_ms", "vp_cursor_mid_ms", "vp_cursor_bot_ms",
    "vp_cursor_top_in_ms", "vp_cursor_mid_in_ms", "vp_cursor_bot_in_ms",
]


def evaluate(feat_df, feature_cols, target, seeds=(1, 2, 3, 4, 5)):
    X = feat_df.select(feature_cols).to_numpy().astype(float)
    y = feat_df[target].to_numpy().astype(int)
    aucs, f1s = [], []
    for seed in seeds:
        X_tv, X_test, y_tv, y_test = train_test_split(
            X, y, test_size=0.30, random_state=seed, stratify=y
        )
        # 60/10/30 → val = 10/70 of the 70% remaining
        X_tr, X_val, y_tr, y_val = train_test_split(
            X_tv, y_tv, test_size=1/7, random_state=seed, stratify=y_tv
        )
        # Fit on train, report on test (matching run_analysis.py convention)
        pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("lr", LogisticRegression(max_iter=5000, class_weight="balanced")),
        ])
        pipe.fit(X_tr, y_tr)
        proba = pipe.predict_proba(X_test)[:, 1]
        pred  = (proba >= 0.5).astype(int)
        aucs.append(roc_auc_score(y_test, proba))
        f1s.append(f1_score(y_test, pred, average="weighted"))
    return float(np.mean(aucs)), float(np.std(aucs)), float(np.mean(f1s)), float(np.std(f1s))


def main():
    print("ACD band port — run_bands_analysis.py")
    print(f"data: {DATA}\n")

    gt = pl.read_csv(DATA / "groundtruth.tsv", separator="\t")
    parts = pl.read_csv(
        DATA / "participants.tsv",
        separator="\t",
        null_values=["NA", "na", ""],
        schema_overrides={"education": pl.Utf8, "age": pl.Utf8, "income": pl.Utf8},
    )
    df = gt.join(parts, on=["user_id", "log_id"], how="inner")
    print(f"joined metadata rows: {len(df)}")
    native = df.filter(pl.col("ad_type") == "native")
    print(f"native-ad sessions:   {len(native)}\n")

    rows = []
    skipped = 0
    for row in native.iter_rows(named=True):
        log_path = DATA / "logs" / f"{row['log_id']}.csv"
        events, vh = parse_log(log_path)
        if not events:
            skipped += 1
            continue
        feats = compute_retreat_features(events)
        if feats is None:
            skipped += 1
            continue
        feats.update(compute_band_features(events, vh))
        feats["log_id"] = row["log_id"]
        feats["ad_clicked"] = int(row["ad_clicked"])
        feats["attention"] = int(row["attention"])
        feats["noticed"] = int(row["attention"] >= 3)
        feats["viewport_h"] = int(vh) if vh is not None else 0
        rows.append(feats)

    df_feat = pl.DataFrame(rows)
    print(f"feature rows: {len(df_feat)}  skipped: {skipped}")
    print(f"click rate:   {df_feat['ad_clicked'].mean():.3f}")
    print(f"viewport_h missing: {int((df_feat['viewport_h'] == 0).sum())}")
    print()

    # Descriptive: band feature summary
    print("Band-feature summary (native-ad, ms):")
    print(df_feat.select(BAND_FEATURES).describe())
    print()

    target = "ad_clicked"
    print(f"Target: {target}\n")
    print(f"{'model':40s}  {'AUC':>14s}  {'F1w':>14s}  n_feat")
    for name, cols in [
        ("retreat alone (11)",                  RETREAT_FEATURES),
        ("bands alone (6)",                     BAND_FEATURES),
        ("retreat + bands (17)",                RETREAT_FEATURES + BAND_FEATURES),
        ("cursor-band thirds only (3)",
            ["vp_cursor_top_ms", "vp_cursor_mid_ms", "vp_cursor_bot_ms"]),
        ("cursor-band in-target thirds (3)",
            ["vp_cursor_top_in_ms", "vp_cursor_mid_in_ms", "vp_cursor_bot_in_ms"]),
    ]:
        auc_m, auc_s, f1_m, f1_s = evaluate(df_feat, cols, target)
        print(f"{name:40s}  {auc_m:.3f} ± {auc_s:.3f}  {f1_m:.3f} ± {f1_s:.3f}  {len(cols)}")

    # Fit coefficients on full dataset for interpretation
    print("\nCoefficients (full-data fit, retreat + bands, standardized):")
    X_all = df_feat.select(RETREAT_FEATURES + BAND_FEATURES).to_numpy().astype(float)
    y_all = df_feat[target].to_numpy().astype(int)
    pipe = Pipeline([("scaler", StandardScaler()),
                     ("lr", LogisticRegression(max_iter=5000, class_weight="balanced"))])
    pipe.fit(X_all, y_all)
    coefs = pipe.named_steps["lr"].coef_.ravel()
    ordered = sorted(zip(RETREAT_FEATURES + BAND_FEATURES, coefs),
                     key=lambda x: -abs(x[1]))
    for name, c in ordered:
        marker = "*" if name in BAND_FEATURES else " "
        print(f"  {marker} {name:30s}: {c:+.3f}")

    # Persist feature + result summary for downstream use
    OUT = Path(__file__).resolve().parent / "results_bands.txt"
    with open(OUT, "w") as f:
        f.write(f"ACD band port — {target}\n")
        f.write(f"native-ad sessions: {len(df_feat)}   click rate: {df_feat[target].mean():.3f}\n\n")
        for name, cols in [
            ("retreat alone (11)",                  RETREAT_FEATURES),
            ("bands alone (6)",                     BAND_FEATURES),
            ("retreat + bands (17)",                RETREAT_FEATURES + BAND_FEATURES),
        ]:
            auc_m, auc_s, f1_m, f1_s = evaluate(df_feat, cols, target)
            f.write(f"{name:40s}  AUC {auc_m:.3f} ± {auc_s:.3f}  F1w {f1_m:.3f} ± {f1_s:.3f}\n")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
