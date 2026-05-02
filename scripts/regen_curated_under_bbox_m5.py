"""Regenerate the 28 curated AR replay trials under bbox M5 model.

Outputs to site/replay/data/trials_bbox/ for side-by-side diff against
the existing site/replay/data/trials/. Caption-mismatch report is
emitted to /tmp/ar_caption_diff.md.

Run:
    python3 scripts/regen_curated_under_bbox_m5.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_replay_trial as brt  # noqa: E402

OLD_TRIALS_DIR = ROOT / "site/replay/data/trials"
NEW_TRIALS_DIR = ROOT / "site/replay/data/trials_bbox"
CURATION_JSON = ROOT / "site/replay/data/curation.json"
DIFF_REPORT = Path("/tmp/ar_caption_diff.md")

NEW_TRIALS_DIR.mkdir(parents=True, exist_ok=True)

# Patch screenshot lookup to use the local backup cache (external volume
# not mounted on workstation).
src = (ROOT / "scripts/build_replay_trial.py").read_text()
patched = src.replace(
    'png = AF_ROOT / "full-page-screenshots" / f"{trial_id}.png"',
    'png = AF_ROOT / "full-page-screenshots.local-cache.bak" / f"{trial_id}.png"',
)
exec(compile(patched, "build_replay_trial_patched", "exec"), brt.__dict__)
brt.TRIALS_OUT = NEW_TRIALS_DIR


CAPTION_PATTERNS = [
    # "11 DEFERRED AOIs"
    (re.compile(r"(\d+)\s+DEFERRED\s+AOI", re.I), "DEFERRED"),
    # "4 EVAL-REJ AOIs"
    (re.compile(r"(\d+)\s+EVAL-REJ\s+AOI", re.I), "EVALUATED_REJECTED"),
    # "1 CLK + 9 DEF + 1 REJ in one SERP"
    (re.compile(r"(\d+)\s+CLK", re.I), "CLICKED"),
    (re.compile(r"(\d+)\s+DEF\b", re.I), "DEFERRED"),
    (re.compile(r"(\d+)\s+REJ\b", re.I), "EVALUATED_REJECTED"),
    # "Drive-through: 1 CLICKED + 4 not approached"
    (re.compile(r"(\d+)\s+CLICKED\b", re.I), "CLICKED"),
    (re.compile(r"(\d+)\s+not\s+approached", re.I), "NOT_APPROACHED"),
]


def parse_caption_claims(caption: str) -> dict[str, int]:
    """Extract claimed counts per label from caption text. Returns
    label → count mapping for whichever labels the caption mentions."""
    claims: dict[str, int] = {}
    for pat, label in CAPTION_PATTERNS:
        m = pat.search(caption)
        if m:
            claims[label] = int(m.group(1))
    return claims


def main() -> int:
    curation = json.loads(CURATION_JSON.read_text())
    items = []
    for group, group_items in curation["groups"].items():
        for item in group_items:
            items.append({"group": group, **item})

    print(f"Regenerating {len(items)} curated trials under bbox M5...")
    print(f"  output dir: {NEW_TRIALS_DIR}")
    print()

    rows = []
    n_built = 0
    for item in items:
        tid = item["trial_id"]
        bundle = brt.build_trial(tid)
        if bundle is None:
            rows.append({**item, "status": "BUILD_FAILED"})
            continue
        out = NEW_TRIALS_DIR / f"{tid}.json"
        out.write_text(json.dumps(bundle))
        n_built += 1
        new_summary = bundle["_meta"]["label_summary"]

        # Diff against existing trial JSON
        old_path = OLD_TRIALS_DIR / f"{tid}.json"
        if old_path.exists():
            old_summary = json.loads(old_path.read_text())["_meta"]["label_summary"]
        else:
            old_summary = None

        # Caption claim diff
        claims = parse_caption_claims(item["caption"])
        caption_mismatches = []
        for label, claimed in claims.items():
            actual = new_summary.get(label, 0)
            if actual != claimed:
                caption_mismatches.append((label, claimed, actual))

        rows.append({
            **item,
            "status": "OK",
            "old_summary": old_summary,
            "new_summary": new_summary,
            "caption_claims": claims,
            "caption_mismatches": caption_mismatches,
            "label_summary_changed": old_summary is not None and old_summary != new_summary,
        })

        marker = ""
        if rows[-1]["label_summary_changed"]:
            marker += " [labels-shifted]"
        if caption_mismatches:
            marker += f" [caption-mismatch×{len(caption_mismatches)}]"
        print(f"  {item['group']:6s} {tid}: {json.dumps(new_summary)}{marker}")

    print()
    print(f"Built: {n_built}/{len(items)}")
    print(f"Trials with shifted labels: {sum(1 for r in rows if r.get('label_summary_changed'))}")
    print(f"Trials with caption mismatches: {sum(1 for r in rows if r.get('caption_mismatches'))}")

    # Write diff report
    lines = []
    lines.append("# AR replay caption diff — bbox M5 retrain (2026-05-02)")
    lines.append("")
    lines.append(f"Source: `scripts/regen_curated_under_bbox_m5.py`. "
                 f"M5 model: `m5_final_model_organic.json` (LOSO AUC 0.769, threshold 0.489). "
                 f"Old trials at `site/replay/data/trials/`, new at `site/replay/data/trials_bbox/`.")
    lines.append("")
    lines.append("**Three diff axes per trial:**")
    lines.append("1. *label_summary changed* — new M5 produces a different class distribution than the legacy trial JSON.")
    lines.append("2. *caption mismatch* — the curated caption's number doesn't match the new label_summary.")
    lines.append("3. *coverage* — bboxes themselves are stable across the cascade per upstream check; this diff is M5-driven.")
    lines.append("")

    # Sort by mismatch then group
    rows_with_changes = [r for r in rows if r.get("caption_mismatches") or r.get("label_summary_changed")]
    rows_clean = [r for r in rows if not r.get("caption_mismatches") and not r.get("label_summary_changed")]

    lines.append(f"## Trials with caption-or-label changes ({len(rows_with_changes)})")
    lines.append("")
    lines.append("| Group | Trial | Caption | Old summary | New summary | Caption mismatches |")
    lines.append("|---|---|---|---|---|---|")
    for r in rows_with_changes:
        old_s = json.dumps(r["old_summary"]) if r["old_summary"] else "(no old)"
        new_s = json.dumps(r["new_summary"])
        mm = "; ".join(f"{lbl} claimed {c} actual {a}" for lbl, c, a in r["caption_mismatches"]) or "—"
        lines.append(f"| {r['group']} | `{r['trial_id']}` | {r['caption']} | {old_s} | {new_s} | {mm} |")
    lines.append("")

    lines.append(f"## Trials unchanged ({len(rows_clean)})")
    lines.append("")
    lines.append("| Group | Trial | Caption | label_summary |")
    lines.append("|---|---|---|---|")
    for r in rows_clean:
        lines.append(f"| {r['group']} | `{r['trial_id']}` | {r['caption']} | {json.dumps(r['new_summary'])} |")
    lines.append("")

    DIFF_REPORT.write_text("\n".join(lines))
    print(f"Diff report: {DIFF_REPORT}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
