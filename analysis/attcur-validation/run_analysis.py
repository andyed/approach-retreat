#!/usr/bin/env python3
"""
Approach-retreat feasibility analysis on the Attentive Cursor Dataset
(Leiva & Arapakis 2020, Frontiers in Human Neuroscience 14:565664).

Goal: predict ad attention from approach-retreat cursor features on the
native-ad subset used by Brückner et al. (SIGIR '21, BiLSTM, F1 ~0.55-0.60).

Approach-retreat features are cheap, non-learned, and computed directly from
the `extras.middle` column (cursor-to-ad-center distance) that EvTrack already
precomputes for every mouse event.

Protocol matches Brückner SIGIR '21: 60/10/30 stratified split, 5 seeds,
weighted F1 + AUC reported.
"""
from __future__ import annotations

import json
import sys
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
    """Return a list of event dicts for mouse events only."""
    rows = []
    try:
        with open(log_path) as f:
            f.readline()  # header
            for line in f:
                parts = line.rstrip("\n").split(None, 7)
                if len(parts) < 8:
                    continue
                _cursor, ts, xpos, ypos, event, _xpath, _attrs, extras = parts
                if event not in MOUSE_EVENTS:
                    continue
                try:
                    ts_i = int(ts)
                    x = float(xpos)
                    y = float(ypos)
                except ValueError:
                    continue
                if x == 0.0 and y == 0.0:
                    continue
                middle = None
                in_target = False
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
        return []
    return rows


def compute_features(events):
    if len(events) < 3:
        return None
    ts = np.array([e[0] for e in events], dtype=np.int64)
    xs = np.array([e[1] for e in events], dtype=np.float64)
    ys = np.array([e[2] for e in events], dtype=np.float64)
    middles = np.array(
        [e[4] if e[4] is not None else np.nan for e in events], dtype=np.float64
    )
    in_targets = np.array([e[5] for e in events], dtype=bool)

    valid = ~np.isnan(middles)
    if valid.sum() < 3:
        return None

    mv_valid = middles[valid]
    min_dist = float(np.min(mv_valid))
    max_dist = float(np.max(mv_valid))

    # Index of first min in the full event sequence
    valid_idx = np.where(valid)[0]
    min_pos_in_valid = int(np.argmin(mv_valid))
    min_idx = int(valid_idx[min_pos_in_valid])

    # Retreat: max distance AFTER the min, minus min_dist
    post_valid = middles[min_idx + 1 :]
    post_valid = post_valid[~np.isnan(post_valid)]
    if len(post_valid) > 0:
        retreat_dist = float(post_valid.max() - min_dist)
    else:
        retreat_dist = 0.0

    # Total mouse path length (Brückner-style primitive)
    if len(xs) >= 2:
        d = np.hypot(np.diff(xs), np.diff(ys))
        total_length = float(d.sum())
    else:
        total_length = 0.0

    # Retreat path length (post-min) and arc ratio vs straight-line
    if min_idx < len(xs) - 1:
        rxs = xs[min_idx:]
        rys = ys[min_idx:]
        rpath = float(np.hypot(np.diff(rxs), np.diff(rys)).sum())
        # Straight-line distance to the farthest post-min sample
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

    # Dwell in target: sum of Δt intervals where both endpoints are in_target
    dt = np.diff(ts)
    both = in_targets[:-1] & in_targets[1:]
    dwell = float(dt[both].sum()) if dt.size > 0 else 0.0

    # Number of 0 → 1 transitions (entries into target)
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
        "n_events": len(events),
        "session_ms": session_ms,
    }


