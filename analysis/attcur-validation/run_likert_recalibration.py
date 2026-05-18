"""§4.3-analog deferred-class recalibration against ACD's Likert ≥ 3.

The CIKM paper's §4.3 trains a cursor-only LR classifier on the AdSERP
LAB pool of approached non-click episodes to predict the gaze-regression
"deferred" label (AUC 0.753, Youden-J threshold p = 0.449, precision
86.7 %, recall 77.1 %, F1 0.816). §5 then lists four deployment-time
recalibration paths -- AdSERP default, human relevance annotations,
A/B vs ranker, webcam gaze on opt-in cohort -- but none of those are
empirically demonstrated cross-dataset.

ACD has no gaze, but it has self-reported attention Likert (1-5). This
script runs the analogous §4.3 protocol on ACD: filter to non-click
(ad_clicked == 0), use Likert ≥ 3 as the "noticed/deferred" target,
report per-fold AUC + Youden-J threshold + precision/recall + F1, and
emit summary.json for paper §5 to cite as the cross-dataset
recalibration data point.

This is the WILD-side analog of the AdSERP §4.3 LAB classifier. The
Likert ≥ 3 cut is the closest construct ACD offers to gaze-revisited
"deferred" -- both are "the user noticed and considered this AOI but
did not click."

Run:
    .venv/bin/python analysis/attcur-validation/run_likert_recalibration.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

from run_analysis import compute_features, parse_log, DATA  # noqa: E402

OUT_JSON = HERE / "likert_recalibration_summary.json"


def youden_j_threshold(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Return the threshold maximizing (TPR - FPR)."""
    fpr, tpr, thr = roc_curve(y_true, y_score)
    j = tpr - fpr
    return float(thr[int(np.argmax(j))])


