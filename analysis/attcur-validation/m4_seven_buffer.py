#!/usr/bin/env python3
"""Does the ACD M4-7 result survive a buffer that actually removes the endpoint?

The committed rule (run_analysis.truncate_at_click) cuts every session at its
last `click` event of any kind minus Δ. At Δ = 500 ms that removes a median of
one mousemove from ad-clicked sessions, because the cursor is usually already
at rest on the ad half a second before the click. This producer re-anchors the
cut on the ad press and sweeps Δ.

Rules (all keep events with ts < anchor - Δ; sessions with no anchor are left
whole):
  committed   anchor = last click of any kind (both classes). Δ = 0 means "no
              truncation", as in run_analysis.py.
  ad_anchor   ad-clicked: anchor = last in-target mousedown at or before the
              first in-target click; else that click; else (no in-target click
              logged) the last click of any kind. Non-clicked: last click of any
              kind. Δ = 0 cuts at the anchor itself.
  ad_anchor_drop_noclick_pos   ad_anchor, minus ad-clicked sessions that log no
              click event at all (their endpoint can never be cut).
  ad_anchor_drop_noclick_both  ad_anchor, minus sessions of either class that
              log no click event (symmetric: no session is left whole because
              it lacks a click).

Population after truncation: the committed run_analysis.compute_features rule
(>= 3 mouse events with a valid extras.middle). Features: the seven AdSERP M4
features on d_t = |y_t - ad_center_y| (m4_seven variant (b)), and session mouse
length. Gate: the committed rule at Δ = 500 must reproduce 0.765 / 0.653 / 902.

Run: ATTCUR_DATA=... python m4_seven_buffer.py
Writes output/m4_seven_buffer_summary.json.
"""
from __future__ import annotations

import datetime
import json
import os
from pathlib import Path

import numpy as np
import polars as pl

from run_analysis import DATA, compute_features, parse_log, truncate_at_click
from m4_seven import (M4_SEVEN, N_SPLITS, N_SPLITS_SENS, _agg, _git_sha, ad_bbox,
                      m4_from_dist, split_aucs, verify_upstream_copy)

HERE = Path(__file__).resolve().parent
DELTAS = [0, 500, 1000, 2000]
GATE = {"m4_7_vertical": 0.765, "baseline_mouse_length": 0.653, "n_sessions": 902}


def load_sessions():
    gt = pl.read_csv(DATA / "groundtruth.tsv", separator="\t")
    parts = pl.read_csv(DATA / "participants.tsv", separator="\t",
                        null_values=["NA", "na", ""],
                        schema_overrides={"education": pl.Utf8, "age": pl.Utf8, "income": pl.Utf8})
    native = gt.join(parts, on=["user_id", "log_id"], how="inner").filter(pl.col("ad_type") == "native")
    out = []
    for row in native.iter_rows(named=True):
        log_path = DATA / "logs" / f"{row['log_id']}.csv"
        out.append({"log_id": row["log_id"], "y": int(row["ad_clicked"]),
                    "events": parse_log(log_path), "box": ad_bbox(log_path)})
    return out


def find_anchor(s):
    """(anchor_ts or None, how). Events are (ts, x, y, event, middle, in_target)."""
    ev = s["events"]
    clicks = [e for e in ev if e[3] == "click"]
    if not clicks:
        return None, "no_click_logged"
    if s["y"] == 1:
        ad_clicks = [e for e in clicks if e[5]]
        if ad_clicks:
            t_click = ad_clicks[0][0]
            presses = [e for e in ev if e[3] == "mousedown" and e[5] and e[0] <= t_click]
            if presses:
                return presses[-1][0], "ad_mousedown"
            return t_click, "ad_click"
        return clicks[-1][0], "fallback_last_click_no_ad_click"
    return clicks[-1][0], "last_click"


def cut(s, rule, delta, anchor):
    ev = s["events"]
    if rule == "committed":
        return truncate_at_click(ev, delta)
    if anchor is None:
        return ev
    return [e for e in ev if e[0] < anchor - delta]


