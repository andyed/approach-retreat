#!/usr/bin/env python3
"""Extract clean SERP content from an AdSERP Google HTML snapshot.

Strategy:
- Use ad-boundary-data JSON as ground truth for which result types exist
- Extract dd_top (top commercial unit) products from .commercial-unit-desktop-top
- Extract organic results from div.g containers (h3 inside .yuRUbf)
- Extract native_ad text ads from #tadsb / #bottomads
- Extract dd_right from #rhs

Output: site/data/adserp/<trial_id>.json with:
  query, ad_layout, results[{position, title, url, domain, snippet, etype}]

Usage:
    python3 extract_adserp_serp.py <trial_id> [<trial_id> ...]
"""
import sys
import json
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

ADSERP_ROOT = Path.home() / "Documents/dev/attentional-foraging/AdSERP/data"
SERP_DIR = ADSERP_ROOT / "serps"
AD_BOUNDARY_DIR = ADSERP_ROOT / "ad-boundary-data"
OUT_DIR = Path(__file__).parent.parent / "site/data/adserp"


def clean_google_url(href):
    if not href:
        return ""
    if href.startswith("/url?"):
        parsed = parse_qs(urlparse(href).query)
        if "q" in parsed:
            return parsed["q"][0]
    return href


def display_domain(url):
    if not url:
        return ""
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return url[:40]


def extract_dd_top(soup):
    """Extract products from the top commercial unit (Google Shopping carousel)."""
    items = []
    cu = soup.select_one(".commercial-unit-desktop-top")
    if not cu:
        return items

    # Each PLA inside the carousel
    for pla in cu.select(".pla-unit"):
        title_el = pla.select_one("[role='heading'], h3, .pymv4e, .e10twf")
        link_el = pla.select_one("a[href]")
        price_el = pla.select_one("span[aria-hidden='true'].e10twf, .HhT9Ub, .qptdjc")

        if not title_el and link_el:
            title_el = link_el

        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        url = clean_google_url(link_el.get("href", "")) if link_el else ""
        price = price_el.get_text(strip=True) if price_el else ""

        items.append({
            "title": title,
            "url": url,
            "domain": display_domain(url),
            "snippet": price,
            "etype": "dd_top",
        })

    return items


def extract_organic(soup):
    """Extract organic results from div.g containers."""
    items = []
    seen_titles = set()

    # Primary selector: div.g with h3 inside
    for g in soup.select("div.g"):
        if g.find_parent(class_="g"):
            continue  # nested sitelink

        title_el = g.select_one("h3")
        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        if title in seen_titles or not title:
            continue
        seen_titles.add(title)

        link_el = title_el.find_parent("a") or g.select_one("a[href]")
        url = clean_google_url(link_el.get("href", "")) if link_el else ""
        snippet_el = g.select_one(".VwiC3b, .IsZvec, .aCOpRe, .lyLwlc")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

        items.append({
            "title": title,
            "url": url,
            "domain": display_domain(url),
            "snippet": snippet,
            "etype": "organic",
        })

    return items


def extract_native_ads(soup):
    """Extract bottom text ads from #tadsb / #bottomads."""
    items = []
    seen_titles = set()

    # #tadsb is the inner container; #bottomads wraps it
    container = soup.select_one("#tadsb") or soup.select_one("#bottomads")
    if not container:
        return items

    # Each ad has a [role='heading'] for its title and .lyLwlc for snippet
    headings = container.select("[role='heading']")

    for h in headings:
        title = h.get_text(strip=True)
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)

        # Walk up to find the ad container
        ad_container = h
        for _ in range(8):
            ad_container = ad_container.parent
            if ad_container is None:
                break
            if ad_container.select_one("a[href]"):
                break

        if ad_container is None:
            continue

        link_el = ad_container.select_one("a[href]")
        url = clean_google_url(link_el.get("href", "")) if link_el else ""

        # Snippet: nearest .lyLwlc or .MUxGbd that isn't the title or domain
        snippet = ""
        for snip_el in ad_container.select(".lyLwlc, .MUxGbd"):
            text = snip_el.get_text(strip=True)
            if text and text != title and "Ad" not in text[:5] and "http" not in text[:8]:
                snippet = text
                break

        items.append({
            "title": title,
            "url": url,
            "domain": display_domain(url),
            "snippet": snippet,
            "etype": "native_ad",
        })

    return items


