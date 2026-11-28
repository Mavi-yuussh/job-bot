# ============================================================
#  Job bot settings. Change anything here and commit on GitHub.
#  (GitHub pe ye file kholo -> pencil icon -> edit -> Commit changes)
# ============================================================

# ---------- Kaun si jobs chahiye ----------
# Words in the JOB TITLE that decide the track. Order matters: first match wins.
TRACKS = {
    "science": ["data scientist", "data science", "machine learning scientist", "decision scientist",
                "applied scientist", "ml scientist"],
    "seo": ["seo", "search engine", "aeo ", "geo specialist", "organic growth", "organic search",
            "search specialist", "search analyst", "search marketing specialist"],
    "data": ["data analyst", "business analyst", "web analyst", "digital analyst", "product analyst",
             "marketing analyst", "analytics analyst", "analytics specialist", "analytics executive",
             "analytics associate", "analytics manager", "bi analyst", "bi developer", "business intelligence",
             "power bi", "reporting analyst", "insights analyst", "insight analyst", "ga4", "audience analyst",
             "growth analyst", "data & analytics", "data and analytics", "web analytics", "digital analytics",
             "mis analyst", "research analyst - data", "data specialist"],
}

TRACK_NAMES = {"seo": "SEO", "data": "Data / Business Analyst", "science": "Data Scientist"}

# Which resume to upload for each track
RESUME_FOR = {"seo": "SEO resume", "data": "Data Analyst resume", "science": "Data Analyst resume (ya Data Scientist wala)"}

# Skip a job if its title has any of these
EXCLUDE_TITLE = ["intern", "internship", "fresher", "trainee", "apprentice", "head of", "director", "vp ",
                 "vice president", "chief", "principal", "staff ", "content writer", "copywriter", "sales",
                 "telecaller", "tele caller", "data entry", "graphic", "video editor", "seo content",
                 "part time", "part-time", "freelance", "commission", "unpaid", "teacher", "trainer", "tutor",
                 "faculty", "professor", "sap ", "salesforce", "servicenow", "workday", "data engineer",
                 "software engineer", "software developer", "web developer", "app developer", "php developer",
                 "java developer", ".net developer", "devops", "full stack", "backend", "frontend"]

# Skip these companies (your current employer, scam-ish agencies, etc.)  Whole-word match.
EXCLUDE_COMPANIES = ["abp", "abp network", "abp news", "abp live"]

# ---------- Experience ----------
# You have ~3 yrs. Show jobs that ask for at most 5 yrs as the MINIMUM...
MAX_MIN_EXPERIENCE = 5
# ...and drop fresher/junior jobs whose MAXIMUM is below this (they pay too little).
MIN_MAX_EXPERIENCE = 2

# ---------- Salary ----------
# Current salary ~Rs 30k/month. Only show jobs paying at least this much per month (INR).
# Jobs that do not show salary are KEPT (most Indian jobs hide it) and marked "Salary not listed".
MIN_MONTHLY_INR = 55000
# Fallback exchange rates (INR per 1 unit). The bot tries to fetch live rates first.
FX_FALLBACK = {"INR": 1, "USD": 88.5, "EUR": 102, "GBP": 117, "CAD": 63, "AUD": 58, "SGD": 68,
               "AED": 24, "NZD": 52, "CHF": 110, "JPY": 0.58, "PHP": 1.5}

# ---------- Freshness ----------
MAX_POST_AGE_DAYS = 7     # ignore jobs posted more than this many days ago
BOARD_DAYS = 10           # a job leaves the board this many days after it was posted / first seen
HISTORY_DAYS = 90         # how long every seen job is kept in data/jobs.db
MAX_APPLICANTS = 100      # LinkedIn: skip jobs that already have more applicants than this

# ---------- Location ----------
# Office / hybrid jobs must be in one of these. Remote jobs must allow India (or worldwide/APAC).
GOOD_INDIA_PLACES = ["noida", "delhi", "new delhi", "gurugram", "gurgaon", "ncr", "ghaziabad", "faridabad",
                     "greater noida"]
