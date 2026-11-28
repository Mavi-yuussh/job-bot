"""
Manny's job bot  (v2)
---------------------
Every run (every 3 hours on GitHub):
  1. pulls fresh SEO / Data-Business Analyst / Data Scientist jobs from
     - JobSpy: Indeed India, LinkedIn, Naukri, Google Jobs
     - remote job APIs: Himalayas, Remotive, Jobicy, RemoteOK, Working Nomads
     - company career pages: Lever, Greenhouse, Ashby, Workable, Recruitee, SmartRecruiters
  2. keeps only jobs that fit: title, Delhi NCR office/hybrid or remote-from-India,
     experience 3-5 yrs, salary >= Rs 55k/month (when salary is shown), posted in the last 7 days,
     not crowded (LinkedIn applicants), not abroad-only
  3. tags media companies (MEDIA tab)
  4. never shows jobs you already marked Applied / Skip (data/applied.json)
  5. writes docs/jobs.json (the website), data/seen.json, data/jobs.db (SQLite), data/applied.csv,
     data/run_log.json (which source gave how many jobs)

Run locally:  pip install -r requirements.txt  &&  python jobs_bot.py
"""
import csv
import hashlib
import html
import json
import re
import sqlite3
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

import requests

import config as C

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"
DATA = ROOT / "data"
SEEN = DATA / "seen.json"
APPLIED = DATA / "applied.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/130.0 Safari/537.36"}
IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime.now(timezone.utc)
START = time.time()
SCHEMA = 2

LOG = {"sources": {}, "rejected": Counter()}


def log(*a):
    print(*a, flush=True)


def over_budget():
    return time.time() - START > C.TIME_BUDGET_MIN * 60


def get(url, params=None, as_json=True, timeout=25):
    try:
        r = requests.get(url, params=params, headers=UA, timeout=timeout)
        if r.status_code == 200:
            return r.json() if as_json else r.text
        log(f"  ! {r.status_code} {url[:90]}")
    except Exception as e:  # one bad source must never stop the run
        log(f"  ! failed {url[:90]}: {str(e)[:120]}")
    return None


def strip_html(s):
    s = re.sub(r"<(br|p|li|div|h\d)[^>]*>", "\n", s or "", flags=re.I)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()


def to_dt(v):
    """Anything (epoch s/ms, ISO string, date) -> aware UTC datetime or None."""
    if v is None or v == "" or (isinstance(v, float) and v != v):
        return None
    try:
        if isinstance(v, datetime):
            return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        if isinstance(v, date):
            return datetime(v.year, v.month, v.day, 6, tzinfo=timezone.utc)
        if isinstance(v, (int, float)):
            v = float(v)
            return datetime.fromtimestamp(v / 1000 if v > 1e11 else v, timezone.utc)
        s = str(v).strip()
        if s.isdigit():
            return to_dt(int(s))
        s = s.replace("Z", "+00:00")
        if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", s):
            s = s.replace(" ", "T")
        d = datetime.fromisoformat(s[:32])
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        pass
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%d"):
        try:
            d = datetime.strptime(str(v).strip(), fmt)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


# ---------------------------------------------------------------- money
FX = dict(C.FX_FALLBACK)


def load_fx():
    data = get("https://open.er-api.com/v6/latest/INR")
    rates = (data or {}).get("rates") or {}
    for cur, per_inr in rates.items():
        if per_inr:
            FX[cur.upper()] = 1 / per_inr
    log(f"FX: 1 USD = Rs {FX.get('USD', 0):.1f}")


PER_MONTH = {"yearly": 1 / 12, "year": 1 / 12, "annual": 1 / 12, "annually": 1 / 12, "monthly": 1, "month": 1,
             "weekly": 4.33, "week": 4.33, "daily": 22, "day": 22, "hourly": 168, "hour": 168}