def main():
    gt = pl.read_csv(DATA / "groundtruth.tsv", separator="\t")
    parts = pl.read_csv(
        DATA / "participants.tsv",
        separator="\t",
        null_values=["NA", "na", ""],
        schema_overrides={"education": pl.Utf8, "age": pl.Utf8, "income": pl.Utf8},
    )
    df = gt.join(parts, on=["user_id", "log_id"], how="inner")
    print(f"Joined metadata rows: {len(df)}")

    native = df.filter(pl.col("ad_type") == "native")
    print(f"Native-ad sessions: {len(native)}")

    rows = []
    n_skipped = 0
    for row in native.iter_rows(named=True):
        log_path = DATA / "logs" / f"{row['log_id']}.csv"
        events = parse_log(log_path)
        feats = compute_features(events)
        if feats is None:
            n_skipped += 1
            continue
        feats["log_id"] = row["log_id"]
        feats["ad_clicked"] = int(row["ad_clicked"])
        feats["attention"] = int(row["attention"])
        feats["noticed"] = 1 if int(row["attention"]) >= 3 else 0
        rows.append(feats)

    print(f"Feature rows: {len(rows)}  skipped: {n_skipped}")
    if not rows:
        print("No feature rows -- aborting.")
        sys.exit(1)

    df_feat = pl.DataFrame(rows)
    print("\nLabel distributions (native-ad subset, feature-extracted):")
    print(f"  noticed (attn>=3): {df_feat['noticed'].sum()}/{len(df_feat)} "
          f"({df_feat['noticed'].mean():.3f})")
    print(f"  ad_clicked:         {df_feat['ad_clicked'].sum()}/{len(df_feat)} "
          f"({df_feat['ad_clicked'].mean():.3f})")

    print("\nFeature summary (approach-retreat only, native-ad subset):")
    print(df_feat.select([
        "min_dist", "retreat_dist", "retreat_arc_ratio",
        "total_mouse_length", "dwell_in_target_ms", "ever_in_target",
        "n_target_entries", "n_events"
    ]).describe())

    feature_cols = [
        "min_dist", "max_dist", "retreat_dist", "retreat_path",
        "retreat_arc_ratio", "total_mouse_length", "dwell_in_target_ms",
        "ever_in_target", "n_target_entries", "n_events", "session_ms",
    ]
    X_full = df_feat.select(feature_cols).to_numpy().astype(np.float64)
    X_full = np.nan_to_num(X_full, nan=0.0, posinf=1e9, neginf=-1e9)

    for target in ["noticed", "ad_clicked"]:
        y = df_feat[target].to_numpy().astype(np.int64)
        print(f"\n=== target: {target}  (pos rate {y.mean():.3f}) ===")
        configs = [
            ("approach-retreat (11 feats)", feature_cols),
            ("Brückner primitive (total_mouse_length only)", ["total_mouse_length"]),
            ("min_dist only", ["min_dist"]),
            ("min_dist + retreat_dist + ever_in_target", ["min_dist", "retreat_dist", "ever_in_target"]),
            ("retreat-only (dist + path + arc_ratio)", ["retreat_dist", "retreat_path", "retreat_arc_ratio"]),
        ]
        for label, cols in configs:
            idx = [feature_cols.index(c) for c in cols]
            Xs = X_full[:, idx]
            aucs, f1s = [], []
            for seed in range(5):
                X_tv, X_test, y_tv, y_test = train_test_split(
                    Xs, y, test_size=0.3, stratify=y, random_state=seed
                )
                pipe = Pipeline([
                    ("scaler", StandardScaler()),
                    ("lr", LogisticRegression(max_iter=1000, class_weight="balanced")),
                ])
                pipe.fit(X_tv, y_tv)
                proba = pipe.predict_proba(X_test)[:, 1]
                pred = (proba >= 0.5).astype(int)
                aucs.append(roc_auc_score(y_test, proba))
                f1s.append(f1_score(y_test, pred, average="weighted"))
            aucs = np.array(aucs)
            f1s = np.array(f1s)
            print(f"  [{label}]")
            print(f"      AUC  {aucs.mean():.3f} ± {aucs.std():.3f}")
            print(f"      F1w  {f1s.mean():.3f} ± {f1s.std():.3f}")

    # Feature importance on the click prediction task (full-data fit, no CV)
    print("\n=== Feature importance: approach-retreat → ad_clicked (full-data fit) ===")
    y_click = df_feat["ad_clicked"].to_numpy().astype(np.int64)
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    pipe.fit(X_full, y_click)
    coefs = pipe.named_steps["lr"].coef_[0]
    ordered = sorted(zip(feature_cols, coefs), key=lambda kv: abs(kv[1]), reverse=True)
    max_len = max(len(c) for c in feature_cols)
    for name, c in ordered:
        direction = "→ click" if c > 0 else "→ skip "
        print(f"  {name:<{max_len}}  {c:+.3f}  {direction}")

    # Correlation with attention score (Spearman, pooled)
    print("\n=== Spearman ρ with attention Likert (1-5) ===")
    from scipy.stats import spearmanr
    att = df_feat["attention"].to_numpy().astype(np.float64)
    for name, idx in sorted([(c, feature_cols.index(c)) for c in feature_cols]):
        rho, p = spearmanr(X_full[:, idx], att)
        sig = "***" if p < 1e-3 else ("**" if p < 0.01 else ("*" if p < 0.05 else "  "))
        print(f"  {name:<{max_len}}  ρ = {rho:+.3f}  p = {p:.3e} {sig}")

    print("\nDone.")


if __name__ == "__main__":
    main()
