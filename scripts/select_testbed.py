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
import textwrap
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
import m5_inference  # noqa: E402  (every M5 number in CURATION.md is read from it)


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


# ── SERP composition clustering ─────────────────────────────────────────
COMPOSITION_KEYS = ("top_and_side", "top_only", "side_only", "organic_dominant")

COMPOSITION_TITLES = {
    "top_and_side":     ("Top + side ads", "dd_top block AND dd_right rail present — densest ad surfacing"),
    "top_only":         ("Top ads only",   "dd_top block, no dd_right rail"),
    "side_only":        ("Side ads only",  "dd_right rail, no dd_top block"),
    "organic_dominant": ("Organic-dominant", "no dd_top, no dd_right (native_ad inline only)"),
}


def composition_of(bboxes_dict: dict) -> str:
    """Map a bboxes dict to one of COMPOSITION_KEYS using dd_top/dd_right presence."""
    has_top = bool(bboxes_dict.get("dd_top"))
    has_side = bool(bboxes_dict.get("dd_right"))
    if has_top and has_side:
        return "top_and_side"
    if has_top:
        return "top_only"
    if has_side:
        return "side_only"
    return "organic_dominant"


def compute_population_shares() -> dict:
    """Tally composition cluster across all organic-boundary JSONs in AdSERP."""
    counts = {k: 0 for k in COMPOSITION_KEYS}
    n = 0
    for p in ORGANIC_DIR.glob("*.json"):
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        counts[composition_of(d)] += 1
        n += 1
    return {"counts": counts, "total": n}


def composition_for_bundles(bundles: list[dict]) -> dict[str, list[str]]:
    """Group trial_ids in the audit pool by composition cluster."""
    by_cluster: dict[str, list[str]] = {k: [] for k in COMPOSITION_KEYS}
    for b in bundles:
        by_cluster[composition_of(b["bboxes"])].append(b["trial_id"])
    return by_cluster


# ── Group classification ────────────────────────────────────────────────
def trial_features(b: dict) -> dict:
    """Per-trial summary for group assignment.

    Uses HEURISTIC counts (bbox re-entry) — the same counts `label` now
    carries as the canonical class (2026-09-19 decision: the heuristic is
    primary, M5 is a secondary score). Kept as its own read here anyway
    because the heuristic still cleanly distinguishes DEFERRED (≥2
    episodes) from EVALUATED_REJECTED (1 episode) at the episode level,
    which is what group assignment wants, independent of whichever M5
    score/threshold happens to be loaded.

    This function is only for finding canonical exemplars to surface in
    pedagogical groups; it does not touch M5 at all.
    """
    n_clk = n_def = n_rej = n_not = 0
    for kind in b["aoi_labels"].values():
        for it in kind:
            h = it.get("heuristic_label", it.get("label"))
            if h == "CLICKED":           n_clk += 1
            elif h == "DEFERRED":        n_def += 1
            elif h == "EVALUATED_REJECTED": n_rej += 1
            else:                        n_not += 1
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