def main():
    print("Loading ACD groundtruth + participants ...")
    gt = pl.read_csv(DATA / "groundtruth.tsv", separator="\t")
    parts = pl.read_csv(
        DATA / "participants.tsv",
        separator="\t",
        null_values=["NA", "na", ""],
        schema_overrides={"education": pl.Utf8, "age": pl.Utf8, "income": pl.Utf8},
    )
    df = gt.join(parts, on=["user_id", "log_id"], how="inner")

    native = df.filter(pl.col("ad_type") == "native")
    print(f"Native-ad sessions: {len(native)}")

    rows = []
    n_skipped = 0
    for row in native.iter_rows(named=True):
        log_path = DATA / "logs" / f"{row['log_id']}.csv"
        events = parse_log(log_path)
        feats = compute_features(events, click_buffer_ms=0)
        if feats is None:
            n_skipped += 1
            continue
        feats["log_id"] = row["log_id"]
        feats["ad_clicked"] = int(row["ad_clicked"])
        feats["attention"] = int(row["attention"])
        feats["noticed"] = 1 if int(row["attention"]) >= 3 else 0
        rows.append(feats)

    print(f"Feature rows: {len(rows)}  skipped: {n_skipped}")
    df_feat = pl.DataFrame(rows)

    # §4.3 analog: restrict to non-click subset -- "approached but
    # not-clicked" is the LAB-side recalibration pool.
    non_click = df_feat.filter(pl.col("ad_clicked") == 0)
    n_total = len(non_click)
    n_noticed = int(non_click["noticed"].sum())
    print(f"\nNon-click pool: {n_total} sessions")
    print(f"  noticed (Likert ≥ 3): {n_noticed} ({n_noticed/n_total:.1%})")
    print(f"  not-noticed:         {n_total - n_noticed} "
          f"({(n_total - n_noticed)/n_total:.1%})")

    # WILD M4-analog feature vector: 9 approach features, drops both the
    # WILD baseline (total_mouse_length) and the LAB-analog dwell aggregate
    # (dwell_in_target_ms). Mirrors how LAB §4.3 uses the M4 cursor vector.
    feature_cols = [
        "min_dist", "max_dist", "retreat_dist", "retreat_path",
        "retreat_arc_ratio", "ever_in_target", "n_target_entries",
        "n_events", "session_ms",
    ]
    X = non_click.select(feature_cols).to_numpy().astype(np.float64)
    X = np.nan_to_num(X, nan=0.0, posinf=1e9, neginf=-1e9)
    y = non_click["noticed"].to_numpy().astype(np.int64)

    print(f"\nFeature vector: {len(feature_cols)} approach features (WILD M4-analog)")

    # 5-fold stratified CV. ACD has no participant grouping (one-shot
    # crowdworkers), so KFold is the natural protocol -- unlike LAB §4.3's
    # LOSO 47-fold (which exists because AdSERP has 47 repeated-measures
    # participants).
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    oof_proba = np.zeros_like(y, dtype=np.float64)
    per_fold = []
    for fold_idx, (tr, te) in enumerate(skf.split(X, y), start=1):
        pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("lr", LogisticRegression(max_iter=1000, class_weight="balanced",
                                      penalty="l2", C=1.0, solver="lbfgs")),
        ])
        pipe.fit(X[tr], y[tr])
        proba = pipe.predict_proba(X[te])[:, 1]
        oof_proba[te] = proba
        auc = roc_auc_score(y[te], proba)
        thr = youden_j_threshold(y[te], proba)
        pred = (proba >= thr).astype(int)
        f1 = f1_score(y[te], pred)
        per_fold.append({
            "fold": fold_idx,
            "n_train": int(len(tr)),
            "n_test": int(len(te)),
            "auc": float(auc),
            "youden_j_threshold": float(thr),
            "f1_at_threshold": float(f1),
        })

    # OOF aggregate (pooled across all folds for a single set of metrics
    # that map onto the §4.3 headline numbers).
    auc_oof = roc_auc_score(y, oof_proba)
    thr_oof = youden_j_threshold(y, oof_proba)
    pred_oof = (oof_proba >= thr_oof).astype(int)
    prec, rec, f1, _ = precision_recall_fscore_support(
        y, pred_oof, average="binary", zero_division=0
    )

    per_fold_aucs = np.array([f["auc"] for f in per_fold])

    print("\n=== Per-fold ===")
    for f in per_fold:
        print(f"  fold {f['fold']}: AUC = {f['auc']:.3f}  "
              f"Youden p = {f['youden_j_threshold']:.3f}  "
              f"F1 = {f['f1_at_threshold']:.3f}")

    print(f"\n=== Pooled OOF metrics (WILD §4.3 analog) ===")
    print(f"  AUC                  : {auc_oof:.3f}")
    print(f"  Per-fold AUC SD      : {per_fold_aucs.std():.3f}")
    print(f"  Youden-J threshold p : {thr_oof:.3f}")
    print(f"  Precision            : {prec:.3f}")
    print(f"  Recall               : {rec:.3f}")
    print(f"  F1                   : {f1:.3f}")

    # §4.3 LAB headline for comparison
    print(f"\n=== §4.3 LAB headline (AdSERP, gaze-regression target) ===")
    print(f"  AUC                  : 0.753  (LOSO 47-fold)")
    print(f"  Youden-J threshold p : 0.449")
    print(f"  Precision            : 0.867")
    print(f"  Recall               : 0.771")
    print(f"  F1                   : 0.816")

    print(f"\n=== Cross-dataset gap (WILD Likert − LAB gaze) ===")
    print(f"  AUC               Δ : {auc_oof - 0.753:+.3f}")
    print(f"  Operating thresh  Δ : {thr_oof - 0.449:+.3f}")
    print(f"  Precision         Δ : {prec - 0.867:+.3f}")
    print(f"  Recall            Δ : {rec - 0.771:+.3f}")
    print(f"  F1                Δ : {f1 - 0.816:+.3f}")

    # Sidecar JSON
    summary = {
        "task": "ACD non-click Likert ≥ 3 recalibration (§4.3 WILD analog)",
        "cohort": {
            "n_sessions": int(n_total),
            "n_noticed": int(n_noticed),
            "noticed_rate": float(n_noticed / n_total),
        },
        "features": {
            "cols": feature_cols,
            "n_features": len(feature_cols),
            "feature_set": "WILD M4-analog (approach features, no dwell, no baseline)",
        },
        "cv": {
            "scheme": "StratifiedKFold(5, shuffle=True, random_state=0)",
            "note": "ACD has no participant grouping; KFold not LOSO.",
        },
        "pooled_oof": {
            "auc": float(auc_oof),
            "auc_per_fold_sd": float(per_fold_aucs.std()),
            "youden_j_threshold": float(thr_oof),
            "precision": float(prec),
            "recall": float(rec),
            "f1": float(f1),
        },
        "per_fold": per_fold,
        "lab_headline_for_comparison": {
            "source": "CIKM paper §4.3",
            "task": "AdSERP non-click gaze-regression deferred target",
            "protocol": "LOSO 47-fold",
            "auc": 0.753,
            "youden_j_threshold": 0.449,
            "precision": 0.867,
            "recall": 0.771,
            "f1": 0.816,
        },
        "cross_dataset_gap": {
            "delta_auc": float(auc_oof - 0.753),
            "delta_threshold": float(thr_oof - 0.449),
            "delta_precision": float(prec - 0.867),
            "delta_recall": float(rec - 0.771),
            "delta_f1": float(f1 - 0.816),
        },
        "interpretation": (
            "Likert ≥ 3 is a noisier proxy for the §4.3 gaze-revisited "
            "deferred construct than AdSERP's fixation-based label. "
            "Cross-dataset gap quantifies how far the LAB-calibrated "
            "operating threshold travels when retargeted on a different "
            "attention construct."
        ),
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2))
    print(f"\nWrote {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