REMOTE_OK_WORDS = ["india", "worldwide", "anywhere", "global", "apac", "asia", "remote - in", "(in)", " in)"]
# If a remote job says any of these, you would need to be abroad -> skip (no passport/visa right now)
ABROAD_ONLY = [r"must (?:be|reside|live)[^.]{0,30}(?:in|within) (?:the )?(?:us|u\.s\.|usa|united states|uk|united kingdom|canada|europe|eu|australia)\b",
               r"authori[sz]ed to work in (?:the )?(?:us|u\.s\.|usa|united states|uk|canada|eu)\b",
               r"\b(?:us|u\.s\.) citizen", r"security clearance", r"green card",
               r"relocat\w* to (?:the )?(?:us|usa|united states|uk|dubai|uae|canada|singapore|europe|germany|australia)",
               r"\bon-?site in (?:new york|san francisco|london|dubai|singapore|toronto)"]

# ---------- Your skills (used for the fit score) ----------
SKILLS = {
    "seo": ["seo", "technical seo", "on-page", "on page", "schema", "structured data", "core web vitals",
            "page speed", "search console", "gsc", "ga4", "google analytics", "tag manager", "gtm", "ahrefs",
            "semrush", "screaming frog", "keyword research", "aeo", "geo", "ai overviews", "google discover",
            "google news", "news seo", "amp", "indexing", "crawl", "sitemap", "javascript seo", "log file",
            "content strategy", "looker studio", "publisher", "media", "news"],
    "data": ["sql", "bigquery", "power bi", "dax", "tableau", "looker", "looker studio", "python", "pandas",
             "excel", "google sheets", "apps script", "dashboard", "etl", "a/b", "statistics", "ga4",
             "google analytics", "data visualization", "reporting", "kpi", "stakeholder", "insights",
             "user behaviour", "user behavior", "traffic", "digital analytics", "media", "funnel", "cohort"],
    "science": ["python", "pandas", "numpy", "scikit", "sklearn", "machine learning", "statistics", "sql",
                "regression", "classification", "nlp", "llm", "forecast", "a/b", "experiment", "bigquery",
                "jupyter", "tableau", "power bi", "data visualization", "media", "recommendation"],
}

# ---------- Media ----------
# A job goes to the MEDIA tab if the company matches one of these, or the JD talks like a media company.
MEDIA_COMPANIES = ["times internet", "times of india", "bennett", "times network", "hindustan times", "ht media",
                   "ht digital", "india today", "living media", "aaj tak", "ndtv", "network18", "network 18",
                   "news18", "moneycontrol", "firstpost", "zee", "indian express", "jagran", "amar ujala",
                   "dainik bhaskar", "db corp", "db digital", "the hindu", "lokmat", "inshorts", "dailyhunt",
                   "verse innovation", "sharechat", "mohalla tech", "pocket fm", "pocketfm", "kuku fm", "jiostar",
                   "jiohotstar", "hotstar", "star india", "viacom18", "sony pictures networks", "culver max",
                   "sonyliv", "mx player", "pratilipi", "glance", "scroll", "theprint", "the print", "quint",
                   "newslaundry", "yourstory", "inc42", "mint", "business standard", "economic times",
                   "cricbuzz", "reuters", "bloomberg", "dow jones", "spotify", "netflix", "warner bros",
                   "disney", "buzzfeed", "vox media", "dotdash", "ziff davis", "future plc", "axios", "bbc",
                   "cnn", "outlook", "republic", "tv9", "india.com", "news nation", "the week", "manorama",
                   "mathrubhumi", "eenadu", "sakal", "patrika", "prabhat khabar", "news24", "indiatimes",
                   "gaana", "jiosaavn", "saavn", "amazon mx", "eros", "balaji", "alt balaji", "tvf",
                   "the viral fever", "pinkvilla", "scoopwhoop", "storypick", "mensxp", "idiva", "oneindia",
                   "greynium", "rediff", "quintype", "nyt", "new york times", "guardian", "economist",
                   "thomson reuters", "condé nast", "conde nast", "hearst", "publicis", "dentsu", "groupm",
                   "madison", "wpp", "ogilvy", "mediacom", "omnicom"]