def monthly_inr(lo, hi, currency="INR", interval=None):
    """Return (lo, hi) in Rs per month, or None."""
    try:
        lo = float(lo) if lo not in (None, "") else None
        hi = float(hi) if hi not in (None, "") else None
    except Exception:
        return None
    if lo != lo:
        lo = None
    if hi != hi:
        hi = None
    if not lo and not hi:
        return None
    lo, hi = lo or hi, hi or lo
    cur = (currency or "INR").upper().strip()
    cur = {"RS": "INR", "₹": "INR", "$": "USD", "€": "EUR", "£": "GBP"}.get(cur, cur)
    rate = FX.get(cur)
    if not rate:
        return None
    iv = (str(interval).lower().split(".")[-1] if interval else "")
    if iv not in PER_MONTH:
        # guess: big numbers are yearly
        iv = "yearly" if hi * rate >= 150000 else "monthly"
        if cur != "INR" and hi < 1000:
            iv = "hourly"
    f = PER_MONTH[iv] * rate
    return int(lo * f), int(hi * f)


LPA = re.compile(r"(\d{1,2}(?:\.\d)?)\s*l?\s*(?:-|–|to)\s*(?:₹|rs\.?)?\s*(\d{1,2}(?:\.\d)?)\s*(?:lpa|lakhs?|l\b|lacs?)|"
                 r"(\d{1,2}(?:\.\d)?)\s*(?:lpa|lakhs? per annum|lakhs?/annum|lacs? p\.?a)", re.I)
INR_RANGE = re.compile(r"(?:₹|rs\.?|inr)\s*([\d,]{5,9})\s*(?:-|–|to)\s*(?:₹|rs\.?|inr)?\s*([\d,]{5,9})\s*"
                       r"(per month|/month|/ month|p\.?m\.?|monthly|per annum|p\.?a\.?|/year|per year|annually)?", re.I)


def salary_from_text(text):
    t = text or ""
    m = LPA.search(t)
    if m:
        if m.group(1):
            return int(float(m.group(1)) * 1e5 / 12), int(float(m.group(2)) * 1e5 / 12)
        v = int(float(m.group(3)) * 1e5 / 12)
        return v, v
    m = INR_RANGE.search(t)
    if m:
        a, b = int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
        unit = (m.group(3) or "").lower()
        iv = "monthly" if "m" in unit and "annum" not in unit else ("yearly" if unit else None)
        return monthly_inr(a, b, "INR", iv)
    return None


def fmt_k(v):
    return f"{v / 1000:.0f}k" if v < 100000 else f"{v / 100000:.1f}L"


# ---------------------------------------------------------------- filters
def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def which_track(title):
    t = f" {(title or '').lower()} "
    if any(x in t for x in C.EXCLUDE_TITLE):
        return None
    for track, words in C.TRACKS.items():
        if any(w in t for w in words):
            return track
    return None


EXP_RX = re.compile(r"(\d{1,2})(?:\.\d)?\s*(?:\+|plus)?\s*(?:-|–|to)?\s*(\d{1,2})?\s*\+?\s*(?:years?|yrs?)", re.I)


def experience(text):
    """(min, max) years the job asks for, or (None, None)."""
    t = (text or "")[:6000]
    best = []
    for m in EXP_RX.finditer(t):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else None
        if a > 20 or (b is not None and (b > 25 or b < a)):
            continue
        ctx = t[max(0, m.start() - 70): m.end() + 70].lower()
        if "experience" in ctx or "exp" in ctx or "work" in ctx:
            best.append((a, b))
    if not best:
        return None, None
    a, b = min(best, key=lambda x: x[0])
    return a, b


def detect_mode(location, text, remote_flag=None, wfh_type=None):
    blob = f"{location} {wfh_type or ''}".lower()
    body = (text or "").lower()[:4000]
    if "hybrid" in blob or "hybrid" in body[:1500]:
        return "Hybrid"
    if remote_flag or "remote" in blob or "work from home" in blob or "wfh" in blob:
        return "Remote"
    if re.search(r"\b(fully remote|100% remote|remote[- ]first|work from home|remote role|remote position)\b", body):
        return "Remote"
    return "Office"


def abroad_only(text):
    t = (text or "").lower()
    return any(re.search(p, t) for p in C.ABROAD_ONLY)


def location_ok(location, mode, text):
    loc = (location or "").lower()
    if any(p in loc for p in C.GOOD_INDIA_PLACES):
        return True
    if mode != "Remote":
        return False
    if abroad_only(text):
        return False
    if any(w in loc for w in C.REMOTE_OK_WORDS):
        return True
    # "Remote" with no country: keep only if the JD itself mentions India
    bare = re.sub(r"[^a-z]", "", loc)
    if bare in ("", "remote", "remotejob", "workfromhome", "wfh"):
        return "india" in (text or "").lower()
    return False


