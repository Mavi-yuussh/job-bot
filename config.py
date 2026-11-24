# ------------------------------------------------------------
#  Settings for the job bot. Change these freely.
# ------------------------------------------------------------

# Words that must appear in the JOB TITLE for each track
TRACKS = {
    "seo": ["seo", "search engine", "aeo", "geo specialist", "organic growth", "search specialist"],
    "data": ["data analyst", "web analyst", "digital analyst", "analytics", "bi analyst",
             "business intelligence", "power bi", "reporting analyst", "insights analyst", "ga4"],
}

# What to search for on each source
SEARCH_TERMS = {
    "seo": ["seo", "technical seo", "seo specialist"],
    "data": ["data analyst", "web analyst", "digital analyst", "power bi"],
}

# Skip jobs whose title has any of these
EXCLUDE_TITLE = ["intern", "internship", "fresher", "trainee", "head of", "director", "vp ",
                 "vice president", "chief", "principal", "content writer", "sales", "telecaller"]

# Your skills - used to score how well a job fits you
MY_SKILLS = ["seo", "technical seo", "schema", "structured data", "core web vitals", "search console",
             "gsc", "ga4", "google analytics", "tag manager", "gtm", "ahrefs", "semrush", "screaming frog",
             "aeo", "geo", "ai overviews", "discover", "news", "sql", "bigquery", "power bi", "dax",
             "tableau", "looker", "python", "pandas", "excel", "apps script", "dashboard", "etl",
             "a/b", "statistics", "llm", "media", "publisher"]

# India locations you are happy with (office / hybrid)
GOOD_INDIA_PLACES = ["noida", "delhi", "new delhi", "gurugram", "gurgaon", "ncr", "ghaziabad", "faridabad"]

# Max years of experience a job may ask for (you have ~2.7)
MAX_MIN_EXPERIENCE = 5

# Drop a job from the board after this many days
KEEP_DAYS = 30

# Company career pages on Lever (jobs.lever.co/<slug>). Add more slugs you find.
LEVER_COMPANIES = ["paytm", "weekdayworks", "shyftlabs"]

# Company career pages on Greenhouse (boards.greenhouse.io/<token>). Add tokens you find.
GREENHOUSE_COMPANIES = []

# Adzuna (free key from developer.adzuna.com) - searches Indian job boards.
# Put ADZUNA_APP_ID and ADZUNA_APP_KEY as GitHub secrets / env vars. Optional.
ADZUNA_WHERE = ["Noida", "Delhi", "Gurgaon"]