def alignment_disclosure(curation: dict, composition: dict | None,
                         suspect_tids: set[str]) -> str:
    """Blockquote naming the pooled trials on AllSERP's alignment-exclusion list.

    Generated rather than hand-written: the list is AF's and grows, the pool
    is re-selected here, and a disclosure that has to be re-typed after every
    selection is a disclosure that silently stops being true.
    """
    if not composition:
        return ""
    pool = composition.get("audit_pool", {})
    bucket_of = {tid: k for k, tids in pool.items() for tid in tids}
    listed = [t for t in sorted(bucket_of) if t in suspect_tids]
    if not listed:
        return ""
    group_of = {it["trial_id"]: key
                for key, items in curation["groups"].items() for it in items}
    n_testbed = sum(len(v) for v in curation["groups"].values())
    excl = brt.load_alignment_exclusions()
    date = excl.get("date") or "undated"
    all_tids = excl.get("tids", [])

    parts = []
    for tid in listed:
        where = (f"Group {group_of[tid]}, and the `{bucket_of[tid]}` composition bucket"
                 if tid in group_of else
                 f"`{bucket_of[tid]}` composition bucket, not in the {n_testbed}")
        parts.append(f"[`{tid}`](../site/replay/trials/{tid}.html) ({where})")
    if len(parts) == 1:
        named, subject = parts[0], "It is a shift-periodic page"
    else:
        named = ", ".join(parts[:-1]) + " and " + parts[-1]
        subject = "These are shift-periodic pages"
    n = len(listed)
    body = (
        f"**{n} pooled trial{'s are' if n != 1 else ' is'} on AllSERP's "
        f"alignment-exclusion list ({date}).** The testbed predates that list "
        "and was not re-selected against it, so the overlap is stated here "
        f"rather than silently carried: {named}. {subject} with pathological "
        "widget rendering where a one-slot-wrong AOI lattice cannot be ruled "
        "out geometrically, so AllSERP drops them from typed-flavor feature "
        "derivation. Their replay pages carry an alignment-suspect badge and "
        "stay published as demonstrations of the inference task; **do not read "
        "their per-AOI labels as evidence about a specific result**, because "
        "the AOI the label is attached to may be the wrong one. The full "
        f"{len(all_tids)}-trial list is the authority: "
        "`attentional-foraging/data/aoi-typed/alignment-exclusions.json`."
    )
    return textwrap.fill(body, width=76, initial_indent="> ",
                         subsequent_indent="> ", break_on_hyphens=False)


def m5_disagreement_rate(bundles: list[dict]) -> float | None:
    """Share of M5-scored organic AOIs where M5's label at its own operating
    threshold disagrees with the observed (canonical) label.

    Reported in CURATION.md. It moves whenever the model does, so it is
    measured on the bundles being documented rather than quoted from an
    old spot check.
    """
    n = n_diff = 0
    for b in bundles:
        for it in b["aoi_labels"].get("organic_result", []):
            if it.get("m5_proba") is None:
                continue
            n += 1
            if it["m5_label"] != it["label"]:
                n_diff += 1
    return n_diff / n if n else None


def _operating_points_table(clf: "m5_inference.M5Classifier") -> list[str]:
    """Markdown table rows for the model's `operating_points` block.

    Empty list when the loaded model doesn't carry one (v2-only) — the
    caller falls back to _v2_only_operating_row() in that case.
    """
    ops = clf.operating_points()
    if not ops:
        return []
    lines = [
        "| Threshold | Predicted-deferred share | Deferred precision/recall | Rejected precision/recall |",
        "|---|---|---|---|",
    ]
    for row in ops:
        method = row.get("method", "")
        tag = f" ({method})" if method else ""
        lines.append(
            f"| {row['threshold']:.3f}{tag} | {100 * row['predicted_deferred_share']:.1f}% | "
            f"{100 * row['deferred_precision']:.1f}% / {100 * row['deferred_recall']:.1f}% | "
            f"{100 * row['rejected_precision']:.1f}% / {100 * row['rejected_recall']:.1f}% |"
        )
    return lines


def _v2_only_operating_row(clf: "m5_inference.M5Classifier") -> list[str]:
    """Fallback table (one Youden row) for a model with no `operating_points`
    block. v2's `loso_youden_j` only carries the deferred-side precision/
    recall directly; the rejected side is derived from TPR/FPR when the
    class counts are available, else printed as 'not recorded' rather than
    silently omitted."""
    yj = clf.model.get("loso_youden_j") or {}
    if not yj:
        return []
    n_def = clf.model.get("n_deferred")
    n_rej = clf.model.get("n_eval_rej")
    tpr, fpr = yj.get("tpr"), yj.get("fpr")
    rej_prec = rej_rec = "not recorded"
    if tpr is not None and fpr is not None and n_def and n_rej:
        fn = n_def * (1 - tpr)
        tn = n_rej * (1 - fpr)
        rej_rec = f"{100 * (1 - fpr):.1f}%"
        if (tn + fn) > 0:
            rej_prec = f"{100 * tn / (tn + fn):.1f}%"
    prec, rec = yj.get("precision"), yj.get("recall")
    def_cell = f"{100 * prec:.1f}% / {100 * rec:.1f}%" if prec is not None and rec is not None else "not recorded"
    thr = yj.get("threshold", clf.threshold)
    return [
        "| Threshold | Predicted-deferred share | Deferred precision/recall | Rejected precision/recall |",
        "|---|---|---|---|",
        f"| {thr:.3f} (Youden-J) | not recorded | {def_cell} | {rej_prec} / {rej_rec} |",
    ]