def company_blocked(company):
    c = f" {norm(company)} "
    return any(f" {norm(x)} " in c for x in C.EXCLUDE_COMPANIES)


def is_media(company, text):
    c = (company or "").lower()
    if any(m in c for m in C.MEDIA_COMPANIES):
        return True
    t = (text or "").lower()[:5000]
    return sum(w in t for w in C.MEDIA_JD_WORDS) >= 2


def fit_score(track, text):
    t = (text or "").lower()
    hits = sorted({s for s in C.SKILLS[track] if re.search(r"(?<![a-z])" + re.escape(s) + r"(?![a-z])", t)})
    n = len(hits)
    return ("strong" if n >= 6 else "ok" if n >= 3 else "stretch"), hits


def applicants_count(v):
    if v is None:
        return None
    m = re.search(r"(\d[\d,]*)", str(v))
    return int(m.group(1).replace(",", "")) if m else None


def job_id(title, company):
    return hashlib.sha1(f"{norm(title)}|{norm(company)}".encode()).hexdigest()[:14]


def reject(reason):
    LOG["rejected"][reason] += 1
    return None


def raw(source, company, title, url, location="", remote=None, posted=None, text="", salary=None,
        exp_text=None, applicants=None, alt_url=None, wfh=None, direct=False):
    return dict(source=source, company=(company or "").strip(), title=(title or "").strip(), url=url,
                location=location or "", remote=remote, posted=posted, text=text or "", salary=salary,
                exp_text=exp_text, applicants=applicants, alt_url=alt_url, wfh=wfh, direct=direct)


def prefilter(r):
    """Cheap checks before any extra network call. Returns track or None."""
    if not r.get("url") or not r.get("title"):
        return reject("no url/title")
    track = which_track(r["title"])
    if not track:
        return reject("title not SEO/Data")
    if company_blocked(r["company"]):
        return reject("blocked company")
    p = to_dt(r["posted"])
    if p and (NOW - p).days > C.MAX_POST_AGE_DAYS:
        return reject(f"older than {C.MAX_POST_AGE_DAYS} days")
    mode = detect_mode(r["location"], r["text"], r["remote"], r["wfh"])
    if not location_ok(r["location"], mode, r["text"]):
        return reject("location (not NCR / not India-remote)")
    return track


def finalize(r, track):
    text = r["text"]
    blob = f"{r['title']} {r.get('exp_text') or ''} {text}"
    mn, mx = experience(f"{r.get('exp_text') or ''} {text}")
    if mn is not None and mn > C.MAX_MIN_EXPERIENCE:
        return reject(f"asks > {C.MAX_MIN_EXPERIENCE} yrs")
    if mx is not None and mx < C.MIN_MAX_EXPERIENCE:
        return reject("fresher / junior")
    pay = None
    if r["salary"]:
        pay = monthly_inr(*r["salary"])
    if not pay:
        pay = salary_from_text(f"{r.get('exp_text') or ''} {text}")
    if pay and pay[1] < C.MIN_MONTHLY_INR:
        return reject("salary below Rs 55k/month")
    apps = applicants_count(r.get("applicants"))
    if apps is not None and apps > C.MAX_APPLICANTS:
        return reject(f"> {C.MAX_APPLICANTS} applicants")
    mode = detect_mode(r["location"], text, r["remote"], r["wfh"])
    fit, hits = fit_score(track, blob)
    p = to_dt(r["posted"])
    if mn is None:
        exp = "Exp not listed"
    elif mx is None:
        exp = f"{mn}+ yrs"
    else:
        exp = f"{mn}–{mx} yrs"
    return {
        "v": SCHEMA,
        "id": job_id(r["title"], r["company"]),
        "track": track,
        "media": is_media(r["company"], text),
        "fit": fit,
        "hits": hits[:10],
        "company": r["company"] or "(company not shown)",
        "title": r["title"],
        "location": r["location"] or ("Remote" if mode == "Remote" else ""),
        "mode": mode,
        "exp": exp,
        "exp_min": mn,
        "pay": f"₹{fmt_k(pay[0])}–{fmt_k(pay[1])}/month" if pay and pay[0] != pay[1] else (
            f"₹{fmt_k(pay[1])}/month" if pay else ""),
        "pay_hi": pay[1] if pay else None,
        "posted_at": p.isoformat() if p else None,
        "applicants": apps,
        "source": r["source"],
        "direct": bool(r.get("direct")),
        "url": r["url"],
        "alt_url": r.get("alt_url") or "",
        "resume": C.RESUME_FOR[track],
        "group": r.get("_group", r["source"]),
        "desc": re.sub(r"\s+", " ", text)[:2500],
    }


