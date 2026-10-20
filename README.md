# 🩸 BloodLink

**Find a blood donor who can reach the hospital today.**

BloodLink is a blood donor matching web app. A family posts an urgent blood request; BloodLink finds donors whose blood group is compatible and who are medically eligible to donate today, ranks them, and alerts everyone online in real time.

Built as the end-term project for **AIM3140 Web Technologies** at Manipal University Jaipur, using every topic in the course: HTML, CSS, Bootstrap, JavaScript, jQuery/AJAX, AngularJS, Node.js, Python CGI, MySQL, MySQL Connector, JSON and Django.

![BloodLink home page](docs/screenshots/home.png)

---

## Features

- **Post a blood request** with blood group, units, hospital, city and urgency (critical / urgent / planned)
- **Smart donor matching**: finds compatible, available, eligible donors and ranks them with a score out of 100
- **Eligibility rules**: age 18–65, weight ≥ 45 kg, and at least 90 days since the last donation
- **One-tap pledging**: a donor pledges and only then sees the family's phone number
- **Live alerts**: new requests, pledges and fulfilled requests pop up in every open browser, with no refresh needed
- **Live filters** on the requests list (jQuery AJAX) and an **instant donor finder** (AngularJS)
- **Blood compatibility chart**: pick your group to see who you can give to and receive from
- **"Am I eligible?" checker**: a Python CGI page that handles both GET and POST
- **Donor accounts and dashboard** with Django authentication (hashed passwords)
- **Admin panel** to search, filter and verify donors
- **Privacy**: phone numbers are never exposed in the public API

## Screenshots

| A donor pledges, and the family gets a live alert | The family sees pledges and best-matched donors |
|---|---|
| ![Pledging](docs/screenshots/pledge.png) | ![Owner view](docs/screenshots/request-owner.png) |

| Open requests with live AJAX filters | Find donors (AngularJS) |
|---|---|
| ![Open requests](docs/screenshots/requests.png) | ![Find donors](docs/screenshots/find-donors.png) |

| "Am I eligible?" (Python CGI) |
|---|
| ![CGI eligibility checker](docs/screenshots/cgi-eligibility.png) |

---

## Tech stack

| Layer | Technology | Used for |
|---|---|---|
| Frontend | HTML5, CSS3, Bootstrap 5 | Pages, forms, tables, responsive layout |
| | JavaScript (vanilla) | Compatibility chart, form validation, live numbers |
| | jQuery + AJAX | Live request filters, pledge button, availability switch |
| | AngularJS 1.8 | Donor finder with two-way data binding |
| Backend | Django 4.2 | MVT, URL routing, ORM, authentication, admin |
| | Python CGI | Eligibility checker (GET and POST) |
| | Node.js | Live alerts with Server-Sent Events |
| Database | MySQL | All data (via PyMySQL for Django, MySQL Connector for scripts and CGI) |
| Data | JSON | REST-style API, seed data, import/export scripts |

## How it works

```
Browser ──GET/POST──▶ Django (port 8000) ──ORM──▶ MySQL
   ▲                       │
   │ live alerts (SSE)     │ POST /notify (JSON)
   └────── Node.js (port 4000) ◀┘

Browser ──GET/POST──▶ Python CGI server (port 8001) ──MySQL Connector──▶ MySQL
```

1. A family posts a request. Django saves it to MySQL and sends it to the Node.js server.
2. Node.js pushes the alert to every browser that has BloodLink open.
3. Django ranks eligible donors and shows the best matches to the family.
4. A donor pledges using an AJAX POST and gets the family's number.
5. The family marks the donor as donated, which starts that donor's 90-day waiting period.

### Donor ranking

Donors are first filtered by compatible blood group, availability and eligibility, then scored:

| Rule | Points |
|---|---|
| Exact blood group / compatible group | 35 / 15 |
| Same city as the hospital | 30 |
| Verified by an admin | 10 |
| Past donations through BloodLink | 5 each, max 15 |
| Well rested (never donated, or 180+ days ago) / otherwise | 10 / 5 |

Exact matches score higher, so scarce O− blood is saved for patients who need it.

---

## Getting started

### Requirements

- Python 3.9+
- MySQL 8 (or MariaDB 10.5+)
- Node.js 18+