def extract_dd_right(soup):
    """Extract right-rail ads from #rhs."""
    items = []
    rhs = soup.select_one("#rhs")
    if not rhs:
        return items
    for h in rhs.select("[role='heading'], h3"):
        title = h.get_text(strip=True)
        if not title or "Related" in title:
            continue
        link = h.find_parent("a") or h.find_next("a")
        url = clean_google_url(link.get("href", "")) if link else ""
        items.append({
            "title": title,
            "url": url,
            "domain": display_domain(url),
            "snippet": "",
            "etype": "dd_right",
        })
    return items


def extract_serp(trial_id):
    html_path = SERP_DIR / f"{trial_id}.html"
    if not html_path.exists():
        raise FileNotFoundError(f"SERP not found: {html_path}")

    # Load ad-boundary ground truth
    ad_boundary_path = AD_BOUNDARY_DIR / f"{trial_id}.json"
    ad_boundary = {}
    if ad_boundary_path.exists():
        ad_boundary = json.loads(ad_boundary_path.read_text())

    expected = {
        "dd_top": len(ad_boundary.get("dd_top", [])),
        "dd_right": len(ad_boundary.get("dd_right", [])),
        "native_ad": len(ad_boundary.get("native_ad", [])),
    }

    with open(html_path) as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    q_input = soup.select_one('input[name="q"]')
    query = q_input.get("value", "") if q_input else ""

    # Extract by type, in display order: dd_top → organic → native_ad → dd_right
    dd_top = extract_dd_top(soup)
    organic = extract_organic(soup)
    native_ads = extract_native_ads(soup)
    dd_right = extract_dd_right(soup)

    all_results = dd_top + organic + native_ads + dd_right

    # Assign positions
    for i, r in enumerate(all_results):
        r["position"] = i

    actual = {
        "dd_top": len(dd_top),
        "organic": len(organic),
        "native_ad": len(native_ads),
        "dd_right": len(dd_right),
    }

    return {
        "trial_id": trial_id,
        "query": query,
        "ad_layout_expected": expected,
        "extracted_counts": actual,
        "n_results": len(all_results),
        "results": all_results,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_adserp_serp.py <trial_id> [<trial_id> ...]")
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for trial_id in sys.argv[1:]:
        try:
            data = extract_serp(trial_id)
            out_path = OUT_DIR / f"{trial_id}.json"
            out_path.write_text(json.dumps(data, indent=2))

            exp = data["ad_layout_expected"]
            act = data["extracted_counts"]

            # Flag mismatches
            issues = []
            for k in ("dd_top", "native_ad", "dd_right"):
                if exp[k] != act[k]:
                    # Note: dd_top in boundary data is the carousel container (1),
                    # but we extract individual products from inside it (>1)
                    if k == "dd_top" and exp[k] == 1 and act[k] >= 1:
                        continue
                    issues.append(f"{k}: expected {exp[k]}, got {act[k]}")

            print(f"{trial_id}: {data['n_results']} results, q='{data['query'][:50]}'")
            print(f"  organic={act['organic']} dd_top={act['dd_top']} native_ad={act['native_ad']} dd_right={act['dd_right']}")
            if issues:
                print(f"  ⚠ {'; '.join(issues)}")
            print(f"  → {out_path}")
        except Exception as e:
            print(f"{trial_id}: ERROR — {e}")


if __name__ == "__main__":
    main()