# ---------------------------------------------------------------- sources
def src_jobspy():
    try:
        from jobspy import scrape_jobs
    except Exception as e:
        log("  ! jobspy not installed:", e)
        return []
    out, dead, fails = [], set(), Counter()
    plan = [(term, places, remote) for terms in C.JOBSPY_TERMS.values() for term in terms
            for places, remote in C.JOBSPY_PLACES]
    # interleave sites so one slow/blocked site doesn't eat the whole budget
    for term, places, remote in plan:
        for site in C.JOBSPY_SITES:
            if site in dead or over_budget():
                continue
            kw = dict(site_name=[site], search_term=term, location=places[site], results_wanted=C.JOBSPY_RESULTS,
                      country_indeed="India", verbose=0, description_format="plain")
            if site == "indeed" and remote:
                kw["is_remote"] = True          # Indeed can't combine remote + hours_old
            else:
                kw["hours_old"] = C.JOBSPY_HOURS_OLD
                if remote:
                    kw["is_remote"] = True
            if site == "google":
                where = "remote India" if remote else "in Delhi NCR"
                kw["google_search_term"] = f"{term} jobs {where} since 3 days ago"
            name = f"{site.title()} (JobSpy)"
            st = LOG["sources"].setdefault(name, {"fetched": 0, "kept": 0, "error": ""})
            try:
                df = scrape_jobs(**kw)
                errs = (getattr(df, "attrs", {}) or {}).get("errors") or {}
                if errs:
                    st["error"] = str(list(errs.values())[0])[:160]
                rows = df.to_dict("records")
            except Exception as e:
                rows = []
                st["error"] = str(e)[:160]
                log(f"  ! {site} '{term}': {str(e)[:120]}")
            if st["error"] and not rows:
                fails[site] += 1
                if fails[site] >= 3:  # blocked / broken for this run
                    dead.add(site)
                    log(f"  ! {site} disabled for this run: {st['error'][:100]}")
            else:
                fails[site] = 0
                st["error"] = ""
            st["fetched"] += len(rows)
            for j in rows:
                j = {k: (None if isinstance(v, float) and v != v else v) for k, v in j.items()}
                loc = j.get("location")
                if isinstance(loc, dict):
                    loc = ", ".join(str(x) for x in [loc.get("city"), loc.get("state"), loc.get("country")] if x)
                sal = None
                if j.get("min_amount") or j.get("max_amount"):
                    sal = (j.get("min_amount"), j.get("max_amount"), j.get("currency") or "INR", j.get("interval"))
                url = j.get("job_url")
                direct = j.get("job_url_direct")
                out.append(raw(name.split(" ")[0], j.get("company"), j.get("title"), direct or url, loc or "",
                               j.get("is_remote") or (remote and site != "naukri"), j.get("date_posted"),
                               j.get("description") or "", sal, j.get("experience_range"), None,
                               url if direct else None, j.get("work_from_home_type"), bool(direct)))
                out[-1]["_site"] = site
                out[-1]["_lid"] = j.get("id")
                out[-1]["_li_url"] = url
            time.sleep(2.5 if site == "linkedin" else 1.2)
    return out


