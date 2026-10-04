# Bright Smile project instructions

Run the local server yourself and open the preview in the browser available to this environment. Do not give the user server-start instructions when you can run it.

Before making substantial visual changes, use the Product Design plugin's `get-context` skill when the visual source is unclear or no longer matches the current goal. When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

Use Python with ordinary HTML templates, CSS, and small JavaScript files. Do not use React, Vite, or a Node build pipeline. The user explicitly requested this simpler structure.

Code comments must be about 70% English and 30% Tagalog (Taglish), with fifth-grade explanations for important sections and actions.

Match the supplied healthcare reference: pale blue, white, charcoal, light sans-serif headings, rounded photographs, and a genuinely transparent doctor cutout. Public pages are Home, About Us, Services, Contact Us, and Book an Appointment. Keep the original prototype in `legacy/`.

Supabase owns database and authentication; Cal.com owns live scheduling. Until credentials are supplied, label appointment previews clearly and do not store patient passwords or claim real reservations. Hosting target is Vercel. Keep private keys on the Python server.

Use a dedicated Supabase project for this website. Credentials belong in this project's ignored `.env`; do not ask the user to paste secrets into chat, print their values, or reuse them in another project. Any Supabase MCP connection must use the selected project's `project_ref`, not account-wide access. See `CONNECT-SERVICES.md` for the setup checklist.

The user wants one short `.env` intake file, not lengthy setup documents or replies. Keep responses brief and direct. Use the separate GitHub, Supabase, Vercel, and Cal.com accounts identified by the `PROJECT_*` fields; these are setup targets, not login credentials. Do not reuse existing account connections or change global account settings for other projects. Account authorization must still be completed for the specified accounts.

Prefer project-local MCP configuration in `.codex/config.toml` when setting up new connections. Confirm exact account and resource targets before enabling. Configuration scope is not the same as provider permission scope: use Supabase `project_ref`, selected-repository GitHub permissions, and a dedicated Vercel/Cal.com account or provider-supported restricted access. Do not promise that an account-wide MCP token is limited to this folder. Fetch only credentials the connected provider actually exposes; do not claim MCP automatically supplies every secret key.
