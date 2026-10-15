#!/usr/bin/env python3
"""The seven AdSERP M4 features, refit on the Attentive Cursor Dataset.

Invoked by `run_analysis.py --m4-seven`. The committed §4.5 comparison used an
eight-feature "M4-analog" adapted to ACD (min_dist, max_dist, retreat_path,
retreat_arc_ratio, ever_in_target, n_target_entries, n_events, session_ms).
This mode instead computes the exact seven features of the AdSERP headline
model M4 from a per-sample cursor-to-ad distance series, so the paper can say
"the same seven features, refit on ACD".

Accumulator rules: `m4_from_dist` is the per-result feature block of
attentional-foraging/scripts/m4_nb21_hybrid_rerun.py (compute_hybrid_features,
the parity-verified Python port of the JS ResultFeatureTracker), copied
verbatim. `verify_upstream_copy()` re-reads the upstream file at run time and
asserts the copied block is textually identical, so the copy cannot drift
silently. Only the distance series fed into it differs by variant:

  (a) "middle":   d_t = extras.middle, EvTrack's Euclidean distance from the
                  cursor to the ad's bounding-box center.
  (b) "vertical": d_t = |y_t - ad_center_y|, the AdSERP signal model. The ad's
                  bounding box is not stored in ACD, but every mouse event's
                  extras carry Euclidean distances to the four box corners and
                  the center, so the axis-aligned box (left, top, right, bottom)
                  is recovered by a joint nonlinear least-squares fit to all five
                  distances over the session's events. ad_center_y = (top+bottom)/2.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import subprocess
import textwrap
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
UPSTREAM = Path.home() / "Documents/dev/attentional-foraging/scripts/m4_nb21_hybrid_rerun.py"

# Constants copied from m4_nb21_hybrid_rerun.py (same names, same values).
PROX_THRESHOLD = 100
MIN_VEL_DT_MS = 8.0
MAX_PLAUSIBLE_VEL = 5000.0

# AdSERP M4 = the nine-feature tracker vector minus the two leakage-screened
# terms (final_dist, retreat_dist).
M4_SEVEN = [
    "min_dist", "mean_dist", "dwell_in_proximity_ms",
    "mean_approach_velocity", "max_approach_velocity",
    "direction_changes", "frac_decreasing",
]

# Committed §4.5 numbers (Table 5, output/results-buffered-grid.txt Run C).
# The mode refuses to report new numbers unless these reproduce.
COMMITTED = {
    "baseline_mouse_length": 0.653,
    "m3_analog_10": 0.765,
    "m4_analog_8": 0.763,
    "n_sessions": 902,
}

N_SPLITS = 5          # committed protocol: random_state 0..4
N_SPLITS_SENS = 100   # sensitivity: same protocol, more repeats
TEST_SIZE = 0.3

# Box-fit quality flag. Distances are integer-rounded, so a correct fit sits
# near 0.25 px median residual; sessions above this are flagged and dropped in
# a sensitivity rerun (they stay in the headline population).
BOX_FLAG_MEDIAN_RESID_PX = 2.0

# Starting boxes (left, top, right, bottom) for the fit: the SERP layouts seen
# in ACD's native-ad pages. The fit keeps the lowest-cost solution.
BOX_INITS = ([128, 100, 744, 286], [128, 100, 778, 374], [150, 125, 782, 231],
             [128, 100, 778, 494], [791, 105, 1250, 360])


# --- verbatim copy -----------------------------------------------------------
# BEGIN VERBATIM (m4_nb21_hybrid_rerun.py, compute_hybrid_features inner loop)
def m4_from_dist(ts_all, dist):
    min_dist = float(dist.min())
    mean_dist = float(dist.mean())
    final_dist = float(dist[-1])
    min_idx = int(np.argmin(dist))
    retreat_dist = float(dist[-1] - dist[min_idx])

    in_prox = dist < PROX_THRESHOLD
    dwell_ms = 0.0
    for i in range(1, len(ts_all)):
        if in_prox[i]:
            dt = int(ts_all[i] - ts_all[i - 1])
            if 0 < dt < 2000:
                dwell_ms += dt

    if len(ts_all) >= 2:
        dts = np.diff(ts_all).astype(float)
        # Floor dt (not just the dt==0 case) so a tiny gap cannot
        # manufacture an impossible speed, then clamp symmetrically. The
        # clamp preserves sign, so direction_changes / frac_decreasing and
        # the by-design negative mean are unaffected. See JS parity note.
        dts = np.maximum(dts, MIN_VEL_DT_MS)
        vels = -np.diff(dist) / dts * 1000.0
        vels = np.clip(vels, -MAX_PLAUSIBLE_VEL, MAX_PLAUSIBLE_VEL)
        mean_vel = float(vels.mean())
        max_vel = float(vels.max())
        direction_changes = int(np.sum(np.diff(np.sign(vels)) != 0))
        frac_decreasing = float(np.mean(np.diff(dist) < 0))
    else:
        mean_vel = max_vel = 0.0
        direction_changes = 0
        frac_decreasing = 0.0
# END VERBATIM
    return {
        "min_dist": min_dist,
        "mean_dist": mean_dist,
        "final_dist": final_dist,
        "retreat_dist": retreat_dist,
        "dwell_in_proximity_ms": dwell_ms,
        "mean_approach_velocity": mean_vel,
        "max_approach_velocity": max_vel,
        "direction_changes": direction_changes,
        "frac_decreasing": frac_decreasing,
    }


def _verbatim_block(lines):
    return textwrap.dedent("\n".join(lines)).strip()


def verify_upstream_copy():
    """Assert m4_from_dist's body equals the upstream per-result block.

    Upstream block = from `min_dist = float(dist.min())` through the last
    `frac_decreasing = 0.0`; local block = the same span between the
    BEGIN/END VERBATIM markers in this file.
    """
    if not UPSTREAM.exists():
        return {"status": "skipped", "reason": f"{UPSTREAM} not found"}
    up = UPSTREAM.read_text().splitlines()
    start = next(i for i, l in enumerate(up) if l.strip() == "min_dist = float(dist.min())")
    end = max(i for i, l in enumerate(up) if l.strip() == "frac_decreasing = 0.0")
    mine = Path(__file__).read_text().splitlines()
    m0 = next(i for i, l in enumerate(mine) if l.strip() == "min_dist = float(dist.min())")
    m1 = next(i for i, l in enumerate(mine) if l.startswith("# END VERBATIM"))
    ok = _verbatim_block(up[start:end + 1]) == _verbatim_block(mine[m0:m1])
    if not ok:
        raise SystemExit("m4_from_dist drifted from m4_nb21_hybrid_rerun.py -- re-copy it.")
    return {
        "status": "identical",
        "upstream_file": str(UPSTREAM),
        "upstream_lines": [start + 1, end + 1],
        "upstream_git_sha": _git_sha(UPSTREAM.parent, UPSTREAM.name),
        "upstream_sha256": hashlib.sha256(UPSTREAM.read_bytes()).hexdigest(),
    }


# --- ACD log parsing for variant (b) -----------------------------------------
def parse_box_rows(log_path: Path):
    """(x, y, topLeft, topRight, bottomLeft, bottomRight, middle) for every
    event whose extras carry all five distances (x=y=0 dropped, as in
    run_analysis.parse_log)."""
    out = []
    with open(log_path) as f:
        f.readline()
        for line in f:
            parts = line.rstrip("\n").split(None, 7)
            if len(parts) < 8:
                continue
            try:
                x, y = float(parts[2]), float(parts[3])
                d = json.loads(parts[7])
            except (ValueError, json.JSONDecodeError):
                continue
            if (x == 0.0 and y == 0.0) or not isinstance(d, dict):
                continue
            try:
                out.append((x, y, float(d["topLeft"]), float(d["topRight"]),
                            float(d["bottomLeft"]), float(d["bottomRight"]),
                            float(d["middle"])))
            except (KeyError, TypeError, ValueError):
                continue
    return np.array(out, dtype=np.float64).reshape(-1, 7)


def _box_distances(p, E):
    L, T, R, B = p
    x, y = E[:, 0], E[:, 1]
    return np.stack([np.hypot(x - L, y - T), np.hypot(x - R, y - T),
                     np.hypot(x - L, y - B), np.hypot(x - R, y - B),
                     np.hypot(x - (L + R) / 2, y - (T + B) / 2)], axis=1)


def ad_bbox(log_path: Path):
    """Ad bounding box from the five per-event distances. Uses every event in
    the session: the box is page layout (what getBoundingClientRect returns at
    render time), not behaviour, so post-click events carry no label."""
    E = parse_box_rows(log_path)
    if len(E) == 0:
        return None
    best = None
    for init in BOX_INITS:
        r = least_squares(lambda p: (_box_distances(p, E) - E[:, 2:]).ravel(),
                          init, loss="soft_l1", f_scale=3.0)
        if best is None or r.cost < best.cost:
            best = r
    L, T, R, B = (float(v) for v in best.x)
    resid = np.abs(_box_distances(best.x, E) - E[:, 2:])
    return {"left": L, "top": T, "right": R, "bottom": B,
            "center_y": (T + B) / 2,
            "median_resid_px": float(np.median(resid)),
            "n_events": int(len(E))}


# --- evaluation ---------------------------------------------------------------
def split_aucs(X, y, n_splits):
    """Committed protocol: stratified 70/30 by session, random_state 0..n-1,
    StandardScaler + LogisticRegression(class_weight='balanced')."""
    aucs = []
    for seed in range(n_splits):
        Xtr, Xte, ytr, yte = train_test_split(
            X, y, test_size=TEST_SIZE, stratify=y, random_state=seed)
        pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("lr", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ])
        pipe.fit(Xtr, ytr)
        aucs.append(float(roc_auc_score(yte, pipe.predict_proba(Xte)[:, 1])))
    return np.array(aucs)


def _agg(a):
    # np.std default (ddof=0) -- matches the committed run_analysis.py output.
    return {"mean": round(float(a.mean()), 4), "sd": round(float(a.std()), 4),
            "per_split": [round(float(v), 4) for v in a]}


def _git_sha(repo: Path, path: str | None = None):
    try:
        cmd = ["git", "-C", str(repo), "log", "-1", "--format=%H"]
        if path:
            cmd += ["--", path]
        return subprocess.check_output(cmd, text=True).strip()
    except Exception:
        return None


def _git_dirty(repo: Path):
    try:
        return bool(subprocess.check_output(
            ["git", "-C", str(repo), "status", "--porcelain", "--",
             "run_analysis.py", "m4_seven.py"], text=True).strip())
    except Exception:
        return None


def run(df_feat_rows, sessions, data_dir: Path, args, feature_cols):
    """df_feat_rows: committed compute_features rows (same population).
    sessions: {log_id: truncated event list} for those rows, in the same order."""
    upstream = verify_upstream_copy()
    y = np.array([r["ad_clicked"] for r in df_feat_rows], dtype=np.int64)
    n = len(y)

    def committed_X(cols):
        X = np.array([[r[c] for c in cols] for r in df_feat_rows], dtype=np.float64)
        return np.nan_to_num(X, nan=0.0, posinf=1e9, neginf=-1e9)

    m4_eight = [c for c in feature_cols if c not in ("dwell_in_target_ms", "total_mouse_length")]
    ref = {
        "baseline_mouse_length": split_aucs(committed_X(["total_mouse_length"]), y, N_SPLITS),
        "m3_analog_10": split_aucs(committed_X(feature_cols), y, N_SPLITS),
        "m4_analog_8": split_aucs(committed_X(m4_eight), y, N_SPLITS),
    }
    gate = {"committed": COMMITTED, "recomputed": {k: round(float(v.mean()), 3) for k, v in ref.items()}}
    gate["recomputed"]["n_sessions"] = n
    gate["pass"] = all(gate["recomputed"][k] == COMMITTED[k] for k in COMMITTED)
    print(f"\n[repro gate] {json.dumps(gate)}")
    if not gate["pass"]:
        raise SystemExit("Committed §4.5 numbers did not reproduce -- refusing to report M4-7.")

    # Per-session distance series for the two variants.
    feats = {"middle": [], "vertical": []}
    tri_log = []
    for r in df_feat_rows:
        ev = sessions[r["log_id"]]
        ts = np.array([e[0] for e in ev], dtype=np.int64)
        mid = np.array([e[4] if e[4] is not None else np.nan for e in ev], dtype=np.float64)
        ok = ~np.isnan(mid)
        feats["middle"].append(m4_from_dist(ts[ok], mid[ok]))
        bb = ad_bbox(data_dir / "logs" / f"{r['log_id']}.csv")
        tri_log.append({"log_id": r["log_id"], **(bb or {"failed": True})})
        if bb is None:
            feats["vertical"].append(None)
            continue
        ys = np.array([e[2] for e in ev], dtype=np.float64)
        feats["vertical"].append(m4_from_dist(ts, np.abs(ys - bb["center_y"])))

    n_fail = sum(1 for f in feats["vertical"] if f is None)
    resid = np.array([t["median_resid_px"] for t in tri_log if "median_resid_px" in t])
    heights = np.array([t["bottom"] - t["top"] for t in tri_log if "top" in t])
    widths = np.array([t["right"] - t["left"] for t in tri_log if "top" in t])
    flagged = [t["log_id"] for t in tri_log if t.get("median_resid_px", 0) > BOX_FLAG_MEDIAN_RESID_PX]
    tri_summary = {
        "method": "joint axis-aligned box fit (left, top, right, bottom): scipy least_squares, soft_l1, to all five extras distances (4 corners + middle) over every mouse event in the session",
        "n_sessions": n, "n_failed": n_fail,
        "flag_median_resid_px": BOX_FLAG_MEDIAN_RESID_PX,
        "flagged_log_ids": flagged,
        "median_resid_px": {"p50": round(float(np.median(resid)), 2),
                                          "p95": round(float(np.percentile(resid, 95)), 2),
                                          "max": round(float(resid.max()), 2)},
        "ad_height_px": {"p5": round(float(np.percentile(heights, 5)), 1), "p50": round(float(np.median(heights)), 1),
                         "p95": round(float(np.percentile(heights, 95)), 1)},
        "ad_width_px": {"p50": round(float(np.median(widths)), 1)},
    }
    print(f"[box fit] {json.dumps(tri_summary)}")
    if n_fail:
        raise SystemExit(f"{n_fail} sessions had no recoverable ad box; population would change.")

    mouse = committed_X(["total_mouse_length"])
    dwell = committed_X(["dwell_in_target_ms"])
    results = {}
    for variant, rows in feats.items():
        X7 = np.array([[f[c] for c in M4_SEVEN] for f in rows], dtype=np.float64)
        assert np.isfinite(X7).all(), variant
        models = {
            "m4_7": X7,
            "m4_7_plus_mouse_length": np.hstack([X7, mouse]),
            "m4_7_plus_dwell_in_target_ms": np.hstack([X7, dwell]),
        }
        block = {}
        for name, X in models.items():
            a5 = split_aucs(X, y, N_SPLITS)
            a100 = split_aucs(X, y, N_SPLITS_SENS)
            block[name] = {"auc": _agg(a5),
                           "auc_100_splits": {"mean": round(float(a100.mean()), 4), "sd": round(float(a100.std()), 4)}}
        # Paired per-split differences (same split indices), for reference only.
        m4 = split_aucs(X7, y, N_SPLITS)
        block["paired_m4_7_minus_mouse_length"] = _agg(m4 - ref["baseline_mouse_length"])
        block["paired_m4_7_minus_m4_analog_8"] = _agg(m4 - ref["m4_analog_8"])
        block["feature_means_by_class"] = {
            c: {"clicked": round(float(X7[y == 1, j].mean()), 2), "not_clicked": round(float(X7[y == 0, j].mean()), 2)}
            for j, c in enumerate(M4_SEVEN)}
        keep = np.array([r["log_id"] not in flagged for r in df_feat_rows])
        if (~keep).any():
            block["sensitivity_drop_flagged_boxes"] = {
                "n_sessions": int(keep.sum()),
                "m4_7": _agg(split_aucs(X7[keep], y[keep], N_SPLITS)),
                "baseline_mouse_length": _agg(split_aucs(mouse[keep], y[keep], N_SPLITS)),
            }
        results[variant] = block
        print(f"\n=== M4-7, distance = {variant} ===")
        for name in models:
            s = block[name]["auc"]
            print(f"  {name:<32} AUC {s['mean']:.3f} ± {s['sd']:.3f}   (100 splits {block[name]['auc_100_splits']['mean']:.3f} ± {block[name]['auc_100_splits']['sd']:.3f})")

    ref_100 = {k: split_aucs(committed_X(c), y, N_SPLITS_SENS) for k, c in
               (("baseline_mouse_length", ["total_mouse_length"]), ("m4_analog_8", m4_eight))}
    reference = {k: {"auc": _agg(v)} for k, v in ref.items()}
    for k, v in ref_100.items():
        reference[k]["auc_100_splits"] = {"mean": round(float(v.mean()), 4), "sd": round(float(v.std()), 4)}
    reference["m4_analog_8"]["features"] = m4_eight
    print("\n=== reference (committed feature vectors) ===")
    for k, v in reference.items():
        print(f"  {k:<32} AUC {v['auc']['mean']:.3f} ± {v['auc']['sd']:.3f}")

    repo = HERE.parent.parent
    summary = {
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "regime": "WILD, ACD",
        "config": {
            "dataset": "Attentive Cursor Dataset (Leiva & Arapakis 2020), native-ad sessions",
            "data_dir": str(data_dir),
            "target": "ad_clicked",
            "click_buffer_ms": args.click_buffer_ms,
            "drop_retreat_dist": args.drop_retreat_dist,
            "n_sessions": n, "n_positive": int(y.sum()), "positive_rate": round(float(y.mean()), 4),
            "population_rule": "native-ad sessions; every session truncated at (last 'click' event of any kind) - buffer, whether or not the ad was clicked; sessions with <3 mouse events with a valid extras.middle after truncation dropped (run_analysis.compute_features)",
            "one_session_per_participant": True,
            "split_protocol": {
                "kind": "repeated stratified holdout (sklearn train_test_split)",
                "train_test": "70/30", "stratify": "ad_clicked", "unit": "session (= participant)",
                "repeats": N_SPLITS, "random_state": list(range(N_SPLITS)),
                "sd": "population SD over the repeats (numpy ddof=0)",
                "sensitivity_repeats": N_SPLITS_SENS,
                "model": "StandardScaler + LogisticRegression(max_iter=1000, class_weight='balanced')",
                "note": "No validation split and no CV folds; run_analysis.py's docstring/README '60/10/30' describes Brueckner's protocol, not what the code runs.",
            },
            "m4_seven_features": M4_SEVEN,
            "accumulator_constants": {"prox_threshold_px": PROX_THRESHOLD, "dwell_dt_window_ms": [0, 2000],
                                      "min_vel_dt_ms": MIN_VEL_DT_MS, "max_plausible_vel_px_s": MAX_PLAUSIBLE_VEL},
            "distance_variants": {
                "middle": "d_t = extras.middle, Euclidean cursor-to-ad-center distance (EvTrack), events with a valid middle",
                "vertical": "d_t = |y_t - ad_center_y|, ad box fit jointly to the four corner + center distances; all mouse events (AdSERP signal model)",
            },
        },
        "repro_gate": gate,
        "upstream_copy_check": upstream,
        "ad_box_fit": tri_summary,
        "results": results,
        "reference": reference,
        "provenance": {
            "producer": "analysis/attcur-validation/run_analysis.py --m4-seven (m4_seven.py)",
            "approach_retreat_git_sha": _git_sha(repo),
            "working_tree_dirty": _git_dirty(HERE),
            "python_numpy": np.__version__,
        },
    }
    out = HERE / "output" / "m4_seven_summary.json"
    out.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"\nWrote {out}")
