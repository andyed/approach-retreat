"""Build per-trial replay HTML pages from template + trial JSONs.

Reads:  site/replay/template.html, site/replay/data/trials/*.json
Writes: site/replay/trials/{trial_id}.html, site/replay/index.html

Run:    python3 scripts/build_replay_pages.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPLAY = ROOT / "site/replay"
TEMPLATE = REPLAY / "template.html"
TRIAL_JSON_DIR = REPLAY / "data/trials"
TRIAL_HTML_DIR = REPLAY / "trials"


INDEX_CSS = """
body { background: #111; color: #eee; font-family: system-ui, -apple-system, sans-serif; padding: 32px; max-width: 1280px; margin: 0 auto; }
h1 { font-size: 22px; margin-bottom: 6px; }
.lede { color: #aaa; font-size: 13px; margin-bottom: 24px; line-height: 1.5; }
.lede a { color: #6af; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px; }
.card { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px; padding: 16px; text-decoration: none; color: #eee; transition: border-color 0.15s, transform 0.15s; }
.card:hover { border-color: #4a8aca; transform: translateY(-1px); }
.card h2 { font-size: 14px; font-weight: 600; margin-bottom: 6px; color: #ff9933; }
.card .query { font-size: 12px; color: #aaa; margin-bottom: 12px; min-height: 32px; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; font-size: 11px; color: #888; }
.stats .v { color: #ddd; font-weight: 600; display: block; font-size: 13px; }
.crumbs { color: #666; font-size: 11px; margin-top: 24px; padding-top: 16px; border-top: 1px solid #222; }
.pills { display: flex; gap: 4px; margin-bottom: 12px; flex-wrap: wrap; }
.pill { display: inline-block; font-family: monospace; font-size: 10px; font-weight: bold; padding: 2px 7px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.08); }
.pill.clk { background: #16a34a; color: #fff; }
.pill.def { background: #f59e0b; color: #000; }
.pill.rej { background: #ef4444; color: #fff; }
.pill.not { background: #2a2a2a; color: #888; }
"""


def build_trial_page(trial_path: Path, template: str) -> Path:
    trial = json.loads(trial_path.read_text())
    tid = trial["trial_id"]
    query = trial.get("task", "").split("|")[-1].strip() or tid
    title = f"AR Replay: {tid}"
    out = (
        template
        .replace("__TITLE__", title)
        .replace("__TRIAL_ID__", tid)
        .replace("__QUERY__", query)
        .replace("__SCREENSHOT__", f"../data/{trial['screenshot']}")
        .replace("__TRIAL_DATA__", json.dumps(trial))
    )
    TRIAL_HTML_DIR.mkdir(parents=True, exist_ok=True)
    out_path = TRIAL_HTML_DIR / f"{tid}.html"
    out_path.write_text(out)
    return out_path


def build_index(trials: list[dict]) -> Path:
    cards = []
    for t in trials:
        tid = t["trial_id"]
        query = t.get("task", "").split("|")[-1].strip() or tid
        n_organic = len(t["bboxes"].get("organic_result", []))
        n_ad = sum(len(t["bboxes"].get(k, [])) for k in ("native_ad", "dd_top", "dd_right"))
        s = t["_meta"].get("label_summary", {})
        pills = (
            f'<span class="pill clk">CLK {s.get("CLICKED", 0)}</span>'
            f'<span class="pill def">DEF {s.get("DEFERRED", 0)}</span>'
            f'<span class="pill rej">REJ {s.get("EVALUATED_REJECTED", 0)}</span>'
            f'<span class="pill not">NA {s.get("NOT_APPROACHED", 0)}</span>'
        )
        cards.append(f"""
        <a class="card" href="trials/{tid}.html">
          <h2>{tid}</h2>
          <div class="query">{query}</div>
          <div class="pills">{pills}</div>
          <div class="stats">
            <span><span class="v">{(t['duration_ms']/1000):.1f}s</span>duration</span>
            <span><span class="v">{t['_meta']['n_cursor']}</span>cursor</span>
            <span><span class="v">{n_organic}</span>organic</span>
            <span><span class="v">{n_ad}</span>ads</span>
          </div>
        </a>
        """)
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>AR Replay — AdSERP signal testbed</title>
<style>{INDEX_CSS}</style></head><body>
<h1>AdSERP Signal Testbed</h1>
<p class="lede">Replay of the <a href="https://github.com/kayhan-latifzadeh/AdSERP">AdSERP dataset</a> with per-AOI <strong>four-class taxonomy labels</strong> overlaid: <span class="pill clk">CLICKED</span> <span class="pill def">DEFERRED</span> <span class="pill rej">EVALUATED-REJECTED</span> <span class="pill not">NOT-APPROACHED</span>. Labels derived from cursor enter/dwell/exit episodes against AOI bboxes — the inference task the AR library performs in production. Sibling to the <a href="../index.html">live testbed</a>.</p>
<div class="grid">
  {"".join(cards)}
</div>
<div class="crumbs">Built from raw AdSERP signals — no NB15 derivatives. Organic AOIs from CV row-projection (see <code>attentional-foraging/scripts/extract_organic_bboxes.py</code>). AOI labels from <code>derive_aoi_labels()</code> in <code>scripts/build_replay_trial.py</code>.</div>
</body></html>
"""
    out = REPLAY / "index.html"
    out.write_text(html)
    return out


def main() -> int:
    template = TEMPLATE.read_text()
    trial_files = sorted(TRIAL_JSON_DIR.glob("*.json"))
    if not trial_files:
        print(f"no trials in {TRIAL_JSON_DIR}")
        return 1
    trials = [json.loads(p.read_text()) for p in trial_files]
    for tp in trial_files:
        out = build_trial_page(tp, template)
        print(f"  {out.relative_to(REPLAY)}")
    idx = build_index(trials)
    print(f"\n  {idx.relative_to(REPLAY)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