def evaluate(sessions, rule, delta, anchors):
    keep, removed_samples, hit = [], {0: 0, 1: 0}, {0: 0, 1: 0}
    removed_moves, hit_moves = {0: 0, 1: 0}, {0: 0, 1: 0}
    approach_moves, hit_approach, approach_ms = {0: 0, 1: 0}, {0: 0, 1: 0}, {0: [], 1: []}
    dropped_pop, excluded = {0: 0, 1: 0}, {0: 0, 1: 0}
    for s in sessions:
        a, how = anchors[s["log_id"]]
        if rule == "ad_anchor_drop_noclick_pos" and s["y"] == 1 and how == "no_click_logged":
            excluded[1] += 1
            continue
        if rule == "ad_anchor_drop_noclick_both" and how == "no_click_logged":
            excluded[s["y"]] += 1
            continue
        ev = cut(s, rule, delta, a)
        n_rm = len(s["events"]) - len(ev)
        removed_samples[s["y"]] += n_rm
        hit[s["y"]] += int(n_rm > 0)
        # mousemoves are the samples that carry the approach; the click /
        # mousedown / mouseup triple sits at the press position.
        n_mv = sum(e[3] == "mousemove" for e in s["events"]) - sum(e[3] == "mousemove" for e in ev)
        removed_moves[s["y"]] += n_mv
        hit_moves[s["y"]] += int(n_mv > 0)
        # Approach samples: mousemoves inside [anchor - Δ, anchor), i.e. the
        # pre-press window the buffer exists to remove (post-press motion is
        # excluded from this count).
        anc = a
        if rule == "committed":
            clk = [e[0] for e in s["events"] if e[3] == "click"]
            anc = clk[-1] if (clk and delta > 0) else None
        if anc is not None:
            win = [e[0] for e in s["events"] if e[3] == "mousemove" and anc - delta <= e[0] < anc]
            approach_moves[s["y"]] += len(win)
            hit_approach[s["y"]] += int(len(win) > 0)
            if win:
                approach_ms[s["y"]].append(anc - win[0])
        f = compute_features(ev, 0)
        if f is None:
            dropped_pop[s["y"]] += 1
            continue
        ts = np.array([e[0] for e in ev], dtype=np.int64)
        ys = np.array([e[2] for e in ev], dtype=np.float64)
        m4 = m4_from_dist(ts, np.abs(ys - s["box"]["center_y"]))
        keep.append(([m4[c] for c in M4_SEVEN], f["total_mouse_length"], s["y"], n_rm))
    X7 = np.array([k[0] for k in keep], dtype=np.float64)
    mouse = np.array([[k[1]] for k in keep], dtype=np.float64)
    y = np.array([k[2] for k in keep], dtype=np.int64)
    rm_kept = np.array([k[3] for k in keep])
    a7, am = split_aucs(X7, y, N_SPLITS), split_aucs(mouse, y, N_SPLITS)
    a7h, amh = split_aucs(X7, y, N_SPLITS_SENS), split_aucs(mouse, y, N_SPLITS_SENS)
    by = lambda d: {"clicked": d[1], "not_clicked": d[0]}
    return {
        "rule": rule, "delta_ms": delta,
        "n_sessions": int(len(y)), "n_positive": int(y.sum()),
        "excluded_no_click": by(excluded),
        "dropped_lt3_samples": by(dropped_pop),
        "samples_removed": by(removed_samples),
        "sessions_hit": by(hit),
        "mousemoves_removed": by(removed_moves),
        "sessions_hit_mousemove": by(hit_moves),
        "approach_mousemoves_removed": by(approach_moves),
        "sessions_hit_approach": by(hit_approach),
        "median_samples_removed_kept_sessions": {
            "clicked": float(np.median(rm_kept[y == 1])), "not_clicked": float(np.median(rm_kept[y == 0]))},
        "m4_7_vertical": {"auc": _agg(a7), "auc_100_splits": {"mean": round(float(a7h.mean()), 4), "sd": round(float(a7h.std()), 4)}},
        "mouse_length": {"auc": _agg(am), "auc_100_splits": {"mean": round(float(amh.mean()), 4), "sd": round(float(amh.std()), 4)}},
        "paired_m4_7_minus_mouse": _agg(a7 - am),
    }