def linkedin_details(r):
    """Fill JD text + applicant count for a LinkedIn job (public guest page)."""
    m = re.search(r"(\d{8,})", str(r.get("_li_url") or r.get("_lid") or r["url"]))
    if not m:
        return
    page = get(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{m.group(1)}", as_json=False, timeout=15)
    if not page:
        return
    d = re.search(r'class="show-more-less-html__markup[^"]*"[^>]*>(.*?)</div>', page, re.S)
    if d:
        r["text"] = strip_html(d.group(1))
    a = re.search(r'num-applicants__caption[^>]*>\s*([^<]+)<', page) or re.search(
        r'(Be among the first \d+ applicants|Over \d+ applicants|\d+ applicants)', page)
    if a:
        r["applicants"] = a.group(1).strip()
    crit = re.findall(r'description__job-criteria-text[^>]*>\s*([^<]+)<', page)
    if crit:
        r["exp_text"] = (r.get("exp_text") or "") + " " + " ".join(c.strip() for c in crit)


def src_himalayas():
    out = []
    for terms in C.REMOTE_TERMS.values():
        for q in terms:
            data = get("https://himalayas.app/jobs/api/search", {"q": q, "country": "IN", "sort": "recent"})
            for j in (data or {}).get("jobs", []):
                restr = [str(x).lower() for x in (j.get("locationRestrictions") or [])]
                loc = "Remote (" + (", ".join(restr) if restr else "worldwide") + ")"
                sal = None
                if j.get("minSalary") or j.get("maxSalary"):
                    sal = (j.get("minSalary"), j.get("maxSalary"), j.get("currency") or "USD",
                           j.get("salaryPeriod") or "yearly")
                out.append(raw("Himalayas", j.get("companyName"), j.get("title"), j.get("applicationLink"), loc, True,
                               j.get("pubDate"), (j.get("excerpt") or "") + "\n" + strip_html(j.get("description")),
                               sal))
            time.sleep(1.5)
    return out


def src_remotive():
    out = []
    for terms in C.REMOTE_TERMS.values():
        data = get("https://remotive.com/api/remote-jobs", {"search": terms[0], "limit": 80})
        for j in (data or {}).get("jobs", []):
            out.append(raw("Remotive", j.get("company_name"), j.get("title"), j.get("url"),
                           "Remote (" + (j.get("candidate_required_location") or "") + ")", True,
                           j.get("publication_date"), strip_html(j.get("description")) + " " + (j.get("salary") or "")))
        time.sleep(31)  # Remotive allows ~2 requests/minute
    return out


def src_jobicy():
    out = []
    for tag in ["seo", "data-analyst", "data-science", "business-analyst", "analytics"]:
        data = get("https://jobicy.com/api/v2/remote-jobs", {"count": 50, "tag": tag})
        for j in (data or {}).get("jobs", []):
            sal = None
            if j.get("annualSalaryMin") or j.get("annualSalaryMax"):
                sal = (j.get("annualSalaryMin"), j.get("annualSalaryMax"), j.get("salaryCurrency") or "USD", "yearly")
            out.append(raw("Jobicy", j.get("companyName"), j.get("jobTitle"), j.get("url"),
                           "Remote (" + str(j.get("jobGeo") or "") + ")", True, j.get("pubDate"),
                           strip_html(j.get("jobDescription") or j.get("jobExcerpt")), sal))
        time.sleep(1)
    return out


def src_remoteok():
    out = []
    for tag in ["seo", "analyst", "data"]:
        data = get("https://remoteok.com/api", {"tags": tag})
        for j in (data or [])[1:] if isinstance(data, list) else []:
            sal = (j.get("salary_min"), j.get("salary_max"), "USD", "yearly") if j.get("salary_max") else None
            out.append(raw("RemoteOK", j.get("company"), j.get("position"), j.get("apply_url") or j.get("url"),
                           "Remote (" + (j.get("location") or "") + ")", True, j.get("date"),
                           strip_html(j.get("description")), sal))
        time.sleep(2)
    return out


def src_workingnomads():
    data = get("https://www.workingnomads.com/api/exposed_jobs/") or []
    return [raw("Working Nomads", j.get("company_name"), j.get("title"), j.get("url"),
                "Remote (" + (j.get("location") or "") + ")", True, j.get("pub_date"),
                strip_html(j.get("description"))) for j in data if isinstance(j, dict)]


def src_lever():
    out = []
    for slug in C.LEVER:
        data = get(f"https://api.lever.co/v0/postings/{slug}", {"mode": "json"})
        for j in data or []:
            cat = j.get("categories") or {}
            locs = cat.get("allLocations") or [cat.get("location") or ""]
            loc = ", ".join(x for x in locs if x)
            sr = j.get("salaryRange") or {}
            sal = (sr.get("min"), sr.get("max"), sr.get("currency"), sr.get("interval")) if sr else None
            text = (j.get("descriptionPlain") or "") + "\n" + "\n".join(
                f"{l.get('text')}: {strip_html(l.get('content'))}" for l in (j.get("lists") or []))
            text += "\n" + (j.get("additionalPlain") or "")
            out.append(raw(f"{slug} careers (Lever)", slug.replace("-", " ").title(), j.get("text"), j.get("hostedUrl"),
                           loc, j.get("workplaceType") == "remote", j.get("createdAt"), text, sal,
                           wfh=j.get("workplaceType"), direct=True))
    return out


def src_greenhouse():
    out = []
    for slug in C.GREENHOUSE:
        data = get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", {"content": "true"})
        for j in (data or {}).get("jobs", []):
            loc = (j.get("location") or {}).get("name", "")
            text = strip_html(html.unescape(j.get("content") or ""))
            out.append(raw(f"{slug} careers (Greenhouse)", j.get("company_name") or slug.title(), j.get("title"),
                           j.get("absolute_url"), loc, "remote" in loc.lower(),
                           j.get("first_published") or j.get("updated_at"), text, direct=True))
    return out


def src_ashby():
    out = []
    for slug in C.ASHBY:
        data = get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", {"includeCompensation": "true"})
        for j in (data or {}).get("jobs", []):
            locs = [j.get("location") or ""] + [x.get("location", "") for x in (j.get("secondaryLocations") or [])]
            text = j.get("descriptionPlain") or strip_html(j.get("descriptionHtml"))
            comp = (j.get("compensation") or {}).get("compensationTierSummary") or ""
            out.append(raw(f"{slug} careers (Ashby)", slug.title(), j.get("title"), j.get("jobUrl"), ", ".join(locs),
                           bool(j.get("isRemote")), j.get("publishedAt"), text + "\n" + comp,
                           wfh=j.get("workplaceType"), direct=True))
    return out


def src_workable():
    out = []
    for slug in C.WORKABLE:
        data = get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}", {"details": "true"})
        name = (data or {}).get("name") or slug
        for j in (data or {}).get("jobs", []):
            loc = ", ".join(x for x in [j.get("city"), j.get("state"), j.get("country")] if x)
            out.append(raw(f"{slug} careers (Workable)", name, j.get("title"), j.get("url") or j.get("shortlink"), loc,
                           bool(j.get("telecommuting")), j.get("published_on") or j.get("created_at"),
                           strip_html(j.get("description")), direct=True))
    return out


