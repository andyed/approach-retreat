#!/usr/bin/env python3
"""Build movie-recommendation scenario JSONs from TMDB metadata.

Reads TMDB_READ_TOKEN from .env, fetches per-title details from TMDB, and
writes site/data/<scenario_id>.json files matching the existing answer schema
(position/title/author/author_bio/snippet/full_text/upvotes/year) plus
movie-specific fields (poster_url, runtime, rating, genres, watch_on).

Also patches site/data/questions.json to register the new scenarios.

Run:  python3 scripts/build_movie_scenarios.py
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "site" / "data"
QUESTIONS = DATA_DIR / "questions.json"
ENV = ROOT / ".env"


def load_token() -> str:
    if not ENV.exists():
        sys.exit(".env missing — drop TMDB_READ_TOKEN there")
    for line in ENV.read_text().splitlines():
        if line.startswith("TMDB_READ_TOKEN="):
            return line.split("=", 1)[1].strip()
    sys.exit("TMDB_READ_TOKEN not in .env")


TOKEN = load_token()
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}
BASE = "https://api.themoviedb.org/3"


def tmdb_get(path: str, **params) -> dict:
    url = f"{BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def best_match(title: str, year: int) -> dict:
    r = tmdb_get("/search/movie", query=title, year=year)
    if not r["results"]:
        r = tmdb_get("/search/movie", query=title)
    if not r["results"]:
        raise RuntimeError(f"no TMDB result for {title} ({year})")
    exact = [x for x in r["results"] if (x.get("release_date") or "").startswith(str(year))]
    return (exact or r["results"])[0]


def details(movie_id: int) -> dict:
    return tmdb_get(
        f"/movie/{movie_id}",
        append_to_response="credits,release_dates,watch/providers",
    )


def director(credits: dict) -> str:
    for c in credits.get("crew", []):
        if c.get("job") == "Director":
            return c["name"]
    return ""


def us_certification(release_dates: dict) -> str:
    for r in release_dates.get("results", []):
        if r.get("iso_3166_1") != "US":
            continue
        for d in r.get("release_dates", []):
            if d.get("certification"):
                return d["certification"]
    return ""


def us_providers(watch: dict) -> str:
    us = watch.get("results", {}).get("US", {})
    flatrate = [p["provider_name"] for p in us.get("flatrate", [])]
    if flatrate:
        return ", ".join(flatrate[:3])
    rent = [p["provider_name"] for p in us.get("rent", [])]
    if rent:
        return f"Rent: {', '.join(rent[:2])}"
    return ""


def to_answer(position: int, title: str, year: int, snippet: str, det: dict) -> dict:
    poster_path = det.get("poster_path") or ""
    poster_url = f"https://image.tmdb.org/t/p/w342{poster_path}" if poster_path else ""
    backdrop_path = det.get("backdrop_path") or ""
    backdrop_url = f"https://image.tmdb.org/t/p/w780{backdrop_path}" if backdrop_path else ""
    runtime = det.get("runtime") or 0
    cert = us_certification(det.get("release_dates", {}))
    genres = [g["name"] for g in det.get("genres", [])]
    director_name = director(det.get("credits", {}))
    providers = us_providers(det.get("watch/providers", {}))
    synopsis = (det.get("overview") or "").strip()

    meta_parts = []
    if runtime:
        meta_parts.append(f"{runtime} min")
    if cert:
        meta_parts.append(cert)
    if genres:
        meta_parts.append(" / ".join(genres[:2]))
    metadata_line = " · ".join(meta_parts)

    full_text = synopsis
    if providers:
        full_text = f"{synopsis}\n\nWatch on: {providers}"

    return {
        "position": position,
        "title": title,
        "year": int(str(year)[:4]),
        "author": director_name,
        "author_bio": metadata_line,
        "snippet": snippet,
        "full_text": full_text,
        "upvotes": det.get("vote_count") or 0,
        # movie-specific extras for movie-aware layouts:
        "poster_url": poster_url,
        "backdrop_url": backdrop_url,
        "tmdb_id": det.get("id"),
        "tagline": det.get("tagline") or "",
        "rating": cert,
        "runtime": runtime,
        "genres": genres,
        "watch_on": providers,
        "vote_average": det.get("vote_average"),
    }


# Curated scenarios — title, year, context-specific match snippet.
# Lean toward classics and well-known films; mix anchors with one or two
# slightly off-axis fits per context to give AR cursor variance.
SCENARIOS = {
    "date-night": {
        "title": "Recommend movies for date night",
        "subtitle": "Adult chemistry · character drama · smart action",
        "tone": "romantic / adult co-decision",
        "year_min": 1942,
        "year_max": 2016,
        "movies": [
            ("Casablanca", 1942,
             "The reigning grandfather of the date-night film: cynical bar, terrible decisions, two adults who know exactly what they're doing."),
            ("Before Sunrise", 1995,
             "Two strangers walk Vienna and talk for ninety minutes — the rare romance that earns its silences."),
            ("The Princess Bride", 1987,
             "The safest possible suggestion. Nobody you'd want to date hates this movie."),
            ("La La Land", 2016,
             "Big musical numbers and a quiet ending that splits opinion in a way that gives you something to talk about after."),
            ("Eternal Sunshine of the Spotless Mind", 2004,
             "Romantic for people who think 'romantic comedy' is a slur. Sad, weird, hopeful in spite of itself."),
            ("Pride & Prejudice", 2005,
             "Knightley plus Macfadyen plus that hand flex. Two hours of restrained yearning, fully calibrated for the genre."),
            ("Out of Sight", 1998,
             "Soderbergh, Lopez, Clooney in the trunk scene. Adult chemistry, no one acts like a teenager."),
            ("Notting Hill", 1999,
             "Rom-com comfort food made with a real screenplay. Holds up better than it has any right to."),
            ("Moonrise Kingdom", 2012,
             "Twee on purpose, but the kids are the adults and the adults are the kids. Wes Anderson's most romantic film."),
            ("Crouching Tiger, Hidden Dragon", 2000,
             "If you want spectacle that isn't superhero-shaped — wuxia plus a love triangle plus rooftop chases."),
        ],
    },
    "kids-saturday": {
        "title": "Recommend movies for the kids on Saturday",
        "subtitle": "Ages 5–10 · animated and family adventure",
        "tone": "kid-friendly / parent-tolerable",
        "year_min": 1982,
        "year_max": 2014,
        "movies": [
            ("The Iron Giant", 1999,
             "Brad Bird's first feature, and probably the best science-fiction film for kids ever made. Superman-tested."),
            ("Kiki's Delivery Service", 1989,
             "Miyazaki's most kid-friendly Studio Ghibli — gentle, magical, no scary villain. A 5-year-old can sit through it."),
            ("Toy Story", 1995,
             "If they haven't seen the original, they should. Holds up exactly thirty years later."),
            ("How to Train Your Dragon", 2010,
             "Dragon-flying scenes still hit. Strong score, real emotional stakes, no juvenile humor crutches."),
            ("Paddington", 2014,
             "The friendliest film ever made. Adults cry, kids laugh, the bear is competent."),
            ("The Goonies", 1985,
             "Pirate treasure, secret tunnels, a bunch of kids with no parents in sight. Slightly age-up — better for 8–10."),
            ("Babe", 1995,
             "A pig who herds sheep with kindness. Adults will be unprepared for how moving it still is."),
            ("The Incredibles", 2004,
             "Pixar's only movie that works as a dad movie too. Fast pacing, no slow middle."),
            ("E.T. the Extra-Terrestrial", 1982,
             "Probably their first taste of a film that earns its tears. Spielberg at his most direct."),
            ("Wallace & Gromit: The Curse of the Were-Rabbit", 2005,
             "Stop-motion claymation at its sharpest. Inventive enough that adults stay awake."),
        ],
    },
    "extended-family": {
        "title": "Recommend movies for the extended family",
        "subtitle": "Multi-generational · broad-appeal classics",
        "tone": "consensus / nothing risky",
        "year_min": 1946,
        "year_max": 2010,
        "movies": [
            ("Back to the Future", 1985,
             "Multi-generational wins are hard. This one wins. Grandma will follow the time-travel rules."),
            ("The Princess Bride", 1987,
             "The household-name rewatchable. Quoted across the room within the first ten minutes."),
            ("Singin' in the Rain", 1952,
             "Older relatives will be delighted. Younger ones will be surprised it's actually fun."),
            ("It's a Wonderful Life", 1946,
             "Holiday-coded but works any time. Strong on grandparents, surprisingly current on its core argument."),
            ("The Sound of Music", 1965,
             "Long, but the songs do the work. Three-generation reliable pick."),
            ("Cool Runnings", 1993,
             "Underrated as the family-friendly sports comedy. Bobsled, John Candy, no objectionable content."),
            ("Forrest Gump", 1994,
             "Aunts and uncles will quote it. The historical backdrop carries the older relatives."),
            ("The Sandlot", 1993,
             "Summer childhood compressed into 100 minutes. Plays for everyone over six."),
            ("Big", 1988,
             "The Tom Hanks one where he's a kid in an adult body. The piano scene still works on a phone."),
            ("Toy Story 3", 2010,
             "Doubles as a toy story for the kids and a college-departure story for the parents. Universal cry."),
        ],
    },
    "solo-wind-down": {
        "title": "Recommend a movie for a quiet solo evening",
        "subtitle": "Atmospheric · contemplative · single-viewer",
        "tone": "slow / interior",
        "year_min": 1962,
        "year_max": 2023,
        "movies": [
            ("Lost in Translation", 2003,
             "A jet-lagged Tokyo hotel and a quiet friendship. Made for a single viewer with the lights low."),
            ("Her", 2013,
             "Spike Jonze's loneliest film. The kind of movie that feels different watched alone."),
            ("In the Mood for Love", 2000,
             "Wong Kar-wai. Two neighbors, a hallway, every glance held a beat too long."),
            ("Lawrence of Arabia", 1962,
             "Nearly four hours and not a single dragging minute. Watch widescreen, with no one talking."),
            ("Wings of Desire", 1987,
             "Wenders. Black-and-white angels listening to a city. Slow but never boring."),
            ("Paterson", 2016,
             "A bus driver writes poetry. Almost nothing happens. That's the point."),
            ("Past Lives", 2023,
             "Three timelines, one love story. New canon, won't disappoint anyone who liked Lost in Translation."),
            ("Drive My Car", 2021,
             "Three-hour quiet masterpiece. Long drives, Chekhov, grief. The ending repays the runtime."),
            ("Moonlight", 2016,
             "Three chapters, one life. Aesthetic precision, emotional payoff."),
            ("The Tree of Life", 2011,
             "Malick at his most ambitious. Cosmos to suburban Texas. Either it works on you or it doesn't."),
        ],
    },
    "teen-sleepover": {
        "title": "Recommend movies for a teen sleepover",
        "subtitle": "Ages 13–16 · high-energy · cult favorites",
        "tone": "loud / quotable / no slow middle",
        "year_min": 1985,
        "year_max": 2018,
        "movies": [
            ("The Breakfast Club", 1985,
             "Original Saturday-detention movie. Their parents will recognize the dialogue."),
            ("Mean Girls", 2004,
             "Quoted reflexively by a generation. Still funny in 2026, somehow."),
            ("Clueless", 1995,
             "Highest-craft teen comedy of the 90s. Holds up because the script is genuinely sharp."),
            ("10 Things I Hate About You", 1999,
             "Heath Ledger, Julia Stiles, Shakespeare in disguise. Real chemistry."),
            ("Scott Pilgrim vs. the World", 2010,
             "Edgar Wright kineticism. Arcade aesthetic, video-game logic. Plays especially well at midnight."),
            ("Spider-Man: Into the Spider-Verse", 2018,
             "Best animated superhero movie ever made. Colors alone keep them awake."),
            ("Edge of Tomorrow", 2014,
             "Time-loop alien invasion done right. Cruise dies a lot. Tighter than the runtime suggests."),
            ("Hot Fuzz", 2007,
             "Pegg and Frost in a small English village. Loud, stupid, smart. Sleepover-bulletproof."),
            ("The Matrix", 1999,
             "Either it'll be their first time and it'll blow them away, or it'll be a rewatch with friends."),
            ("Easy A", 2010,
             "Emma Stone's breakout. Sharp, mean enough to be funny, kind enough to land."),
        ],
    },
    "rainy-sunday-afternoon": {
        "title": "Recommend a movie for a rainy Sunday afternoon",
        "subtitle": "Comfort rewatches · nothing taxing",
        "tone": "easy / familiar / dozable",
        "year_min": 1986,
        "year_max": 2014,
        "movies": [
            ("The Big Lebowski", 1998,
             "The Coens' most rewatchable. Half-dozes well. The rug really did tie the room together."),
            ("Groundhog Day", 1993,
             "Probably the best comfort movie ever made. Improves on rewatches."),
            ("The Grand Budapest Hotel", 2014,
             "Wes Anderson's set-design peak. Light, fast, no emotional homework."),
            ("Stand By Me", 1986,
             "Short, mid-eighties summer, Stephen King's sweetest adaptation. Done in 90 minutes."),
            ("When Harry Met Sally...", 1989,
             "Talking-walking-eating-delicatessen New York romcom. Earned its canonical status."),
            ("O Brother, Where Art Thou?", 2000,
             "Coens go folksy. Soundtrack runs the whole thing. Forgive the Depression-era bleached look."),
            ("Almost Famous", 2000,
             "Cameron Crowe's love letter to 70s rock. Ends well."),
            ("Chicken Run", 2000,
             "Aardman stop-motion prison-break. Funny enough that you don't notice it's a chicken movie."),
            ("The Royal Tenenbaums", 2001,
             "Wes Anderson at his most melancholy. Best when you have nothing else to do."),
            ("Amélie", 2001,
             "Whimsical Paris fantasy. Voice-over carries the front half. Looks better on a rainy day."),
        ],
    },
}


def build():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    new_question_entries = []
    for sid, sc in SCENARIOS.items():
        print(f"\n[{sid}]  {sc['title']}")
        answers = []
        for i, (title, year, snippet) in enumerate(sc["movies"]):
            try:
                m = best_match(title, year)
                d = details(m["id"])
                answers.append(to_answer(i, title, year, snippet, d))
                print(f"  [{i:2d}] {title} ({year})  →  tmdb_id={d.get('id')}")
            except Exception as e:
                print(f"  [{i:2d}] FAILED {title} ({year}): {e}", file=sys.stderr)
                raise
            time.sleep(0.05)  # polite pacing under the 40 req / 10s limit
        out = DATA_DIR / f"{sid}.json"
        out.write_text(json.dumps(answers, indent=2, ensure_ascii=False) + "\n")
        print(f"  → wrote {out.relative_to(ROOT)}")
        new_question_entries.append({
            "id": sid,
            "title": sc["title"],
            "subtitle": sc["subtitle"],
            "year_min": sc["year_min"],
            "year_max": sc["year_max"],
            "answer_count": len(answers),
            "ad_count": 0,
            "tone": sc["tone"],
        })

    # Patch questions.json: keep existing entries, replace any of our IDs.
    if QUESTIONS.exists():
        idx = json.loads(QUESTIONS.read_text())
    else:
        idx = {"questions": [], "default": None}
    keep = [q for q in idx.get("questions", []) if q["id"] not in SCENARIOS]
    idx["questions"] = keep + new_question_entries
    if not idx.get("default"):
        idx["default"] = next(iter(SCENARIOS))
    QUESTIONS.write_text(json.dumps(idx, indent=2, ensure_ascii=False) + "\n")
    print(f"\n→ patched {QUESTIONS.relative_to(ROOT)} ({len(idx['questions'])} questions total)")


if __name__ == "__main__":
    build()
