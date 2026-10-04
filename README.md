# Bright Smile Dental Clinic

Python + HTML + CSS + small JavaScript files. No React, Node build, or frontend framework.
Comments use simple Taglish, roughly 70% English and 30% Tagalog.

## Where to find things

| File/folder | Purpose |
|---|---|
| `app.py` | Pages, preview booking, Cal.com adapter, Supabase Auth and contact endpoints |
| `templates/` | Plain HTML for the pages; `base.html` shares the header/footer |
| `static/style.css` | Shared design and responsive layouts |
| `static/main.js` | Mobile menu and contact form |
| `static/booking.js` | Calendar and appointment steps |
| `static/images/` | Generated photographs; the doctor PNG has genuine transparency |
| `static/fonts/`, `static/icons/` | Local Inter font and Phosphor icons |
| `supabase-setup.sql` | Reviewable schema and access rules; not yet applied anywhere |
| `.env.example` | Empty settings; copy to private `.env` when ready |
| `CONNECT-SERVICES.md` | Where to find keys, Cal.com event IDs, and project scope instructions |
| `vercel.json` | FastAPI hosting configuration |
| `tests/test_app.py` | API boundary and preview checks |
| `legacy/` | The original three-file prototype |

## Run locally

```powershell
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
.venv/Scripts/python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Open `http://127.0.0.1:8000/`. Public pages use real paths: `/about`, `/services`, `/contact`, `/book`.
Patient forms are at `/account`. The old `/index-2.html` URL redirects to the new homepage.

## What works now

- Responsive public pages, service descriptions, native HTML FAQs, mobile navigation.
- Preview booking: service, Manila calendar, sample slots, validation, and a preview result.
- The Python health endpoint: `/api/health`.
- Contact and auth forms return truthful setup messages until configured.
- Preview bookings do not reserve a slot, send email, or store patient details.

## Connect providers later

1. Choose the clinic's Supabase project, review `supabase-setup.sql`, and apply it there. No database has been created or modified by this rebuild.
2. Set `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, and a backend-only `SUPABASE_SECRET_KEY`. Never put private keys in HTML or JavaScript.
3. In Supabase Auth, enable email/password and email confirmation. Configure the Site URL and allowed confirmation URL. The account uses server-side password grant and HttpOnly session cookies; sign-up asks users to confirm email before signing in. No custom password table exists.
4. Add Cal.com event types for the five services. Set each `CAL_EVENT_*` ID, `CAL_API_KEY`, and `SITE_URL`. Confirm the event lengths, Manila timezone, opening hours, lunch, dentist availability, and in-person location in Cal.com.
5. Keep `LIVE_BOOKING_ENABLED=false` until a test booking has verified real availability and email delivery. Then set it to `true`; all five event IDs must be configured. The adapter uses [Cal.com slots](https://cal.com/docs/api-reference/v2/slots/get-available-time-slots-for-an-event-type) version `2024-09-04` and [booking creation](https://cal.com/docs/api-reference/v2/bookings/create-a-booking) version `2026-02-25`.
6. Set `CONTACT_ENABLED=true` only after the contact table is ready. Messages go to Supabase, not email; staff inbox UI/email notifications are future work. Set platform rate limits before enabling a public inbox.

Cal.com is the source of scheduling truth. Supabase appointment history, signed Cal.com webhook syncing, staff queue management, cancellation/rescheduling, password recovery, and email notifications beyond Cal.com's own emails are not implemented in this frontend-focused rebuild. The old prototype remains available as source in `legacy/`.

## Vercel

Import this folder/repository as a **FastAPI** project. `app.py` exports the app, and local static files are mounted under `/static`; Vercel's [FastAPI support](https://vercel.com/docs/frameworks/backend/fastapi) promotes mounted assets to the CDN. No npm build is needed. Add private provider settings in the Vercel environment UI and set `SITE_URL` to the deployment URL. Confirm email redirects after deployment. This project has not been deployed or connected to a Vercel account yet.

## Verification

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
node --check static/main.js
node --check static/booking.js
```

Provider integrations are covered by mocked boundary tests, not live provider verification. Credentials and a selected deployment project are still needed for live testing.

## Design and assets

The supplied screenshot is the visual reference: pale-blue hero, slim sans-serif type, cutout portrait, rounded photography, light cards, open spacing, charcoal footer. Inter regular is a close visual match; the exact reference font cannot be identified from the image alone. Photos are illustrative and must not be presented as real staff portraits or patient testimonials.

Built-in Image Gen produced three project assets: a transparent Filipino dentist portrait, a candid dental consultation, and a pale-blue dental-room photo. Prompt summaries: friendly dentist with folded arms and soft editorial light; dentist explaining care to a seated patient; bright clean chair and orderly tools. All omit text, logos, and watermarks. Icons come from [Phosphor](https://github.com/phosphor-icons/core) and fonts from [Inter](https://rsms.me/inter/), under their respective open licenses.
