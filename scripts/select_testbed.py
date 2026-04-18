"""Pass 2: select + label + classify candidates for the AR signal testbed.

Reads AF's trial-scores.csv → picks top N with per-participant diversity →
copies PNGs from /Volumes/andyed → invokes AF's organic-bbox extractor →
builds AR replay bundles (with four-class label inference) → classifies
trials into pedagogical groups → writes curation.json + docs/CURATION.md.

Run:  python3 scripts/select_testbed.py [--n 80] [--cap 3]
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

AR_ROOT = Path(__file__).resolve().parent.parent
AF_ROOT = AR_ROOT.parent / "attentional-foraging"
SCORES = AF_ROOT / "AdSERP/data/trial-scores.csv"
PNG_VOL = Path("/Volumes/andyed/Downloads/adserp-dataset/full-page-screenshots")
PNG_LOCAL = AF_ROOT / "AdSERP/data/full-page-screenshots"
ORGANIC_DIR = AF_ROOT / "AdSERP/data/organic-boundary-data"
SITE_DATA = AR_ROOT / "site/replay/data"
TRIALS_DIR = SITE_DATA / "trials"
PNG_OUT = SITE_DATA / "png"
CURATION_JSON = AR_ROOT / "site/replay/data/curation.json"
CURATION_MD = AR_ROOT / "docs/CURATION.md"

sys.path.insert(0, str(AR_ROOT / "scripts"))
import build_replay_trial as brt  # noqa: E402


def select_diverse_top(scores_csv: Path, n: int, cap_per_participant: int) -> list[str]:
    rows = sorted(
        (r for r in csv.DictReader(scores_csv.open())),
        key=lambda r: float(r["score"]),
        reverse=True,
    )
    selected: list[str] = []
    p_count: Counter = Counter()
    for r in rows:
        if len(selected) >= n:
            break
        pid = r["trial_id"].split("-")[0]
        if p_count[pid] >= cap_per_participant:
            continue
        selected.append(r["trial_id"])
        p_count[pid] += 1
    return selected


def copy_screenshots(trial_ids: list[str]) -> int:
    PNG_LOCAL.mkdir(parents=True, exist_ok=True)
    n_copied = 0
    for tid in trial_ids:
        local = PNG_LOCAL / f"{tid}.png"
        if local.exists():
            continue
        src = PNG_VOL / f"{tid}.png"
        if not src.exists():
            print(f"  WARN: {tid}.png missing on volume", file=sys.stderr)
            continue
        shutil.copy2(src, local)
        n_copied += 1
    return n_copied


def extract_organics(trial_ids: list[str]) -> int:
    missing = [t for t in trial_ids if not (ORGANIC_DIR / f"{t}.json").exists()]
    if not missing:
        return 0
    cmd = ["uv", "run", "python", "scripts/extract_organic_bboxes.py", *missing]
    print(f"  extracting organics for {len(missing)} trials...")
    res = subprocess.run(cmd, cwd=AF_ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr, file=sys.stderr)
        raise RuntimeError("organic extraction failed")
    return len(missing)


def build_bundles(trial_ids: list[str]) -> list[dict]:
    TRIALS_DIR.mkdir(parents=True, exist_ok=True)
    PNG_OUT.mkdir(parents=True, exist_ok=True)
    bundles = []
    for tid in trial_ids:
        b = brt.build_trial(tid)
        if b is None:
            print(f"  SKIP {tid}: missing input")
            continue
        (TRIALS_DIR / f"{tid}.json").write_text(json.dumps(b))
        bundles.append(b)
    return bundles


# ── Group classification ────────────────────────────────────────────────
def trial_features(b: dict) -> dict:
    """Per-trial summary for group assignment."""
    s = b["_meta"]["label_summary"]
    n_clk = s.get("CLICKED", 0)
    n_def = s.get("DEFERRED", 0)
    n_rej = s.get("EVALUATED_REJECTED", 0)
    n_not = s.get("NOT_APPROACHED", 0)
    classes_active = sum(1 for k in (n_clk, n_def, n_rej) if k > 0)
    # Boundary signal: any approached AOI with dwell in [100, 250] ms (close to threshold)
    near_threshold = 0
    for kind in b["aoi_labels"].values():
        for it in kind:
            if it["label"] in ("DEFERRED", "EVALUATED_REJECTED"):
                if 100 <= it["total_dwell_ms"] <= 250:
                    near_threshold += 1
    # Cursor-gaze divergence: count of organic AOIs gaze-fixated but cursor-NOT_APPROACHED
    gaze_only = 0
    for it in b["aoi_labels"].get("organic_result", []):
        if it["label"] != "NOT_APPROACHED":
            continue
        idx = it["bbox_index"]
        bbox = b["bboxes"]["organic_result"][idx]
        bx, by = bbox["location"]["x"], bbox["location"]["y"]
        bw, bh = bbox["size"]["width"], bbox["size"]["height"]
        for f in b["fixations"]:
            if bx <= f["x"] <= bx + bw and by <= f["y"] <= by + bh:
                if f["duration"] >= 200:
                    gaze_only += 1
                    break
    return {
        "n_clicked": n_clk,
        "n_deferred": n_def,
        "n_rejected": n_rej,
        "n_not_approached": n_not,
        "classes_active": classes_active,
        "near_threshold": near_threshold,
        "gaze_only_aois": gaze_only,
        "duration_ms": b["duration_ms"],
        "n_cursor": b["_meta"]["n_cursor"],
        "n_fixations": b["_meta"]["n_fixations"],
    }


def classify(bundles: list[dict], target_per_group: dict[str, int]) -> dict:
    """Assign trials to pedagogical groups. Trials may match multiple groups but
    are placed in their best-fit (in priority order)."""
    feats = {b["trial_id"]: trial_features(b) for b in bundles}
    bundle_by_id = {b["trial_id"]: b for b in bundles}
    used: set[str] = set()
    groups: dict[str, list[dict]] = defaultdict(list)

    def query(b):
        return (b.get("task", "").split("|")[-1].strip()) or b["trial_id"]

    def add(group: str, tid: str, caption: str):
        groups[group].append({"trial_id": tid, "caption": caption})
        used.add(tid)

    # Group E — Multi-AOI drama (3 active label classes in one trial). Highest priority.
    candidates_e = sorted(
        (t for t, f in feats.items() if f["classes_active"] >= 3),
        key=lambda t: (feats[t]["n_deferred"], feats[t]["n_rejected"], feats[t]["n_cursor"]),
        reverse=True,
    )
    for tid in candidates_e[:target_per_group["E"]]:
        f = feats[tid]
        cap = f"{f['n_clicked']} CLK + {f['n_deferred']} DEF + {f['n_rejected']} REJ in one SERP — comparative inference"
        add("E", tid, cap)

    # Group B-DEF — Canonical DEFERRED (retreat-and-return clearly visible)
    candidates_def = sorted(
        (t for t, f in feats.items() if t not in used and f["n_deferred"] >= 1),
        key=lambda t: (feats[t]["n_deferred"], feats[t]["n_cursor"]),
        reverse=True,
    )
    for tid in candidates_def[:target_per_group["B-DEF"]]:
        f = feats[tid]
        cap = f"{f['n_deferred']} DEFERRED AOI{'s' if f['n_deferred'] > 1 else ''} — cursor entered, left, returned"
        add("B-DEF", tid, cap)

    # Group B-REJ — Canonical EVALUATED_REJECTED (approach + retreat, no return)
    candidates_rej = sorted(
        (t for t, f in feats.items() if t not in used and f["n_rejected"] >= 2 and f["n_deferred"] == 0),
        key=lambda t: (feats[t]["n_rejected"], feats[t]["n_cursor"]),
        reverse=True,
    )
    for tid in candidates_rej[:target_per_group["B-REJ"]]:
        f = feats[tid]
        cap = f"{f['n_rejected']} EVAL-REJ AOIs — evaluated and dropped, no re-approach"
        add("B-REJ", tid, cap)

    # Group C — Boundary cases (dwell close to 100ms threshold)
    candidates_c = sorted(
        (t for t, f in feats.items() if t not in used and f["near_threshold"] >= 1),
        key=lambda t: feats[t]["near_threshold"],
        reverse=True,
    )
    for tid in candidates_c[:target_per_group["C"]]:
        f = feats[tid]
        cap = f"{f['near_threshold']} AOI(s) with dwell near the 100ms classification threshold"
        add("C", tid, cap)

    # Group D — Cursor-vs-gaze divergence
    candidates_d = sorted(
        (t for t, f in feats.items() if t not in used and f["gaze_only_aois"] >= 2),
        key=lambda t: feats[t]["gaze_only_aois"],
        reverse=True,
    )
    for tid in candidates_d[:target_per_group["D"]]:
        f = feats[tid]
        cap = f"{f['gaze_only_aois']} AOI(s) gaze-fixated ≥200ms but cursor never entered — cursor-only would miss them"
        add("D", tid, cap)

    # Group A — Trivial: 1 click, no other approached AOIs, short duration
    candidates_a = sorted(
        (t for t, f in feats.items() if t not in used and f["n_clicked"] == 1 and f["n_deferred"] == 0 and f["n_rejected"] == 0),
        key=lambda t: feats[t]["duration_ms"],
    )
    for tid in candidates_a[:target_per_group["A"]]:
        f = feats[tid]
        cap = f"Drive-through: 1 CLICKED + {f['n_not_approached']} not approached, {f['duration_ms']/1000:.1f}s"
        add("A", tid, cap)

    return {"groups": dict(groups), "features": feats, "bundle_query": {b["trial_id"]: query(b) for b in bundles}}


def write_curation_md(curation: dict, n_pool: int) -> None:
    CURATION_MD.parent.mkdir(parents=True, exist_ok=True)
    g = curation["groups"]
    feats = curation["features"]
    queries = curation["bundle_query"]

    GROUP_DESCRIPTIONS = {
        "A":     ("Trivial calls", "Cursor walks to one result and clicks. The label assignment is unambiguous — useful as a sanity check that the inference logic agrees on easy cases."),
        "B-DEF": ("Canonical DEFERRED", "Cursor enters a result, retreats, then returns. The retreat-and-return is the inference fingerprint that distinguishes 'still considering' from 'already rejected'."),
        "B-REJ": ("Canonical EVALUATED-REJECTED", "Cursor enters a result, retreats, and never comes back during the trial. Multiple such AOIs in one trial show the rejection pattern at scale."),
        "C":     ("Boundary cases", "AOIs with dwell duration close to the 100ms classification threshold. Small changes in the threshold flip the label — the testbed cases that motivate threshold-sensitivity analysis."),
        "D":     ("Cursor-vs-gaze divergence", "AOIs heavily fixated by gaze (≥200ms) where the cursor never entered. A cursor-only classifier marks these NOT_APPROACHED, but the gaze evidence says they were considered. Diagnostic for cursor-as-attention-proxy assumptions."),
        "E":     ("Multi-AOI dramas", "Trials with 3+ active label classes (CLICKED + DEFERRED + EVALUATED-REJECTED) in one SERP. Lets you compare inference signatures side-by-side within one query session."),
    }

    lines = [
        "# AR Replay Signal Testbed — Curation Rubric",
        "",
        f"_Generated by `scripts/select_testbed.py`. Pool: top **{n_pool}** trials from `attentional-foraging/AdSERP/data/trial-scores.csv` after per-participant diversity capping. Final testbed: **{sum(len(v) for v in g.values())}** trials across {len(g)} groups._",
        "",
        "## What this is",
        "",
        "This is a **signal testbed**, not a showcase. Each trial is a tagged demonstration of the four-class taxonomy inference task: SERP screenshot + cursor + per-AOI labels overlaid. The viewer renders what a cursor-only classifier emits on this cursor stream.",
        "",
        "Per-AOI labels are **predictions**, not ground truth. The classifier uses cursor + AOI bboxes only; gaze and pupil are shown for context. If you disagree with a label on a specific trial, that trial belongs in Group F (failure modes) and the inference logic needs work.",
        "",
        "## Inference: M5 (primary) + bbox-episode heuristic (secondary)",
        "",
        "Two classifiers run on every organic AOI; both are reported in the trial JSON and in the viewer.",
        "",
        "### M5 (primary for organic AOIs)",
        "",
        "Logistic regression on the M4 nine-feature approach set, **trained against NB22 gaze-derived labels** (1916 deferred / 439 eval-rejected non-click episodes across 47 AdSERP participants). Trained in `attentional-foraging/scripts/m5_cursor_only_taxonomy.py`; coefficients shipped at `scripts/models/m5_final_model.json`.",
        "",
        "- **LOSO AUC:** 0.794 (median per-participant 0.794, IQR [0.707, 0.869])",
        "- **Operating threshold:** p* = 0.395 (Youden-J on out-of-fold predictions)",
        "- **Predicted-deferred precision:** 90.2%",
        "- **Features (cursor-only, no gaze, no scroll):** `min_dist`, `mean_dist`, `final_dist`, `retreat_dist`, `dwell_in_proximity_ms`, `mean_approach_velocity`, `max_approach_velocity`, `direction_changes`, `frac_decreasing` — all geometric on cursor `pageY` relative to AOI y-center.",
        "- **Domain:** organic results only (M5's training population). Ad AOIs fall back to the heuristic.",
        "- **Approached-by-M5 definition:** `min_dist < 100px` (cursor came within 100px of the AOI's y-center). More permissive than the heuristic's bbox-containment definition.",
        "",
        "### Bbox-episode heuristic (secondary, all AOIs)",
        "",
        "Walk the cursor stream against the AOI bbox. An **episode** is an enter→exit traversal where dwell ≥ 100ms (filters drive-by crossings). Label rules:",
        "",
        "- `CLICKED` — any episode contains a click event inside the bbox.",
        "- `DEFERRED` — ≥2 kept episodes (cursor literally re-entered the bbox).",
        "- `EVALUATED_REJECTED` — exactly 1 kept episode.",
        "- `NOT_APPROACHED` — 0 kept episodes.",
        "",
        "### Final canonical label (per AOI)",
        "",
        "1. `CLICKED` if any bbox episode contains a click event (both classifiers agree on this case).",
        "2. For organic AOIs: M5 prediction (DEFERRED if proba ≥ 0.395, else EVALUATED_REJECTED). NOT_APPROACHED if min_dist ≥ 100px.",
        "3. For ad AOIs: bbox-episode heuristic.",
        "",
        "### Why surface both",
        "",
        "M5 and the heuristic disagree often (~80% of approached organic AOIs in spot checks). The disagreement is meaningful: M5 sees \"deferred-like signature\" (close approach + dwell + retreat), the heuristic sees \"literal re-approach\" (cursor physically re-entered the bbox). Both are valid framings of the four-class taxonomy. Group D and the per-AOI badges (`≠ heur:LABEL` chevron) surface the disagreements directly so a reviewer can decide which framing is more defensible per case.",
        "",
        "## Regime tag",
        "",
        "**`[CURSOR-ONLY]` algorithm running on `[LAB]` data, supervision was `[LAB, NB22 gaze-derived]`.**",
        "",
        "Per the [LAB/WILD convention](../CLAUDE.md#role-in-the-cikm-paper-the-lab--wild-bridge), the four-class taxonomy is currently `[LAB]`-only because the canonical version is gaze-derived. M5 is the named cursor-only-bootstrap that earns `[BOTH]` *if* its agreement with the gaze-derived ground truth is high enough; M5's LOSO AUC of 0.794 against NB22 is the published evidence. The replay viewer is the visual inspection tool for that bootstrap — every disagreement between M5 and the heuristic on a specific AOI is a candidate for human adjudication.",
        "",
        "## Selection rubric",
        "",
        "1. **Pass 1** (`scripts/score_trials.py` in attentional-foraging) scores every trial on cursor-only features:",
        "   ```",
        "   score = 0.20 * normalize(n_mousemove,    50, 400)",
        "         + 0.25 * normalize(distinct_y_bands, 2,   8)",
        "         + 0.25 * normalize(y_band_revisits,  0,   6)",
        "         + 0.15 * normalize(duration_ms,   5000, 25000)",
        "         + 0.15 * has_click",
        "         × (1 - 0.5 * pupil_dropout_rate)",
        "   ```",
        "   `has_click` is 1.0 for every trial in AdSERP (protocol-required) — kept for transparency but doesn't discriminate.",
        "",
        f"2. **Pass 2** (this script) takes the top **{n_pool}** with a per-participant cap, extracts organic AOI bboxes, builds replay bundles with M5 + heuristic labels, and assigns each trial to the most diagnostic group it qualifies for (priority order: E → B-DEF → B-REJ → C → D → A).",
        "",
        "## Groups",
        "",
    ]
    for key in ("E", "B-DEF", "B-REJ", "C", "D", "A"):
        title, desc = GROUP_DESCRIPTIONS[key]
        items = g.get(key, [])
        lines.append(f"### Group {key} — {title} ({len(items)} trials)")
        lines.append("")
        lines.append(desc)
        lines.append("")
        if not items:
            lines.append("_No trials qualified at the current selection thresholds._")
            lines.append("")
            continue
        lines.append("| Trial | Query | Caption |")
        lines.append("|---|---|---|")
        for it in items:
            tid = it["trial_id"]
            q = queries.get(tid, tid)[:60]
            lines.append(f"| [`{tid}`](../site/replay/trials/{tid}.html) | {q} | {it['caption']} |")
        lines.append("")

    lines += [
        "## Group F — Failure modes (manual)",
        "",
        "Trials where the inference probably gets it wrong. Populated manually after reviewing groups B-DEF, B-REJ, C, D and noticing labels that disagree with the visible cursor pattern. None auto-assigned in this pass.",
        "",
        "## Extended candidate pool",
        "",
        f"All {n_pool} candidate trials are visible at `/replay/index.html`. The {sum(len(v) for v in g.values())} group-assigned trials are highlighted there. The rest constitute an unstructured browseable set for spot-checking.",
        "",
    ]
    CURATION_MD.write_text("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=80, help="candidate pool size (default 80)")
    ap.add_argument("--cap", type=int, default=3, help="max trials per participant (default 3)")
    args = ap.parse_args()

    print(f"[1/6] Selecting top {args.n} (cap {args.cap}/participant)...")
    selected = select_diverse_top(SCORES, args.n, args.cap)
    p_count = Counter(t.split("-")[0] for t in selected)
    print(f"      selected {len(selected)} trials across {len(p_count)} participants")

    print(f"[2/6] Copying screenshots from /Volumes/andyed...")
    n_copied = copy_screenshots(selected)
    print(f"      copied {n_copied} new PNGs (rest already cached)")

    print(f"[3/6] Extracting organic bboxes...")
    n_extracted = extract_organics(selected)
    print(f"      extracted {n_extracted} new (rest already cached)")

    print(f"[4/6] Building replay bundles + per-AOI labels...")
    bundles = build_bundles(selected)
    print(f"      built {len(bundles)} bundles")

    print(f"[5/6] Classifying into groups...")
    target_per_group = {"A": 5, "B-DEF": 6, "B-REJ": 6, "C": 5, "D": 5, "E": 6}
    curation = classify(bundles, target_per_group)
    CURATION_JSON.write_text(json.dumps({k: v for k, v in curation.items() if k != "features"}))
    for grp, items in curation["groups"].items():
        print(f"      Group {grp:6s}: {len(items)} trials")

    print(f"[6/6] Writing docs/CURATION.md...")
    write_curation_md(curation, len(selected))
    print(f"      wrote {CURATION_MD}")

    print("\nDone. Run `python3 scripts/build_replay_pages.py` to refresh the viewer index.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
