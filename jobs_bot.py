"""
Manny's job bot
---------------
Every run it:
  1. pulls fresh SEO + Data/Web Analyst jobs from public job APIs
     (Himalayas, Remotive, company career pages on Lever/Greenhouse, optional Adzuna)
  2. keeps only jobs that fit (title words, NCR or remote-for-India, experience <= 5 yrs)
  3. checks the apply link still works
  4. writes docs/jobs.json (shown by docs/index.html) and remembers what it has seen
  5. optionally sends NEW jobs to your phone on Telegram

Run:  python jobs_bot.py
Needs: pip install requests
"""
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

import config as C

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"
STATE = ROOT / "data" / "seen.json"
UA = {"User-Agent": "Mozilla/5.0 (personal job alert bot)"}
IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime.now(timezone.utc)


def log(*a):
    print(*a, flush=True)


def get_json(url, **params):
    try:
        r = requests.get(url, params=params, headers=UA, timeout=25)
        if r.status_code == 200:
            return r.json()
        log(f"  ! {r.status_code} from {url}")
    except Exception as e:  # network errors should never stop the whole run
        log(f"  ! failed {url}: {e}")
    return None


def strip_html(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


# ---------------- filters ----------------
def which_track(title):
    t = title.lower()
    if any(x in t for x in C.EXCLUDE_TITLE):
        return None
    for track, words in C.TRACKS.items():
        if any(w in t for w in words):
            return track
    return None


def min_experience(text):
    """Smallest 'X years' the job asks for, or None."""
    t = text.lower()
    found = []
    for m in re.finditer(r"(\d{1,2})\s*(?:\+|-|–|to)?\s*(\d{1,2})?\s*\+?\s*(?:years|yrs|year)", t):
        found.append(int(m.group(1)))
    found = [x for x in found if x <= 20]
    return min(found) if found else None


def place_ok(location, remote):
    loc = (location or "").lower()
    if remote:
        return True
    return any(p in loc for p in C.GOOD_INDIA_PLACES)


def score(text):
    t = text.lower()
    hits = [s for s in C.MY_SKILLS if s in t]
    n = len(set(hits))
    fit = "strong" if n >= 6 else "ok" if n >= 3 else "stretch"
    return fit, sorted(set(hits))[:8]


def link_alive(url):
    try:
        r = requests.get(url, headers=UA, timeout=20, allow_redirects=True)
        if r.status_code >= 400:
            return False
        body = r.text.lower()[:200000]
        dead = ["no longer accepting", "no longer available", "job has expired", "position has been filled",
                "this job is closed", "job not found", "taken down"]
        return not any(d in body for d in dead)
    except Exception:
        return True  # can't tell -> keep, better than losing a real job


def make_job(source, company, title, url, location, remote, posted, text, pay=""):
    track = which_track(title)
    if not track or not url:
        return None
    if not place_ok(location, remote):
        return None
    exp = min_experience(text)
    if exp is not None and exp > C.MAX_MIN_EXPERIENCE:
        return None
    fit, hits = score(title + " " + text)
    return {
        "id": re.sub(r"[^a-z0-9]+", "-", (source + "-" + url).lower())[-90:],
        "track": track,
        "where": "remote" if remote else "india",
        "fit": fit,
        "company": company or "",
        "title": title.strip(),
        "location": location or ("Remote" if remote else ""),
        "mode": "Remote" if remote else "Office / Hybrid (check listing)",
        "exp": f"{exp}+ yrs asked" if exp is not None else "Not listed",
        "pay": pay or "",
        "posted": posted or "",
        "source": source,
        "url": url,
        "note": ("Matches: " + ", ".join(hits)) if hits else "Read the JD before applying.",
    }


# ---------------- sources ----------------
def from_himalayas():
    out = []
    for track, terms in C.SEARCH_TERMS.items():
        for q in terms:
            data = get_json("https://himalayas.app/jobs/api/search", q=q, country="IN", sort="recent", page=1)
            for j in (data or {}).get("jobs", []):
                restr = [str(x).lower() for x in (j.get("locationRestrictions") or [])]
                if restr and not any("india" in r or r == "in" for r in restr):
                    continue
                pay = ""
                if j.get("minSalary") and j.get("maxSalary"):
                    pay = f"{j.get('currency','')} {int(j['minSalary']):,}–{int(j['maxSalary']):,} / {j.get('salaryPeriod') or 'annual'}"
                posted = ""
                if j.get("pubDate"):
                    posted = datetime.fromtimestamp(int(j["pubDate"]), IST).strftime("%d %b")
                out.append(make_job("Himalayas", j.get("companyName"), j.get("title", ""), j.get("applicationLink"),
                                    "Remote (India ok)", True, posted,
                                    (j.get("excerpt") or "") + " " + strip_html(j.get("description"))[:4000], pay))
            time.sleep(1.5)
    return out


def from_remotive():
    out = []
    for track, terms in C.SEARCH_TERMS.items():
        data = get_json("https://remotive.com/api/remote-jobs", search=terms[0], limit=60)
        for j in (data or {}).get("jobs", []):
            loc = (j.get("candidate_required_location") or "").lower()
            if not any(k in loc for k in ["india", "worldwide", "anywhere", "asia", "apac"]):
                continue
            out.append(make_job("Remotive", j.get("company_name"), j.get("title", ""), j.get("url"),
                                "Remote (" + (j.get("candidate_required_location") or "") + ")", True,
                                (j.get("publication_date") or "")[:10],
                                strip_html(j.get("description"))[:4000], j.get("salary") or ""))
        time.sleep(31)  # Remotive allows max 2 requests per minute
    return out


def from_lever():
    out = []
    for slug in C.LEVER_COMPANIES:
        data = get_json(f"https://api.lever.co/v0/postings/{slug}", mode="json") or []
        for j in data:
            cat = j.get("categories") or {}
            loc = cat.get("location") or ""
            remote = j.get("workplaceType") == "remote" and ("india" in loc.lower() or not loc)
            posted = ""
            if j.get("createdAt"):
                posted = datetime.fromtimestamp(j["createdAt"] / 1000, IST).strftime("%d %b")
            out.append(make_job(f"{slug} careers", slug.title(), j.get("text", ""), j.get("hostedUrl"),
                                loc, remote, posted, j.get("descriptionPlain") or ""))
    return out


def from_greenhouse():
    out = []
    for token in C.GREENHOUSE_COMPANIES:
        data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs", content="true") or {}
        for j in data.get("jobs", []):
            loc = (j.get("location") or {}).get("name", "")
            out.append(make_job(f"{token} careers", token.title(), j.get("title", ""), j.get("absolute_url"),
                                loc, "remote" in loc.lower(), (j.get("updated_at") or "")[:10],
                                strip_html(j.get("content"))[:4000]))
    return out


def from_adzuna():
    app_id, app_key = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        return []
    out = []
    for track, terms in C.SEARCH_TERMS.items():
        for where in C.ADZUNA_WHERE:
            data = get_json("https://api.adzuna.com/v1/api/jobs/in/search/1", app_id=app_id, app_key=app_key,
                            what=terms[0], where=where, max_days_old=7, results_per_page=30,
                            **{"content-type": "application/json"})
            for j in (data or {}).get("results", []):
                pay = ""
                if j.get("salary_min") and j.get("salary_max"):
                    pay = f"₹{int(j['salary_min']):,}–{int(j['salary_max']):,} / year (estimate)"
                out.append(make_job("Adzuna", (j.get("company") or {}).get("display_name"), j.get("title", ""),
                                    j.get("redirect_url"), (j.get("location") or {}).get("display_name", ""),
                                    False, (j.get("created") or "")[:10], j.get("description") or "", pay))
            time.sleep(1)
    return out


# ---------------- telegram ----------------
def telegram(new_jobs):
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        return
    if not new_jobs:
        # only say "nothing new" on the morning run, so you are not spammed
        if datetime.now(IST).hour >= 10:
            return
        text = "Subah ki update: abhi koi nayi matching job nahi. Board pe pending jobs pe apply kar do."
    else:
        order = {"strong": 0, "ok": 1, "stretch": 2}
        top = sorted(new_jobs, key=lambda j: order[j["fit"]])[:12]
        lines = [f"🆕 {len(new_jobs)} nayi jobs ({sum(j['track']=='seo' for j in new_jobs)} SEO, "
                 f"{sum(j['track']=='data' for j in new_jobs)} Data)\n"]
        for j in top:
            lines.append(f"• [{j['fit'].upper()}] {j['title']} – {j['company']} ({j['location']})\n{j['url']}")
        site = os.getenv("BOARD_URL")
        if site:
            lines.append(f"\nPoora board: {site}")
        text = "\n".join(lines)
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat, "text": text[:4000], "disable_web_page_preview": True}, timeout=20)
    except Exception as e:
        log("telegram failed:", e)


