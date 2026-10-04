# Bright Smile Dental Clinic

[Visit the website](https://bsmile.vercel.app/)

Hi! I'm a student learning web development, and Bright Smile is my first development project and my first repository on GitHub. This project marks my first step into making commits, organizing my code, and sharing what I'm learning.

I wanted to build something with a clear purpose: a dental clinic website where visitors can learn about the clinic, explore its services, and book an appointment. It's a learning project that I can keep improving as I gain more experience.

## About the project

Bright Smile brings clinic information and appointment scheduling together in one website. It includes:

- Home, About Us, Services, and Contact Us pages.
- An appointment flow for choosing a dental service, date, and time.
- Patient signup, login, and appointment history when Supabase is configured.
- A clinic admin page for viewing bookings and contact messages.
- A responsive layout for phones and computers.
- Clearly labeled sample accounts and records for demonstrations.

Booking runs in preview mode when live scheduling is not configured. Preview appointments do not reserve real slots. Live scheduling uses Cal.com, while Supabase handles accounts and database records.

## Tools used

- **Python and FastAPI** for the server and form handling.
- **HTML and Jinja2** for the pages and shared templates.
- **CSS** for the layout, colors, and responsive design.
- **JavaScript** for navigation, forms, and the booking calendar.
- **Supabase** for authentication and the database.
- **Cal.com** for appointment scheduling.
- **Vercel** as the hosting platform.

## Project structure

| File or folder | Purpose |
|---|---|
| `app.py` | Website routes and service integrations |
| `templates/` | HTML page templates |
| `static/` | Styles, scripts, images, fonts, and icons |
| `supabase-setup.sql` | Database tables and access rules |
| `.env.example` | Blank template for local settings |
| `tests/` | Checks for website behavior and deployment settings |
| `legacy/` | My original prototype |

## Run locally

Use Python 3.12 or newer. From the project folder, run these commands in PowerShell:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.venv/Scripts/python.exe -m uvicorn app:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. Keep private keys in `.env` and out of GitHub. See [CONNECT-SERVICES.md](CONNECT-SERVICES.md) for the Supabase and Cal.com settings.

To run the existing checks:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

## What I'm learning

Through this project, I'm learning how to connect pages to a Python server, make layouts work on different screen sizes, validate forms, and use external services. I'm also practicing Git commits and learning how to maintain a repository on GitHub.

There is still room to improve the project, especially password recovery, appointment cancellation and rescheduling, and notifications. I plan to work on these as I learn more.

## Image disclaimer and credits

The images used in this project were generated using a free ChatGPT account. They are for demonstration purposes and do not represent actual clinic staff, patients, or facilities.

The website uses [Inter](https://rsms.me/inter/) fonts and [Phosphor](https://github.com/phosphor-icons/core) icons. Their license files are included in `static/fonts/` and `static/icons/`.