def main():
    upstream = verify_upstream_copy()
    sessions = load_sessions()
    assert all(s["box"] is not None for s in sessions)
    anchors = {s["log_id"]: find_anchor(s) for s in sessions}
    from collections import Counter
    anchor_counts = {
        "clicked": dict(Counter(how for s in sessions if s["y"] == 1 for how in [anchors[s["log_id"]][1]])),
        "not_clicked": dict(Counter(how for s in sessions if s["y"] == 0 for how in [anchors[s["log_id"]][1]])),
    }
    # How far before the ad click the ad press sits (ad_mousedown anchors).
    press_lead = []
    for s in sessions:
        a, how = anchors[s["log_id"]]
        if how == "ad_mousedown":
            t_click = next(e[0] for e in s["events"] if e[3] == "click" and e[5])
            press_lead.append(t_click - a)
    print(f"anchors: {json.dumps(anchor_counts)}")

    gate_row = evaluate(sessions, "committed", 500, anchors)
    gate = {"committed": GATE, "recomputed": {
        "m4_7_vertical": round(gate_row["m4_7_vertical"]["auc"]["mean"], 3),
        "baseline_mouse_length": round(gate_row["mouse_length"]["auc"]["mean"], 3),
        "n_sessions": gate_row["n_sessions"]}}
    gate["pass"] = gate["recomputed"] == GATE
    print(f"[repro gate] {json.dumps(gate)}")
    if not gate["pass"]:
        raise SystemExit("Committed-rule M4-7 (b) did not reproduce; refusing to report the sweep.")

    rows = []
    for rule in ("committed", "ad_anchor", "ad_anchor_drop_noclick_pos", "ad_anchor_drop_noclick_both"):
        for d in DELTAS:
            r = gate_row if (rule == "committed" and d == 500) else evaluate(sessions, rule, d, anchors)
            rows.append(r)
            print(f"{rule:<30} Δ={d:>4}  n={r['n_sessions']:>3} pos={r['n_positive']:>3}  "
                  f"M4-7 {r['m4_7_vertical']['auc']['mean']:.3f}±{r['m4_7_vertical']['auc']['sd']:.3f} "
                  f"(100: {r['m4_7_vertical']['auc_100_splits']['mean']:.3f})  "
                  f"mouse {r['mouse_length']['auc']['mean']:.3f}±{r['mouse_length']['auc']['sd']:.3f} "
                  f"(100: {r['mouse_length']['auc_100_splits']['mean']:.3f})  "
                  f"rm pos/neg {r['samples_removed']['clicked']}/{r['samples_removed']['not_clicked']}  "
                  f"approach rm pos/neg {r['approach_mousemoves_removed']['clicked']}/{r['approach_mousemoves_removed']['not_clicked']} "
                  f"hit {r['sessions_hit_approach']['clicked']}/{r['sessions_hit_approach']['not_clicked']}")

    summary = {
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "regime": "WILD, ACD",
        "config": {
            "data_dir": str(DATA), "target": "ad_clicked", "deltas_ms": DELTAS,
            "features": {"m4_7_vertical": M4_SEVEN, "mouse_length": ["total_mouse_length"]},
            "distance": "|y_t - ad_center_y|, ad box from the joint corner+center fit (m4_seven.ad_bbox)",
            "rules": {k: v for k, v in {
                "committed": "anchor = last click of any kind; Δ=0 means no truncation (run_analysis.truncate_at_click)",
                "ad_anchor": "ad-clicked: last in-target mousedown at/before the first in-target click, else that click, else last click of any kind; non-clicked: last click of any kind; keep ts < anchor - Δ (Δ=0 cuts at the anchor); no click logged -> session left whole",
                "ad_anchor_drop_noclick_pos": "ad_anchor minus ad-clicked sessions with no click event",
                "ad_anchor_drop_noclick_both": "ad_anchor minus sessions of either class with no click event",
            }.items()},
            "population_rule": ">= 3 mouse events with a valid extras.middle after truncation (run_analysis.compute_features)",
            "split_protocol": f"{N_SPLITS} stratified 70/30 train_test_split by session (random_state 0..{N_SPLITS-1}), plus {N_SPLITS_SENS} for sensitivity; StandardScaler + class-balanced LogisticRegression; mean ± population SD. Each row re-draws its splits on its own population.",
            "samples": "parse_log events (mouse events with x,y != 0). samples_removed / sessions_hit count every event cut (incl. the click/mousedown/mouseup at the press); mousemoves_removed / sessions_hit_mousemove count only mousemove events (incl. post-press motion); approach_mousemoves_removed / sessions_hit_approach count mousemoves in [anchor - Δ, anchor) only. Counted over all sessions entering the rule, before the >=3 drop.",
        },
        "anchors": {"counts": anchor_counts,
                    "ad_press_to_ad_click_ms": {"n": len(press_lead), "p50": float(np.median(press_lead)),
                                                "p90": float(np.percentile(press_lead, 90))}},
        "repro_gate": gate,
        "upstream_copy_check": upstream,
        "rows": rows,
        "provenance": {"producer": "analysis/attcur-validation/m4_seven_buffer.py",
                       "approach_retreat_git_sha": _git_sha(HERE.parent.parent)},
    }
    out = HERE / "output" / "m4_seven_buffer_summary.json"
    out.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
