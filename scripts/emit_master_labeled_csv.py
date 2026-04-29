"""Emit master per-(trial, position) CSV with four-class taxonomy labels.

Reads cursor-approach-features-typed.json, merges in the gaze-derived
four-class label from NB22 (`clicked` / `deferred` / `evaluated_rejected` /
`not_approached`), and writes a flat CSV.

Output: site/replay/data/all_trials_positions.csv
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

# Reuse upstream loaders
AF_NB = Path.home() / 'Documents/dev/attentional-foraging/notebooks-v2'
sys.path.insert(0, str(AF_NB))
from data_loader import (
    load_fixations, load_mouse_events, get_trial_meta,
    interpolate_scroll, result_band_tops, assign_fixation_to_position,
    extract_serp_results,
)

AF_DATA = Path.home() / 'Documents/dev/attentional-foraging/AdSERP/data'
SRC = AF_DATA / 'cursor-approach-features-typed.json'
OUT = Path(__file__).resolve().parent.parent / 'site/replay/data/all_trials_positions.csv'

raw = json.load(open(SRC))
for i, r in enumerate(raw):
    r['_idx'] = i
    r['participant'] = r['trial_id'].split('-')[0]

n = len(raw)
print(f'records: {n:,}', file=sys.stderr)

trial_records = defaultdict(list)
for r in raw:
    trial_records[r['trial_id']].append(r)

# NB22 regression labeler (gaze-y revisits, page-space)
regression_labels = np.zeros(n, dtype=bool)
skipped = 0
for tid, recs in trial_records.items():
    fix_t = load_fixations(tid)
    meta_t = get_trial_meta(tid)
    mouse_t = load_mouse_events(tid)
    if fix_t is None or meta_t is None or mouse_t is None or len(fix_t) < 5:
        skipped += 1
        continue
    doc_h, _, _ = meta_t
    serp = extract_serp_results(tid)
    n_res = len(serp) if serp else 10
    tops = result_band_tops(n_res, doc_h)
    _, scrolls, _ = mouse_t
    s_ts = [s[0] for s in scrolls] if scrolls else [fix_t[0]['t']]
    s_ys = [s[1] for s in scrolls] if scrolls else [0]

    pos_seq = []
    for fix in fix_t:
        sy = interpolate_scroll(fix['t'], s_ts, s_ys)
        p = assign_fixation_to_position(fix['y'], tops, n_res)
        if p >= 0:
            pos_seq.append(p)

    max_seen = -1
    visited: set[int] = set()
    regressed: set[int] = set()
    for p in pos_seq:
        if p in visited and p < max_seen:
            regressed.add(p)
        visited.add(p)
        max_seen = max(max_seen, p)

    for r in recs:
        regression_labels[r['_idx']] = r['position'] in regressed

print(f'skipped trials (insufficient gaze): {skipped}', file=sys.stderr)
print(f'regressed records: {regression_labels.sum():,} ({regression_labels.mean()*100:.1f}%)',
      file=sys.stderr)

clicked = np.array([r['was_clicked'] for r in raw])
approached = np.array([r['min_dist'] < 100 for r in raw])
gaze_ok = np.zeros(n, dtype=bool)
for tid, recs in trial_records.items():
    fix_t = load_fixations(tid); meta_t = get_trial_meta(tid); mouse_t = load_mouse_events(tid)
    if fix_t is None or meta_t is None or mouse_t is None or len(fix_t) < 5:
        continue
    for r in recs:
        gaze_ok[r['_idx']] = True

labels = np.full(n, '', dtype='U25')
labels[clicked] = 'clicked'
labels[~clicked & approached & regression_labels] = 'deferred'
labels[~clicked & approached & ~regression_labels] = 'evaluated_rejected'
labels[~clicked & ~approached] = 'not_approached'
# Records from gaze-skipped trials get 'evaluated_rejected'/'not_approached'
# from the approached split (regression_labels stays False), but that conflates
# "no regression detected" with "no gaze available". Mark those explicitly.
labels[~gaze_ok & ~clicked] = 'no_gaze'

from collections import Counter
print('label counts:', Counter(labels.tolist()), file=sys.stderr)

OUT.parent.mkdir(parents=True, exist_ok=True)
keys = [k for k in raw[0].keys() if not k.startswith('_') and k != 'participant']
keys.append('four_class_label')
with open(OUT, 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=keys)
    w.writeheader()
    for r, lab in zip(raw, labels):
        row = {k: r.get(k) for k in keys if k != 'four_class_label'}
        row['four_class_label'] = lab
        w.writerow(row)

print(f'wrote {OUT} rows={n:,} cols={len(keys)}', file=sys.stderr)
