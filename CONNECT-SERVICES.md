# Connect Bright Smile to Supabase and Cal.com

Paste credentials into the project-root `.env` file. Hindi kailangang ilagay sa chat. Keep `.env.example` empty: that file is the shareable template.

## Keep Supabase separate

1. Create or choose a Supabase project dedicated to **Bright Smile**. You can keep it under your existing organization; use a separate project for other websites.
2. In that project's **Connect** dialog, copy its Project URL and publishable key. Open **Settings → API Keys** for the full list and to create a separate secret key named `bright-smile-backend`.
3. Put only that project's URL and keys in this folder's `.env`.

| `.env` field | Value to paste | Used for |
|---|---|---|
| `SUPABASE_URL` | Project URL, like `https://your-ref.supabase.co` | This project's API endpoint |
| `SUPABASE_PUBLISHABLE_KEY` | Key beginning `sb_publishable_` | Patient signup/login |
| `SUPABASE_SECRET_KEY` | Key beginning `sb_secret_` | Backend contact-inbox writes; optional until enabling contact |

The Python app loads this folder's `.env` with priority over inherited terminal settings. Vercel deployments exclude `.env` and use the Bright Smile project's environment variables. Do not put these credentials in machine-wide environment variables or another project's files.

**Scope has a limit:** the keys target a Supabase project, not a Windows folder. A person or app holding a copied key can still use it to reach that same Supabase project. A dedicated project, separate backend key, limited sharing, and table access policies provide the separation. Secret keys bypass RLS and must stay on the backend.

No Supabase database password or account-wide personal access token is needed for the current website integration.

## Collect Cal.com values

Create a named API key for Bright Smile in **Cal.com Settings → API Keys**. Depending on the dashboard version, API Keys may be under Developer or Security. Paste the raw key into `CAL_API_KEY`; do not add `Bearer` before it. The Python adapter adds the authorization header.

Create five event types for the clinic:

| Service | Planned duration | `.env` field |
|---|---|---|
| Checkup & consultation | 30 minutes | `CAL_EVENT_CHECKUP` |
| Teeth cleaning | 30 minutes | `CAL_EVENT_CLEANING` |
| Dental fillings | 60 minutes | `CAL_EVENT_FILLING` |
| Tooth extraction | 60 minutes | `CAL_EVENT_EXTRACTION` |
| Follow-up care | 30 minutes | `CAL_EVENT_FOLLOWUP` |

Paste the **numeric event type ID** for each event, not its public booking URL. If the ID is visible in the event editor URL, copy that number. You can also retrieve IDs using Cal.com's event-types API.

In Cal.com, set **Asia/Manila**, the correct dentist/host, the clinic address as an in-person location, and actual availability. The current site assumes Monday–Saturday, 9 AM–5 PM, with lunch from noon–1 PM. Confirm or adjust these before live booking. Connect the dentist's calendar if it should block busy times, and confirm that appointment emails are enabled.

All five IDs and the API key are required by the current live-booking switch. A dedicated API key helps you replace it separately, but it does not by itself limit access to these five event types. We have not configured OAuth or an event-specific permission boundary.

No webhook secret or OAuth client secret is needed for this initial API-key integration. Webhook syncing is future work.

## Fill the file and save

- Paste each value after `=` on the matching line. One setting per line; keep comments as they are.
- Keep `LIVE_BOOKING_ENABLED=false` and `CONTACT_ENABLED=false` during setup.
- For local development, use `SITE_URL=http://127.0.0.1:8000`. In production, use `SITE_URL=https://bsmile.vercel.app`. In Supabase Auth URL Configuration, set the Site URL to `https://bsmile.vercel.app` and allow `https://bsmile.vercel.app/account` for email confirmation redirects.
- This `.env` is a local plain-text configuration file, not an encrypted vault. `.gitignore` excludes it from future Git commits, but manual folder sharing or backups can still include it. Share `.env.example` with teammates; give actual credentials through your password manager or provider dashboard.
- Do not paste real keys into this guide, README, HTML, JavaScript, screenshots, or chat.

Run `python check_services.py` to check the configured connections without showing key values. Restart the Python process after editing `.env`.

Database tables still need the reviewed `supabase-setup.sql`, and live auth needs its Supabase settings confirmed. These local files do not create tables, connect accounts, reserve appointments, or turn on live booking automatically.

## Official references

- [Supabase keys and where to find them](https://supabase.com/docs/guides/getting-started/api-keys)
- [Cal.com API v2 authentication](https://cal.com/docs/api-reference/v2/introduction)
- [Cal.com event type ID and configuration](https://cal.com/docs/api-reference/v2/event-types/get-an-event-type)