# ---------------- main ----------------
def main():
    seen = json.loads(STATE.read_text()) if STATE.exists() else {}
    fresh = []
    for name, fn in [("Himalayas", from_himalayas), ("Remotive", from_remotive), ("Lever", from_lever),
                     ("Greenhouse", from_greenhouse), ("Adzuna", from_adzuna)]:
        log(f"-> {name}")
        try:
            got = [j for j in fn() if j]
        except Exception as e:
            log(f"  ! {name} crashed: {e}")
            got = []
        log(f"   {len(got)} matching")
        fresh.extend(got)

    # de-duplicate (same title + company)
    uniq = {}
    for j in fresh:
        key = (j["title"].lower(), j["company"].lower())
        uniq.setdefault(key, j)
    fresh = list(uniq.values())

    today = NOW.date().isoformat()
    new = []
    for j in fresh:
        if j["id"] not in seen:
            if not link_alive(j["url"]):
                continue
            j["first_seen"] = today
            seen[j["id"]] = j
            new.append(j)
        else:
            seen[j["id"]].update({k: v for k, v in j.items() if k != "first_seen"})

    # forget old jobs
    cutoff = (NOW - timedelta(days=C.KEEP_DAYS)).date().isoformat()
    seen = {k: v for k, v in seen.items() if v.get("first_seen", today) >= cutoff}

    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(seen, ensure_ascii=False, indent=1))

    order = {"strong": 0, "ok": 1, "stretch": 2}
    jobs = sorted(seen.values(), key=lambda j: (j.get("first_seen", "") != today, order[j["fit"]],
                                                 j.get("first_seen", "")), reverse=False)
    for j in jobs:
        j["is_new"] = j.get("first_seen") == today
    DOCS.mkdir(exist_ok=True)
    (DOCS / "jobs.json").write_text(json.dumps({
        "updated": datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"),
        "jobs": jobs,
    }, ensure_ascii=False, indent=1))
    log(f"Done: {len(new)} new, {len(jobs)} on board")
    telegram(new)


if __name__ == "__main__":
    sys.exit(main())