### Setup (one time)

```bash
# 1. Install MySQL and Node (macOS with Homebrew)
brew install mysql node
brew services start mysql

# 2. Create the database and user
mysql -u root < sql/setup.sql

# 3. Python environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 4. Tables and demo data
python manage.py migrate
python manage.py seed

# 5. Make the CGI script executable (macOS/Linux)
chmod +x cgi-bin/eligibility.py
```

### Run

Start each server in its own terminal:

```bash
# Terminal 1: Django website (http://127.0.0.1:8000)
source .venv/bin/activate
python manage.py runserver

# Terminal 2: Node.js live alerts (port 4000)
cd node-alerts
node server.js

# Terminal 3: Python CGI server (port 8001)
source .venv/bin/activate
python -m http.server --cgi 8001
```

Open **http://127.0.0.1:8000**.

### Demo accounts

| Role | Username | Password |
|---|---|---|
| Donor | `demo` | `demo1234` |
| Another donor | `kabirv1` | `donor1234` |
| Admin (`/admin`) | `admin` | `admin123` |

To reset to fresh demo data: `python manage.py seed --reset`

> The demo data (names, phone numbers, hospitals) is fictional and loaded from `data/sample_data.json`.

---

## Project structure

```
├── bloodlink/              Django project settings and root URLs
├── core/                   Main Django app
│   ├── models.py           Donor, BloodRequest, DonorResponse
│   ├── views.py            Pages and JSON API
│   ├── urls.py             URL routing
│   ├── forms.py            Forms and server-side validation
│   ├── matching.py         Donor ranking
│   ├── alerts.py           Sends events to Node.js
│   ├── admin.py            Admin panel
│   ├── tests.py            Automated tests
│   ├── management/commands/seed.py
│   ├── templates/core/     HTML templates
│   └── static/core/        CSS, JavaScript, images, vendor libraries
├── cgi-bin/eligibility.py  Python CGI program
├── node-alerts/server.js   Node.js alert server
├── scripts/                MySQL Connector + JSON scripts
├── sql/                    Database setup and CRUD examples
├── data/                   JSON demo data
└── CODE_GUIDE.md           File-by-file explanation of the code
```

## API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/stats/` | Donor and request counts |
| GET | `/api/requests/?city=&group=&urgency=&status=` | Filtered blood requests |
| GET | `/api/donors/` | Donor list (no phone numbers) |
| POST | `/api/requests/<id>/respond/` | Pledge to donate (login + CSRF token) |
| POST | `/api/availability/` | Toggle donor availability (login + CSRF token) |

## Other commands

```bash
python manage.py test core                                        # run the 8 tests
mysql -u bloodlink -pbloodlink123 bloodlink < sql/crud_demo.sql   # MySQL CRUD demo
python scripts/export_stats.py                                    # MySQL → JSON report
python scripts/import_donors.py                                   # JSON → MySQL import
```

## Security

- CSRF protection on every form and AJAX POST
- Passwords hashed by Django's authentication system
- ORM and parameterised queries (`%s`) to prevent SQL injection
- Output escaped in templates, jQuery (`.text()`) and CGI (`html.escape`)
- Only the person who posted a request can change it (others get HTTP 403)

> **Note:** the secret key and database password in `settings.py` are for local development only. Change them before deploying anywhere public.

## Syllabus coverage (AIM3140)

| Unit | Topics | Where |
|---|---|---|
| Web basics and page design | HTTP, HTML, lists, tables, images, links, forms | All templates; dashboard tables; navbar logo; footer external and email links |
| Styling and client-side | CSS (inline, internal, external), JavaScript, DOM, Bootstrap | `style.css`, `main.js`, CGI page styles |
| Backend with Python | CGI with GET/POST, MySQL CRUD | `cgi-bin/eligibility.py`, `sql/crud_demo.sql` |
| Advanced Python web | MySQL Connector, JSON, jQuery AJAX, Node.js, AngularJS | `scripts/`, `requests.js`, `node-alerts/`, `finder.js` |
| Django | MVT, models, views, templates, admin, ORM, URL routing | `core/` |

---

## Author

**Lavanya Agnihotri**
B.Tech CSE (AI & ML), Manipal University Jaipur
AIM3140 Web Technologies, end-term project