def src_recruitee():
    out = []
    for slug in C.RECRUITEE:
        data = get(f"https://{slug}.recruitee.com/api/offers/")
        for j in (data or {}).get("offers", []):
            loc = j.get("location") or ", ".join(x for x in [j.get("city"), j.get("country")] if x)
            sal = j.get("salary") or {}
            s = (sal.get("min"), sal.get("max"), sal.get("currency"), sal.get("period")) if sal.get("max") else None
            out.append(raw(f"{slug} careers (Recruitee)", j.get("company_name") or slug.title(), j.get("title"),
                           j.get("careers_url"), loc, bool(j.get("remote")), j.get("published_at"),
                           strip_html(j.get("description")) + "\n" + strip_html(j.get("requirements")), s,
                           direct=True))
    return out


def src_smartrecruiters():
    out = []
    for cid in C.SMARTRECRUITERS:
        data = get(f"https://api.smartrecruiters.com/v1/companies/{cid}/postings", {"limit": 100, "country": "in"})
        for j in (data or {}).get("content", []):
            l = j.get("location") or {}
            loc = ", ".join(x for x in [l.get("city"), l.get("region"), l.get("country")] if x)
            exp = (j.get("experienceLevel") or {}).get("label", "")
            out.append(raw(f"{cid} careers (SmartRecruiters)", (j.get("company") or {}).get("name") or cid,
                           j.get("name"), f"https://jobs.smartrecruiters.com/{cid}/{j.get('id')}", loc,
                           bool(l.get("remote")), j.get("releasedDate"), exp, exp_text=exp,
                           wfh="hybrid" if l.get("hybrid") else None, direct=True))
    return out


SOURCES = [("JobSpy (Indeed/LinkedIn/Naukri/Google)", src_jobspy), ("Himalayas", src_himalayas),
           ("Jobicy", src_jobicy), ("RemoteOK", src_remoteok), ("Working Nomads", src_workingnomads),
           ("Lever careers", src_lever), ("Greenhouse careers", src_greenhouse), ("Ashby careers", src_ashby),
           ("Workable careers", src_workable), ("Recruitee careers", src_recruitee),
           ("SmartRecruiters careers", src_smartrecruiters), ("Remotive", src_remotive)]


