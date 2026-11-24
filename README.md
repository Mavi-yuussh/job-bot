# Job Bot – Setup Guide (sirf ghar ke laptop + personal accounts se)

**Ye kya karega:** din mein 3 baar (7:10 AM, 1:10 PM, 7:10 PM IST), roz, apne aap nayi SEO aur Data/Web Analyst jobs dhundhega, check karega ki job abhi bhi open hai, website update karega, aur nayi jobs Telegram pe bhejega. Tumhara laptop band ho tab bhi chalega, kyunki ye GitHub ke servers pe chalta hai. Bilkul free hai.

Pehli baar setup mein ~20 minute lagenge, uske baad kuch nahi karna.

---

## STEP 1 – GitHub account
1. **github.com** kholo, **Sign up** dabao, aur **personal Gmail** se account banao. Username yaad rakhna, jaise `manny-jobs-2026`.

## STEP 2 – Repository banao
1. Upar right mein **+** pe click karo, phir **New repository**.
2. Repository name: `job-bot`
3. **Public** select karo. Free mein website sirf public repo pe milti hai, aur page pe tumhara naam kahin nahi hai.
4. **Create repository** dabao.

## STEP 3 – Files upload karo
1. `job-bot.zip` ko laptop pe **Extract** karo, ek folder ban jayega.
2. Repo page pe **uploading an existing file** link pe click karo.
3. Extract kiye folder ke **andar** jitni bhi cheezein hain (`.github`, `data`, `docs`, `jobs_bot.py`, `config.py`, `requirements.txt`, ...), sabko select karke browser mein drag kar do.
4. Neeche **Commit changes** dabao.
5. **Check karo:** repo mein `.github/workflows/daily.yml` dikhna chahiye.
   Agar `.github` folder upload nahi hua, toh **Add file → Create new file** pe jao, naam mein `.github/workflows/daily.yml` likho, extract kiye folder mein `.github/workflows/daily.yml` file ko Notepad mein kholo, uska poora content copy karke yahan paste karo, aur **Commit changes** dabao.

## STEP 4 – Website on karo
1. Repo mein **Settings** kholo, left menu se **Pages**.
2. **Source** mein **GitHub Actions** chuno. ("Deploy from a branch" mat chunna.)

## STEP 5 – Telegram alert (phone pe turant nayi jobs)
1. Telegram mein **@BotFather** search karo, `/newbot` bhejo, bot ka koi bhi naam do, aur username aisa do jo `bot` pe khatam ho (jaise `manny_jobs_bot`). Wo ek **token** dega, use copy kar lo.
2. Apne naye bot pe jao aur **Start** dabao. Ye zaroori hai.
3. Telegram mein **@userinfobot** search karo aur Start dabao. Wo jo **Id** (number) dikhayega, use copy kar lo.
4. GitHub repo mein **Settings → Secrets and variables → Actions → New repository secret** pe jao:
   - Name `TELEGRAM_BOT_TOKEN`, Secret mein token daalo, phir **Add secret**
   - Name `TELEGRAM_CHAT_ID`, Secret mein Id number daalo, phir **Add secret**

## STEP 6 – Pehli baar chalao
1. Repo mein **Actions** tab kholo. Agar button aaye toh **I understand my workflows, go ahead and enable them** dabao.
2. Left mein **Daily job hunt** pe click karo, phir right mein **Run workflow** aur phir hara **Run workflow** button.
3. 2–4 minute mein green ✓ aa jayega, aur Telegram pe message aayega.
4. Website ka link: **`https://<username>.github.io/job-bot/`**
   (Settings → Pages pe bhi ye link dikhega.)

## STEP 7 – Phone pe app ki tarah
1. Chrome mein link kholo, ⋮ menu mein **Add to Home screen** dabao.
2. (Optional) Telegram message mein website ka link bhi chahiye toh **Settings → Secrets and variables → Actions → Variables tab → New variable** pe jao, Name `BOARD_URL` aur Value mein apna website link daalo.

**Ho gaya.** Ab kuch karne ki zaroorat nahi hai.

---

## Roz ka routine (sirf 20–30 minute)
1. Subah Telegram pe nayi jobs ka message aayega.
2. **STRONG** wali jobs pehle kholo. JD padho, resume ke Skills aur Summary mein JD ke exact shabd daalo (sirf wahi jo tumhe sach mein aata hai), aur **usi din** apply karo.
3. Board pe us job ka status **Applied** kar do.
4. Board ke **Portals** tab se Naukri/Foundit/Instahyre pe bhi 10 minute dekh lo. Bot unhe nahi padhta, kyunki wo scraping block karte hain.

## Kuch gadbad ho toh
- **Actions mein laal ✗:** us run pe click karo, laal step kholo, uska screenshot apne **personal** Claude account se bhej do.
- **Telegram message nahi aaya:** check karo ki bot pe Start dabaya tha, aur secrets ke naam bilkul sahi hain (capital letters mein).
- **Website pe purana data dikh raha hai:** phone pe page ko neeche kheench ke refresh karo.
- GitHub ke scheduled runs kabhi-kabhi 10–30 minute late chalte hain. Ye normal hai.

## Settings badalni ho
GitHub pe `config.py` kholo, ✏️ pe click karke edit karo, phir Commit changes dabao:
- `SEARCH_TERMS`: kya search karna hai
- `GOOD_INDIA_PLACES`: kaunse shehar chalenge
- `MAX_MIN_EXPERIENCE`: kitne saal tak ka experience maangne wali jobs chahiye
- `LEVER_COMPANIES` / `GREENHOUSE_COMPANIES`: jis company ka career page `jobs.lever.co/xyz` ya `boards.greenhouse.io/xyz` pe hai, uska `xyz` yahan add karo

## Optional – Indian portals ki jobs (Adzuna, free)
**developer.adzuna.com** pe free account banao, aur `ADZUNA_APP_ID` aur `ADZUNA_APP_KEY` ko Secrets mein daal do. Isse Noida/Delhi/Gurgaon ki aur jobs aayengi.