def _calibration_line(clf: "m5_inference.M5Classifier") -> str | None:
    """One line stating the model's calibration verdict, or None when the
    model carries no `calibration` block (v2)."""
    cal = clf.calibration()
    if not cal:
        return None
    verdict = cal.get("verdict", "no verdict recorded")
    brier = cal.get("brier_score", cal.get("brier"))
    gap = cal.get("max_abs_gap_mean_score_minus_observed_rate", cal.get("max_abs_gap"))
    n_bins = cal.get("n_bins", len(cal.get("bins", [])) or None)
    detail = []
    if brier is not None:
        detail.append(f"Brier {brier:.3f}")
    if gap is not None:
        detail.append(f"max |gap| {gap:.3f}")
    if n_bins:
        detail.append(f"{n_bins} equal-count bins")
    suffix = f" ({', '.join(detail)})" if detail else ""
    return f"- **Calibration:** {verdict}{suffix}."


def write_curation_md(curation: dict, n_pool: int, composition: dict | None = None,
                      disagreement: float | None = None) -> None:
    CURATION_MD.parent.mkdir(parents=True, exist_ok=True)
    g = curation["groups"]
    feats = curation["features"]
    queries = curation["bundle_query"]

    # Every M5 number below is read out of the deployed model file. Until
    # 2026-09-18 this document hand-typed a 0.395 threshold that matched
    # neither shipped model: a constant transcribed into prose has no way
    # to notice a model swap, and nothing downstream checks it.
    clf = m5_inference.M5Classifier()
    model_name = clf.model_path.name
    n_feat = len(clf.features)
    thr = clf.threshold
    auc = clf.loso_auc
    yj = clf.model.get("loso_youden_j", {})
    prov = clf.model.get("provenance", {})
    gate = prov.get("gate", {})
    # v2's gate is flat ({abs_diff, tolerance, sidecar, ...}); v3's nests per-
    # check results under "checks" (cursor-only / bands-only / combined) with
    # no top-level abs_diff. Prefer the combined check (the shipped model's
    # own number) when present, so the sentence doesn't print "diff nan".
    gate_abs_diff = gate.get("abs_diff")
    if gate_abs_diff is None:
        checks = gate.get("checks", {})
        combined = checks.get("cursor_M4_7_plus_bands_3") or next(iter(checks.values()), {})
        gate_abs_diff = combined.get("abs_diff", float("nan"))
    model_date = (prov.get("generated_utc") or "")[:10] or "undated"
    producer = prov.get("producer", "attentional-foraging/scripts/export_m5_cursor_only.py")
    feat_list = ", ".join(f"`{f}`" for f in clf.features)
    n_feat_word = {7: "seven", 9: "nine", 10: "ten", 11: "eleven"}.get(n_feat, str(n_feat))
    ops_table = _operating_points_table(clf) or _v2_only_operating_row(clf)
    calibration_line = _calibration_line(clf)
    suspect_tids = set(brt.load_alignment_exclusions().get("tids", []))
    disagreement_txt = (f"{100 * disagreement:.0f} %" if disagreement is not None
                        else "a large share")
    banner = textwrap.fill(
        f"**Model-version notice ({model_date}).** Replay labels are the "
        "observed bbox-episode class, not a model prediction. "
        f"M5's continuous deferred score comes from `scripts/models/{model_name}` "
        f"({n_feat_word} features, cursor-only typed stream, LOSO {auc:.3f}). "
        "M5 emits a score, not a label (2026-09-19 decision: at v2's own "
        "Youden threshold a REJECTED call was right only 48.5% of the time) "
        "\u2014 the nine-feature May model is retired to "
        "`m5_final_model.legacy-2026-05-02.json`; replay bundles built before "
        "that date carry its scores until rebuilt. See "
        "[Current evidence](current-evidence.md), the "
        "[claims inventory](validation/2026-09-18-claims-inventory.md) \u00a70, and "
        "[attribution lineage](bbox-attribution-lineage.md).",
        width=76, initial_indent="> ", subsequent_indent="> ",
        break_on_hyphens=False)  # never split a hyphenated path inside a code span

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
        banner,
        "",
        f"_Generated by `scripts/select_testbed.py`. Pool: top **{n_pool}** trials from `attentional-foraging/AdSERP/data/trial-scores.csv` after per-participant diversity capping. Final testbed: **{sum(len(v) for v in g.values())}** trials across {len(g)} groups._",
        "",
    ]
    disclosure = alignment_disclosure(curation, composition, suspect_tids)
    if disclosure:
        lines += [disclosure, ""]
    lines += [
        "## What this is",
        "",
        "This is a **signal testbed**, not a showcase. Each trial is a tagged demonstration of the four-class taxonomy inference task: SERP screenshot + cursor + per-AOI labels overlaid. The viewer renders the observed class alongside a continuous cursor-only deferred score.",
        "",
        "Per-AOI `label`s are the **observed** bbox-episode class \u2014 cursor re-entry, not a model call. M5's `deferred_score` is a **prediction**, reported alongside the observed label rather than folded into it. Gaze and pupil are shown for context, not used by either signal. If you disagree with the observed label on a specific trial, that trial belongs in Group F (failure modes) and the episode heuristic needs work; if you disagree with M5's score, that's a modeling question, not a labeling bug.",
        "",
        "## Inference: bbox-episode heuristic (canonical label) + M5 deferred score (secondary)",
        "",
        "Two signals are computed for every organic AOI; both are reported in the trial JSON and in the viewer. The heuristic assigns the canonical `label` for every AOI kind. M5 contributes a continuous score for organic AOIs only \u2014 it does not assign the label.",
        "",
        "### Bbox-episode heuristic (canonical, all AOIs)",
        "",
        "Walk the cursor stream against the AOI bbox. An **episode** is an enter\u2192exit traversal where dwell \u2265 100ms (filters drive-by crossings). Label rules \u2014 this is the observed class, `label` in the bundle:",
        "",
        "- `CLICKED` \u2014 any episode contains a click event inside the bbox.",
        "- `DEFERRED` \u2014 \u22652 kept episodes (cursor literally re-entered the bbox).",
        "- `EVALUATED_REJECTED` \u2014 exactly 1 kept episode.",
        "- `NOT_APPROACHED` \u2014 0 kept episodes.",
        "",
        "### M5 deferred score (secondary, organic AOIs only)",
        "",
        f"Logistic regression on the M4 {n_feat_word}-feature approach set, **trained against NB22 gaze-derived labels** ({clf.model.get('n_deferred', 0):,} deferred / {clf.model.get('n_eval_rej', 0):,} eval-rejected approached non-click rows across 47 AdSERP participants, `typed` attribution, cursor-only stream, press-anchored 500 ms buffer). Trained in `{producer}`; coefficients shipped at `scripts/models/{model_name}`.",
        "",
        f"- **LOSO AUC:** {auc:.3f} pooled (fold mean {clf.model.get('loso_fold_auc_mean', float('nan')):.3f} \u00b1 {clf.model.get('loso_fold_auc_sd', float('nan')):.3f}) `[LAB, AdSERP, typed, cursor-only]` \u2014 the {model_date} retrain, gated to reproduce `{gate.get('sidecar', 'm4_cursor_only_downstream/summary.json')}` \u00a74.3 to {gate.get('tolerance', 1e-6):g} (diff {gate_abs_diff:g}). *Previously: 0.769 / p\\* = 0.489 / precision 87.8 % on nine features from the 2026-05-02 `m5_final_model.json` (now `m5_final_model.legacy-2026-05-02.json`); that stream selected rows by fixation and measured gaze-to-cursor distance, so it carried part of the gaze-return label and was not the runtime measurement \u2014 the 0.769 \u2192 {auc:.3f} drop is the removal of that term, not a regression (`attentional-foraging/docs/ablations/deferred_drop_decomposition.md`).*",
        f"- **Features:** {feat_list} \u2014 the cursor terms are all geometric on cursor `pageY` relative to AOI y-center; `final_dist` and `retreat_dist` are still computed by the extractor but excluded from the model (click-buffer screen, CIKM \u00a73.4). Viewport-band terms (`vt_top`/`vt_mid`/`vt_bot`, when present) are cumulative ms the AOI's centre spent in the top/mid/bottom third of the viewport (`edmonds-2026-vpbands-v1`).",
        "- **Domain:** organic results only (M5's training population). Ad AOIs get no M5 score; their `label` is the heuristic's, same as organics.",
        "- **Approached-by-M5 definition:** `min_dist < 100px` (cursor came within 100px of the AOI's y-center). More permissive than the heuristic's bbox-containment definition \u2014 M5 can score an AOI the heuristic calls NOT_APPROACHED.",
        f"- **The instrument emits a score, not a label** (2026-09-19 decision). At v2's own Youden threshold (p\\* = 0.477), a predicted-DEFERRED call was right 78.1 % of the time but a predicted-REJECTED call was right only 48.5 % \u2014 worse than a coin flip's complement (from TPR 0.7276 / FPR 0.4425 on 6,800 deferred / 3,132 rejected). `m5_label` (DEFERRED/EVALUATED_REJECTED at the model's own `operating_threshold` p\\* = {thr:.3f}) is a convenience view at ONE point on that curve, not the canonical output.",
        "",
        "**Operating points** (from the model's own `operating_points` block when present, else the single Youden-J row derived from `loso_youden_j`):",
        "",
        *ops_table,
        "",
        *([calibration_line, ""] if calibration_line else []),
        "### Why surface both",
        "",
        f"M5's label at p\\* disagrees with the observed heuristic often ({disagreement_txt} of the M5-scored organic AOIs in this pool). The disagreement is expected, not a bug: M5's LOSO AUC of {auc:.3f} means a hard call at any single threshold will miss often, especially on the rejected side (see the operating-points table above). M5 sees a \"deferred-like signature\" (close approach + dwell + retreat); the heuristic sees \"literal re-approach\" (cursor physically re-entered the bbox). Group D and the per-AOI badges (`M5@p* \u2260 observed` chip) surface the disagreements directly so a reviewer can decide, per case, whether the score or the observed re-entry is the more defensible read \u2014 and can pick a different threshold from the operating-points table if p\\* isn't the right cut for their question.",
        "",
        "## Regime tag",
        "",
        "**`[CURSOR-ONLY]` algorithm running on `[LAB]` data, supervision was `[LAB, NB22 gaze-derived]`.**",
        "",
        f"Per the [LAB/WILD convention](../CLAUDE.md#role-in-the-cikm-paper-the-lab--wild-bridge), the four-class taxonomy is currently `[LAB]`-only because the canonical version is gaze-derived. M5 is the named cursor-only-bootstrap that earns `[BOTH]` *if* its agreement with the gaze-derived ground truth is high enough; M5's cursor-only LOSO AUC of {auc:.3f} against NB22 `[LAB, AdSERP, typed, cursor-only]` (`{model_name}`) is the deployable evidence (previously 0.769 on the fixation-selected nine-feature stream; 0.794 is the `[absolute legacy]` gaze-gated diagnostic ceiling `[AR-V2:K9]`, neither deployable). The replay viewer is the visual inspection tool for that bootstrap — every disagreement between M5 and the heuristic on a specific AOI is a candidate for human adjudication.",
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
            caption = it["caption"]
            if tid in suspect_tids:
                caption += (" **Alignment-suspect** — labels may be attached to "
                            "the wrong AOI; see the exclusion note above.")
            lines.append(f"| [`{tid}`](../site/replay/trials/{tid}.html) | {q} | {caption} |")
        lines.append("")

    if composition:
        pop = composition["population_counts"]
        pop_total = composition["population_total"] or 1
        pool = composition["audit_pool"]
        pool_total = composition["audit_pool_total"] or 1
        lines += [
            "## SERP composition clusters (AOI accuracy audit)",
            "",
            "Orthogonal to the behaviour groups above. Trials are bucketed by the AOI bbox kinds present in the SERP layout (`dd_top` block, `dd_right` rail). The audit pool's share is shown alongside the share of all AdSERP trials so a reviewer can see how representative the rendered sample is.",
            "",
            "| Cluster | Audit pool | AdSERP population |",
            "|---|---|---|",
        ]
        for k in COMPOSITION_KEYS:
            title, _ = COMPOSITION_TITLES[k]
            # NOT n_pool: that is the candidate-pool size the closing section
            # prints, and shadowing it here turned "All 141 candidate trials"
            # into "All 11" (the last cluster's count).
            n_cluster = len(pool.get(k, []))
            n_pop = pop.get(k, 0)
            lines.append(
                f"| {title} | {n_cluster} ({100*n_cluster/pool_total:.1f}%) | "
                f"{n_pop} ({100*n_pop/pop_total:.1f}%) |"
            )
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
    ap.add_argument("--n", type=int, default=250, help="candidate pool size (default 250)")
    ap.add_argument("--cap", type=int, default=3, help="max trials per participant (default 3)")
    ap.add_argument(
        "--no-prune", action="store_true",
        help="keep bundles and screenshots outside the current selection. "
             "The pool is not the whole published set: trials added by hand "
             "with build_replay_trial.py (the README hero trials, for one) "
             "have live pages linking to them, and the prune would delete "
             "their bundles and leave those pages orphaned.")
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

    print(f"[5/7] Classifying into groups...")
    target_per_group = {"A": 5, "B-DEF": 6, "B-REJ": 6, "C": 5, "D": 5, "E": 6}
    curation = classify(bundles, target_per_group)
    for grp, items in curation["groups"].items():
        print(f"      Group {grp:6s}: {len(items)} trials")

    print(f"[6/7] Computing SERP composition clusters...")
    pool_clusters = composition_for_bundles(bundles)
    pop = compute_population_shares()
    composition = {
        "audit_pool": {k: pool_clusters[k] for k in COMPOSITION_KEYS},
        "audit_pool_total": len(bundles),
        "population_counts": pop["counts"],
        "population_total": pop["total"],
    }
    for k in COMPOSITION_KEYS:
        n_pool = len(pool_clusters[k])
        n_pop = pop["counts"][k]
        print(
            f"      {k:18s} pool={n_pool:3d} ({100*n_pool/max(len(bundles),1):5.1f}%)  "
            f"pop={n_pop:5d} ({100*n_pop/max(pop['total'],1):5.1f}%)"
        )

    out = {k: v for k, v in curation.items() if k != "features"}
    out["composition"] = composition
    CURATION_JSON.write_text(json.dumps(out))

    print(f"[7/7] Writing docs/CURATION.md...")
    disagreement = m5_disagreement_rate(bundles)
    write_curation_md(curation, len(selected), composition, disagreement)
    print(f"      wrote {CURATION_MD}")

    if args.no_prune:
        print("\n[orphan-prune] skipped (--no-prune)")
        print("\nDone. Run `python3 scripts/build_replay_pages.py` to refresh the viewer index.")
        return 0

    print(f"\n[orphan-prune] Removing screenshots not in current selection...")
    keep = {b["trial_id"] for b in bundles}
    pruned = 0
    # Remove anything in PNG_OUT not in `keep`, plus any stale .png (we now ship .jpg only).
    for f in PNG_OUT.glob("*"):
        if not f.is_file():
            continue
        if f.stem not in keep or f.suffix.lower() == ".png":
            f.unlink()
            pruned += 1
    for f in TRIALS_DIR.glob("*.json"):
        if f.stem not in keep:
            f.unlink()
            pruned += 1
    print(f"      pruned {pruned} orphan files")

    print("\nDone. Run `python3 scripts/build_replay_pages.py` to refresh the viewer index.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
