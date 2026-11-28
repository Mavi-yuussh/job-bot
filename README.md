# Manny Job Board v2

Live: **https://mavi-yuussh.github.io/job-bot/**

## Ye kya karta hai
- Har **3 ghante** GitHub pe bot chalta hai (laptop band ho tab bhi) aur nayi jobs laata hai:
  - **Indeed India, LinkedIn, Naukri, Google Jobs** (JobSpy se)
  - **Remote:** Himalayas, Remotive, Jobicy, RemoteOK, Working Nomads
  - **Company career pages:** Lever, Greenhouse, Ashby, Workable, Recruitee, SmartRecruiters (list `config.py` mein)
- Sirf ye jobs rakhta hai: **SEO / Data-Business Analyst / Data Scientist**, Delhi NCR office-hybrid **ya** India se remote,
  **3–5 saal** experience, salary likhi ho to **₹55k+/month** (dollar wali convert hoti hai), **last 7 din** mein post,
  LinkedIn pe **100 se kam applicants**, aur jo abroad jaane ko bole wo hata deta hai.
- Media companies ki jobs pe **Media** tag lagta hai (Media tab).
- Koi email / Telegram alert **nahi** – tum khud roz ka alarm lagao.

## Roz ka routine (alarm baje → 20 min)
1. Board kholo → **Sabse fresh job kholo →**
2. **Apply ↗** → form bharo → wapas aao → **✓ Applied** (card gayab, Applied tab mein save).
   Wapas aate hi page khud poochta hai "Apply kar diya?".
3. Card pe **Email / ATS** → ATS match %, missing keywords, resume summary, cold email, LinkedIn note – sab copy-paste ready.
4. Board pe kam jobs ho to **Portals** tab – har link pe filters (24 ghante, 3 yrs, salary) already lage hain.

## Applied list kahan save hoti hai
- Browser mein turant, aur **Settings → GitHub token** daaloge to repo ki `data/applied.json` mein bhi (phone + laptop same list).
- Har run ke baad bot banata hai: `data/applied.csv` (Excel), `data/jobs.db` (SQLite – tables `jobs`, `applications`).
  Example SQL: `SELECT status, COUNT(*) FROM applications GROUP BY status;`
- Applied/Skip ki hui job dobara kabhi board pe nahi aati.

## Settings badalni ho
GitHub pe `config.py` → ✏️ → edit → Commit. Jaise `MIN_MONTHLY_INR`, `MAX_MIN_EXPERIENCE`, `GOOD_INDIA_PLACES`,
search words (`JOBSPY_TERMS`), media companies, career-page slugs.

## Kuch gadbad ho
- Board pe **Settings → Bot health** dekho: kaunsa source kitni jobs laaya, kahan error.
- Actions tab mein laal ✗ ho to screenshot Claude ko bhejo.
- GitHub ke scheduled runs kabhi 10–30 min late chalte hain – normal hai.
