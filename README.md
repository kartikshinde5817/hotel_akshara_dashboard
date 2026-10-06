# Hotel Akshara – Billing (Netlify version)

Tables → Hotel / Beer Bar menu → separate bills → daily Hotel & Bar day bills → yearly / month-to-month downloads.

```
public/index.html            the whole app screen (static)
netlify/functions/api.mjs    the API  (served at /api/*)
netlify/functions/lib/       storage layer (Netlify Blobs) + starting menu (first run only)
tools/export_db.py           export the OLD Python database (akshara.db) to JSON
tools/dev-server.mjs         run everything on your own PC for testing
main.py                      the old stand-alone Python version (not used by Netlify)
```

Data (menu, open tables, bills, settings) is stored in **Netlify Blobs** – built into Netlify, nothing to set up and it survives redeploys.

## Deploy

1. Push this folder to your GitHub repo (`git add . && git commit -m "netlify version" && git push`).
2. In Netlify: **Add new site → Import from Git** (or open your existing site → Site configuration → Build & deploy → link the repo). The settings are read from `netlify.toml`; leave the build command empty.
3. Open the site. The **first time** it asks you to choose a password (min. 6 characters). Everyone who uses the billing needs this password.
   - Optional: instead, set `APP_PASSWORD` (and `ADMIN_PIN`) under Site configuration → Environment variables *before* the first visit.
4. Admin PIN is **1234** at first – change it in Admin → Settings straight away.

> Do **not** use drag-and-drop "Netlify Drop" – it cannot install the one dependency (`@netlify/blobs`). Use Git or `npx netlify-cli deploy --prod`.

## Bring your old data across (menu changes + old bills)

```
python tools/export_db.py            # creates akshara-export.json from akshara.db
```
Then in the live site: **Admin → Settings → Import old data** → choose `akshara-export.json`.
This replaces the menu and bills on the site with the ones from the file (bill numbers continue from the highest old number).

## Passwords

| What | Default | Change in |
|---|---|---|
| App password (to open the site) | you choose it on first visit | Admin → Settings → "New app password" |
| Admin PIN (menu, settings, delete bill) | 1234 | Admin → Settings → "New PIN" |

The 🔒 button in the top bar logs a device out.

## Good to know

- The screen refreshes running tables every 20 seconds (only while the page is open and visible) to stay within Netlify's free function allowance. Your own changes are saved instantly.
- Times use India time (`Asia/Kolkata`). Change with the environment variable `APP_TIMEZONE`.
- Two phones editing the *same* table at the same moment: the last save wins. Different tables never clash.
- Back up: Reports → Download Bills (Excel) – year or month range.

## Test on your own PC

```
npm install
npm run dev        # http://localhost:8888  (data kept in ./.local-data)
```