MEDIA_JD_WORDS = ["newsroom", "news publisher", "digital publisher", "publishing", "media house", "media company",
                  "editorial", "broadcast", "ott", "streaming", "entertainment", "news website", "journalis",
                  "news portal", "digital media", "media network", "content platform", "podcast", "audio platform"]

# ---------- Sources ----------
# JobSpy = Indeed India, LinkedIn, Naukri, Google Jobs (public listings, small amounts, a few times a day)
JOBSPY_SITES = ["indeed", "linkedin", "naukri", "google"]
JOBSPY_TERMS = {
    "seo": ["SEO", "technical SEO", "SEO analyst"],
    "data": ["data analyst", "business analyst", "web analyst", "product analyst"],
    "science": ["data scientist"],
}
# (location for each site, remote?)
JOBSPY_PLACES = [
    ({"indeed": "New Delhi, Delhi", "linkedin": "New Delhi, Delhi, India", "naukri": "Delhi NCR",
      "google": "Delhi NCR"}, False),
    ({"indeed": "India", "linkedin": "India", "naukri": "India", "google": "India"}, True),
]
JOBSPY_RESULTS = 25            # per search
JOBSPY_HOURS_OLD = 96          # only jobs posted in the last 4 days
LINKEDIN_DETAIL_CAP = 60       # max LinkedIn JDs fetched per run (for experience/applicants check)
TIME_BUDGET_MIN = 22           # stop scraping after this many minutes

# Free remote job APIs
REMOTE_TERMS = {"seo": ["seo"], "data": ["data analyst", "business analyst"], "science": ["data scientist"]}

# Company career pages (public ATS boards). Add any company whose careers page is on these.
#   Lever:        jobs.lever.co/<slug>
#   Greenhouse:   boards.greenhouse.io/<slug>  or job-boards.greenhouse.io/<slug>
#   Ashby:        jobs.ashbyhq.com/<slug>
#   Workable:     apply.workable.com/<slug>
#   Recruitee:    <slug>.recruitee.com
#   SmartRecruiters: jobs.smartrecruiters.com/<CompanyId>
LEVER = ["jobgether", "hevodata", "paytm", "shyftlabs", "weekdayworks", "spotify", "sharechat", "pocketfm",
         "kukufm", "inshorts", "zeta", "meesho", "cred", "dream11", "games24x7", "mpl", "upgrad", "unacademy",
         "physicswallah", "cars24", "spinny", "lenskart", "nykaa", "urbancompany", "rapido", "jupiter",
         "slice", "fampay", "eightfold", "highlevel", "atlan", "sprinklr", "outplay", "plum", "pristyncare"]
GREENHOUSE = ["interviewkickstart", "yipitdata", "yipitdatajobs", "phonepe", "groww", "postman", "glance",
              "inmobi", "mediaocean", "voxmedia", "buzzfeed", "axios", "dotdashmeredith", "thenewyorktimes",
              "theathletic", "jumpcloud", "razorpaysoftwareprivatelimited", "zomato", "swiggy", "browserstack",
              "chargebee", "freshworks", "druva", "mindtickle", "whatfix", "hackerrank", "clevertap",
              "moengage", "webengage", "netcore", "airtel", "toptal", "deel", "remotecom", "gitlab",
              "doordashusa", "affirm", "coursera", "grammarly", "canva", "wiseinc", "rippling"]
ASHBY = ["sarvam", "pocketfm", "deel", "ramp", "notion", "linear", "zepto", "bluelearn", "kukufm", "atlys",
         "plivo", "smallest", "jar", "fi", "multiplier", "hyperverge"]
WORKABLE = ["azeus-convene", "remote-com", "jobgether", "turing", "uplers", "toptal", "proxify"]
RECRUITEE = ["fullcreative", "bureau", "oyorooms"]
SMARTRECRUITERS = ["PublicisGroupe", "Visa", "BoschGroup", "Experian", "NielsenIQ", "Nielsen", "Ubisoft2",
                   "McDonaldsCorporation", "Wolterskluwer", "SGS"]