# ---------------------------------------------------------------- link check
DEAD_WORDS = ["no longer accepting", "no longer available", "job has expired", "position has been filled",
              "this job is closed", "job not found", "this job has been closed", "posting has closed",
              "job is no longer open", "has been removed"]


def link_alive(url):
    if any(x in url for x in ["linkedin.com", "naukri.com", "indeed.com", "google.com"]):
        return True  # these block bots; trust the scraper
    try:
        r = requests.get(url, headers=UA, timeout=12, allow_redirects=True)
        if r.status_code in (404, 410):
            return False
        if r.status_code >= 400:
            return True  # 403/429 = bot blocked, not dead
        body = r.text.lower()[:150000]
        return not any(d in body for d in DEAD_WORDS)
    except Exception:
        return True


# ---------------------------------------------------------------- storage
def load_json(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_db(seen, applied):
    db = DATA / "jobs.db"
    tmp = DATA / "jobs.db.tmp"
    if tmp.exists():
        tmp.unlink()
    con = sqlite3.connect(tmp)
    con.executescript("""
    CREATE TABLE jobs(id TEXT PRIMARY KEY, track TEXT, media INTEGER, fit TEXT, company TEXT, title TEXT,
      location TEXT, mode TEXT, exp TEXT, pay TEXT, pay_hi_monthly_inr INTEGER, posted_at TEXT, first_seen TEXT,
      applicants INTEGER, source TEXT, url TEXT);
    CREATE TABLE applications(id TEXT PRIMARY KEY, status TEXT, applied_on TEXT, updated_on TEXT, company TEXT,
      title TEXT, track TEXT, source TEXT, url TEXT, notes TEXT);
    """)
    con.executemany("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [
        (j["id"], j["track"], int(j.get("media", False)), j["fit"], j["company"], j["title"], j["location"],
         j["mode"], j["exp"], j["pay"], j.get("pay_hi"), j.get("posted_at"), j.get("first_seen"),
         j.get("applicants"), j["source"], j["url"]) for j in seen.values()])
    con.executemany("INSERT INTO applications VALUES(?,?,?,?,?,?,?,?,?,?)", [
        (k, a.get("status"), a.get("applied_on"), a.get("updated_on"), a.get("company"), a.get("title"),
         a.get("track"), a.get("source"), a.get("url"), a.get("notes", "")) for k, a in applied.items()])
    con.commit()
    con.close()
    tmp.replace(db)


