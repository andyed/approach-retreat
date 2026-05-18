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
    average_precision_score,
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

    # Two targets: §4.3 analog (noticed) plus the §4.5 click target on the
    # same non-click pool for a paired ROC-AUC / PR-AUC sanity check.
    # PR-AUC matters on imbalanced data where ROC-AUC can look respectable
    # despite poor precision at usable recall. Reporting both gives a
    # complete picture of the model's behaviour at deployment thresholds.

    targets = {
        "noticed_likert_ge3": y,
        "ad_clicked": np.zeros_like(y),  # all 0 by construction (non-click pool)
    }
    # ad_clicked target only makes sense on the full ACD pool, not the
    # non-click subset. Build it from df_feat directly.
    y_full = df_feat["ad_clicked"].to_numpy().astype(np.int64)
    X_full_set = df_feat.select(feature_cols).to_numpy().astype(np.float64)
    X_full_set = np.nan_to_num(X_full_set, nan=0.0, posinf=1e9, neginf=-1e9)

    runs = [
        # (run_name, X, y, pool_description)
        ("noticed_likert_ge3 (non-click)", X, y,
         f"§4.3 WILD analog; non-click pool, n={n_total}"),
        ("ad_clicked (full)", X_full_set, y_full,
         f"§4.5 WILD click target; full native-ad pool, n={len(y_full)}"),
    ]

    all_results = {}

    for run_name, X_run, y_run, pool_desc in runs:
        print(f"\n{'='*70}\n=== {run_name}\n=== {pool_desc}\n{'='*70}")
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
        oof_proba = np.zeros(len(y_run), dtype=np.float64)
        per_fold = []
        for fold_idx, (tr, te) in enumerate(skf.split(X_run, y_run), start=1):
            pipe = Pipeline([
                ("scaler", StandardScaler()),
                ("lr", LogisticRegression(max_iter=1000, class_weight="balanced",
                                          penalty="l2", C=1.0, solver="lbfgs")),
            ])
            pipe.fit(X_run[tr], y_run[tr])
            proba = pipe.predict_proba(X_run[te])[:, 1]
            oof_proba[te] = proba
            auc_f = roc_auc_score(y_run[te], proba)
            pr_f = average_precision_score(y_run[te], proba)
            thr = youden_j_threshold(y_run[te], proba)
            pred = (proba >= thr).astype(int)
            f1_f = f1_score(y_run[te], pred)
            per_fold.append({
                "fold": fold_idx,
                "n_train": int(len(tr)),
                "n_test": int(len(te)),
                "roc_auc": float(auc_f),
                "pr_auc": float(pr_f),
                "base_rate": float(y_run[te].mean()),
                "youden_j_threshold": float(thr),
                "f1_at_threshold": float(f1_f),
            })

        auc_oof = roc_auc_score(y_run, oof_proba)
        pr_oof = average_precision_score(y_run, oof_proba)
        thr_oof = youden_j_threshold(y_run, oof_proba)
        pred_oof = (oof_proba >= thr_oof).astype(int)
        prec, rec, f1_oof, _ = precision_recall_fscore_support(
            y_run, pred_oof, average="binary", zero_division=0
        )
        per_fold_aucs = np.array([f["roc_auc"] for f in per_fold])
        per_fold_prs = np.array([f["pr_auc"] for f in per_fold])
        base_rate = float(y_run.mean())
        pr_baseline = base_rate  # PR-AUC of a chance classifier = base rate

        print(f"\n  per-fold (ROC / PR / Youden / F1):")
        for f in per_fold:
            print(f"    fold {f['fold']}: "
                  f"ROC = {f['roc_auc']:.3f}  PR = {f['pr_auc']:.3f}  "
                  f"thr = {f['youden_j_threshold']:.3f}  F1 = {f['f1_at_threshold']:.3f}")
        print(f"\n  pooled OOF:")
        print(f"    base rate           : {base_rate:.3f}  (PR-AUC chance line)")
        print(f"    ROC-AUC             : {auc_oof:.3f}  (SD per fold {per_fold_aucs.std():.3f})")
        print(f"    PR-AUC              : {pr_oof:.3f}  (SD per fold {per_fold_prs.std():.3f})")
        print(f"    PR-AUC lift / chance: {pr_oof - pr_baseline:+.3f}  "
              f"(absolute), {pr_oof / pr_baseline:.2f}× (ratio)")
        print(f"    Youden-J threshold  : {thr_oof:.3f}")
        print(f"    Precision           : {prec:.3f}")
        print(f"    Recall              : {rec:.3f}")
        print(f"    F1                  : {f1_oof:.3f}")

        all_results[run_name] = {
            "pool": pool_desc,
            "n": int(len(y_run)),
            "base_rate": base_rate,
            "pooled_oof": {
                "roc_auc": float(auc_oof),
                "pr_auc": float(pr_oof),
                "pr_auc_chance_baseline": float(pr_baseline),
                "pr_auc_lift_absolute": float(pr_oof - pr_baseline),
                "pr_auc_ratio_vs_chance": float(pr_oof / pr_baseline),
                "roc_auc_per_fold_sd": float(per_fold_aucs.std()),
                "pr_auc_per_fold_sd": float(per_fold_prs.std()),
                "youden_j_threshold": float(thr_oof),
                "precision": float(prec),
                "recall": float(rec),
                "f1": float(f1_oof),
            },
            "per_fold": per_fold,
        }

    # Pull primary "noticed" run results for the legacy fields kept for
    # backward-compatibility with the prior summary.json schema.
    primary = all_results["noticed_likert_ge3 (non-click)"]["pooled_oof"]
    auc_oof = primary["roc_auc"]
    thr_oof = primary["youden_j_threshold"]
    prec = primary["precision"]
    rec = primary["recall"]
    f1 = primary["f1"]
    per_fold_aucs = np.array(
        [f["roc_auc"]
         for f in all_results["noticed_likert_ge3 (non-click)"]["per_fold"]]
    )

    # §4.3 LAB headline for comparison
    print(f"\n=== §4.3 LAB headline (AdSERP, gaze-regression target) ===")
    print(f"  ROC-AUC              : 0.753  (LOSO 47-fold)")
    print(f"  Youden-J threshold p : 0.449")
    print(f"  Precision            : 0.867")
    print(f"  Recall               : 0.771")
    print(f"  F1                   : 0.816")
    print(f"  PR-AUC               : (not currently reported in paper §4.3)")

    print(f"\n=== Cross-dataset gap (WILD Likert noticed − LAB gaze) ===")
    print(f"  ROC-AUC           Δ : {auc_oof - 0.753:+.3f}")
    print(f"  Operating thresh  Δ : {thr_oof - 0.449:+.3f}")
    print(f"  Precision         Δ : {prec - 0.867:+.3f}")
    print(f"  Recall            Δ : {rec - 0.771:+.3f}")
    print(f"  F1                Δ : {f1 - 0.816:+.3f}")

    # Sidecar JSON
    summary = {
        "task": "ACD WILD §4.3-analog recalibration + paired ROC-AUC / PR-AUC sanity check",
        "cohort_overall": {
            "n_native_ad_sessions": int(len(df_feat)),
            "n_non_click": int(n_total),
            "n_noticed_likert_ge3": int(n_noticed),
            "noticed_rate_non_click": float(n_noticed / n_total),
        },
        "features": {
            "cols": feature_cols,
            "n_features": len(feature_cols),
            "feature_set": "WILD M4-analog (approach features, no dwell, no baseline; keeps retreat_dist since non-click subset lacks terminal lock-on)",
        },
        "cv": {
            "scheme": "StratifiedKFold(5, shuffle=True, random_state=0)",
            "note": "ACD has no participant grouping; KFold not LOSO.",
        },
        "runs": all_results,
        "lab_headline_for_comparison": {
            "source": "CIKM paper §4.3",
            "task": "AdSERP non-click gaze-regression deferred target",
            "protocol": "LOSO 47-fold",
            "roc_auc": 0.753,
            "pr_auc": "not currently reported in paper",
            "youden_j_threshold": 0.449,
            "precision": 0.867,
            "recall": 0.771,
            "f1": 0.816,
        },
        "cross_dataset_gap_noticed_vs_gaze": {
            "delta_roc_auc": float(auc_oof - 0.753),
            "delta_threshold": float(thr_oof - 0.449),
            "delta_precision": float(prec - 0.867),
            "delta_recall": float(rec - 0.771),
            "delta_f1": float(f1 - 0.816),
        },
        "interpretation": (
            "Likert ≥ 3 (post-task self-report) is a noisier proxy for "
            "the §4.3 gaze-revisited deferred construct (in-trial fixation "
            "behavior). PR-AUC pair-check: WILD noticed PR-AUC vs the "
            "PR-AUC chance line (= noticed base rate 0.648) and WILD "
            "ad_clicked PR-AUC vs its chance line (= click rate 0.303) "
            "shows whether ROC-AUC numbers reflect real precision-at-recall "
            "or just float on imbalance. Paired pattern is the actual "
            "headline."
        ),
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2))
    print(f"\nWrote {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