def write_csv(applied):
    with open(DATA / "applied.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["status", "applied_on", "company", "title", "track", "source", "url", "notes"])
        for a in sorted(applied.values(), key=lambda a: a.get("applied_on") or "", reverse=True):
            w.writerow([a.get("status"), a.get("applied_on"), a.get("company"), a.get("title"), a.get("track"),
                        a.get("source"), a.get("url"), a.get("notes", "")])


# ---------------------------------------------------------------- main
def main():
    DATA.mkdir(exist_ok=True)
    DOCS.mkdir(exist_ok=True)
    load_fx()
    seen = {k: v for k, v in load_json(SEEN, {}).items() if isinstance(v, dict) and v.get("v") == SCHEMA}
    applied = (load_json(APPLIED, {}) or {}).get("jobs", {})

    raws = []
    for name, fn in SOURCES:
        if over_budget() and name != "JobSpy (Indeed/LinkedIn/Naukri/Google)":
            log(f"-> {name}: skipped (time budget)")
            continue
        log(f"-> {name}")
        t0 = time.time()
        try:
            got = [r for r in fn() if r]
            for r in got:
                r["_group"] = f"{r['_site'].title()} (JobSpy)" if r.get("_site") else name
        except Exception as e:
            log(f"  ! {name} crashed: {e}")
            LOG["sources"].setdefault(name, {})["error"] = str(e)[:160]
            got = []
        if not name.startswith("JobSpy"):
            st = LOG["sources"].setdefault(name, {"fetched": 0, "kept": 0, "error": ""})
            st["fetched"] = st.get("fetched", 0) + len(got)
        log(f"   {len(got)} fetched in {time.time() - t0:.0f}s")
        raws.extend(got)

    # cheap filters first
    candidates = []
    for r in raws:
        track = prefilter(r)
        if track:
            candidates.append((r, track))

    # LinkedIn JD + applicant count for NEW linkedin jobs only
    n = 0
    for r, track in candidates:
        if r.get("_site") == "linkedin" and job_id(r["title"], r["company"]) not in seen and n < C.LINKEDIN_DETAIL_CAP:
            if over_budget() and n > 10:
                break
            linkedin_details(r)
            n += 1
            time.sleep(1.2)
    log(f"LinkedIn details fetched: {n}")

    fresh = {}
    for r, track in candidates:
        j = finalize(r, track)
        if not j:
            continue
        if j["id"] in applied:
            LOG["rejected"]["already applied / skipped"] += 1
            continue
        old = fresh.get(j["id"])
        # prefer direct company links, then the one with a salary / longer JD
        if not old or (j["direct"], bool(j["pay"]), len(j["desc"])) > (old["direct"], bool(old["pay"]), len(old["desc"])):
            fresh[j["id"]] = j

    # link check only for jobs we have never seen
    new_ids = [k for k in fresh if k not in seen]
    with ThreadPoolExecutor(8) as ex:
        alive = dict(zip(new_ids, ex.map(lambda k: link_alive(fresh[k]["url"]), new_ids)))
    today = datetime.now(IST).isoformat(timespec="minutes")
    new = 0
    for k, j in fresh.items():
        if k in seen:
            j["first_seen"] = seen[k].get("first_seen", today)
            j["posted_at"] = j["posted_at"] or seen[k].get("posted_at")
            seen[k] = j
        elif alive.get(k, True):
            j["first_seen"] = today
            seen[k] = j
            new += 1
        else:
            LOG["rejected"]["dead link"] += 1
        if k in seen and j.get("group") in LOG["sources"]:
            LOG["sources"][j["group"]]["kept"] = LOG["sources"][j["group"]].get("kept", 0) + 1

    # history
    hist_cut = NOW - timedelta(days=C.HISTORY_DAYS)
    seen = {k: v for k, v in seen.items() if (to_dt(v.get("first_seen")) or NOW) >= hist_cut}
    slim_cut = NOW - timedelta(days=C.BOARD_DAYS)
    store = {k: ({**v, "desc": ""} if (to_dt(v.get("first_seen")) or NOW) < slim_cut else v) for k, v in seen.items()}
    SEEN.write_text(json.dumps(store, ensure_ascii=False, indent=0), encoding="utf-8")

    # the board: not applied, not too old
    board_cut = NOW - timedelta(days=C.BOARD_DAYS)
    board = []
    for j in seen.values():
        if j["id"] in applied:
            continue
        ref = to_dt(j.get("posted_at")) or to_dt(j.get("first_seen")) or NOW
        if ref < board_cut:
            continue
        board.append(j)
    board.sort(key=lambda j: (j.get("posted_at") or j.get("first_seen") or ""), reverse=True)

    run = {
        "updated": datetime.now(IST).strftime("%d %b %Y, %I:%M %p IST"),
        "updated_iso": NOW.isoformat(),
        "new_this_run": new,
        "minutes": round((time.time() - START) / 60, 1),
        "sources": LOG["sources"],
        "rejected": dict(LOG["rejected"].most_common()),
        "fx_usd": round(FX.get("USD", 0), 2),
        "rules": {"min_monthly_inr": C.MIN_MONTHLY_INR, "max_min_exp": C.MAX_MIN_EXPERIENCE,
                  "max_post_age_days": C.MAX_POST_AGE_DAYS, "board_days": C.BOARD_DAYS},
    }
    (DOCS / "jobs.json").write_text(json.dumps({**run, "jobs": board}, ensure_ascii=False), encoding="utf-8")
    (DATA / "run_log.json").write_text(json.dumps(run, ensure_ascii=False, indent=1), encoding="utf-8")
    (DOCS / "applied.json").write_text(json.dumps({"jobs": applied}, ensure_ascii=False), encoding="utf-8")
    write_csv(applied)
    write_db(seen, applied)
    log(f"Done in {run['minutes']} min: {new} new, {len(board)} on board, {len(applied)} applied")
    log("Rejected:", dict(LOG["rejected"].most_common(12)))


if __name__ == "__main__":
    sys.exit(main())
