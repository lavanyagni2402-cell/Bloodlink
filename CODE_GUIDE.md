# BloodLink code guide

What every file does, the important parts inside it, and how to explain it if your faculty asks.
Open it side by side with the code in VS Code (right-click this file, then **Open Preview**).

---

## The big picture

```
Browser  ──GET/POST──▶  Django (port 8000)  ──SQL──▶  MySQL database
   ▲                        │
   │ live alerts            │ POST /notify
   └──── Node.js (port 4000) ◀┘

Browser  ──GET/POST──▶  CGI server (port 8001) ──runs──▶ cgi-bin/eligibility.py ──▶ MySQL
```

**What happens when you open a page**, for example `/requests/12/`:

1. The browser sends a **GET** request to Django.
2. `bloodlink/urls.py` sends anything that isn't `/admin/` to `core/urls.py`.
3. `core/urls.py` matches `requests/<int:pk>/` and calls the view `request_detail` with `pk=12`.
4. The view in `core/views.py` gets the data from MySQL using the **ORM** (models).
5. The view passes the data to a **template** (`request_detail.html`), which becomes HTML.
6. Django sends the HTML back to the browser.

This is Django's **MVT** pattern: **M**odel (data), **V**iew (logic), **T**emplate (HTML).

---

## Folder layout

```
bloodlink 2/
├── manage.py              starts Django commands (runserver, migrate, seed, test)
├── requirements.txt       Python packages to install
├── bloodlink/             project settings
│   ├── settings.py
│   └── urls.py
├── core/                  the main app
│   ├── models.py          database tables
│   ├── views.py           page logic + JSON API
│   ├── urls.py            which URL goes to which view
│   ├── forms.py           forms + server-side validation
│   ├── matching.py        donor ranking
│   ├── alerts.py          sends alerts to Node.js
│   ├── admin.py           admin panel
│   ├── tests.py           automated tests
│   ├── management/commands/seed.py   loads demo data
│   ├── templates/core/    HTML pages
│   └── static/core/       CSS, JavaScript, Bootstrap, jQuery, AngularJS
├── cgi-bin/eligibility.py CGI program
├── node-alerts/server.js  Node.js alert server
├── scripts/               MySQL Connector + JSON scripts
├── sql/                   SQL files
└── data/                  JSON files with demo data
```

---

## Backend: Django

### `bloodlink/settings.py`: project settings

- `pymysql.install_as_MySQLdb()`: lets Django talk to MySQL using the PyMySQL driver.
- `INSTALLED_APPS`: the apps Django loads. `core` is ours; `django.contrib.admin` and `django.contrib.auth` give the admin panel and login system.
- `DATABASES`: connects to the MySQL database `bloodlink` with user `bloodlink`.
- `MIDDLEWARE`: includes `CsrfViewMiddleware`, which checks the CSRF token on every POST.
- `LOGIN_URL`, `LOGIN_REDIRECT_URL`: where to send users for login and after logging in.

**Say:** "This file connects the project to MySQL and turns on the admin, authentication and CSRF protection."

### `bloodlink/urls.py` and `core/urls.py`: URL routing

- `path("admin/", admin.site.urls)`: the admin panel.
- `path("", include("core.urls"))`: every other URL is handled by `core/urls.py`.
- In `core/urls.py`, each `path()` connects a URL to a view, e.g. `path("requests/<int:pk>/", views.request_detail)`. The `<int:pk>` part captures the request's ID from the URL.
- Login and logout use Django's built-in `LoginView` and `LogoutView`.
- The `api/...` URLs return JSON, not HTML. JavaScript uses them.

**Say:** "URL routing decides which Python function runs for each address."

### `core/models.py`: database tables

| Model | Table in MySQL | What it stores |
|---|---|---|
| `User` (built into Django) | `auth_user` | username, email, hashed password |
| `Donor` | `core_donor` | blood group, city, date of birth, weight, phone, last donation |
| `BloodRequest` | `core_bloodrequest` | patient, blood group, units, hospital, city, urgency, status |
| `DonorResponse` | `core_donorresponse` | which donor pledged for which request, and the status |

Key parts:
- `CAN_DONATE_TO`: dictionary saying which groups each blood group can give to.
- `compatible_donor_groups(patient_group)`: loops through the dictionary to find who can give to a patient.
- `OneToOneField(User)`: each user has one donor profile.
- `ForeignKey(BloodRequest)`: one request has many responses.
- `UniqueConstraint`: a donor can respond to a request only once.
- `@property is_eligible`: returns False if age is not 18–65, weight is under 45 kg, or the last donation was less than 90 days ago.
- `to_dict()`: turns a request into a dictionary so it can be sent as JSON.

**Say:** "Each class is a table. Django creates the tables for me with `migrate`, so I don't write CREATE TABLE by hand."

**If asked "what is the ORM?":** "Object Relational Mapper. I write `Donor.objects.filter(blood_group="O+")` in Python and Django turns it into `SELECT * FROM core_donor WHERE blood_group = 'O+'`. It also protects against SQL injection."

### `core/forms.py`: forms and server-side validation

- `SignupForm` extends Django's `UserCreationForm`, which handles username and password and hashes the password.
- `DonorForm` and `BloodRequestForm` are `ModelForm`s: Django builds the form fields from the model automatically.
- `clean_date_of_birth()`, `clean_needed_by()`, etc. are extra checks. Django calls `clean_<fieldname>()` automatically, and `ValidationError` shows the message under the field.
- `add_bootstrap(form)` adds Bootstrap's CSS classes to every field.

**Say:** "JavaScript checks the form in the browser for speed, but these checks run on the server too, so nobody can skip them."

### `core/views.py`: the logic

**Page views** (return HTML):

| View | What it does | Method |
|---|---|---|
| `home` | 3 most urgent open requests | GET |
| `signup` | creates the user + donor profile, logs them in | GET shows the form, POST saves it |
| `dashboard` | your profile, requests you can help, your pledges | GET, needs login |
| `request_create` | saves a new request, sends a live alert | GET / POST, needs login |
| `request_detail` | one request; the owner also sees the ranked donors | GET |
| `request_set_status` | mark fulfilled / closed (owner only, otherwise 403) | POST only |
| `response_set_status` | mark a donor as donated; sets their last donation to today | POST only |

**JSON API views** (return data for JavaScript):

| View | URL | Used by |
|---|---|---|
| `api_stats` | `/api/stats/` | home page numbers (fetch) |
| `api_requests` | `/api/requests/?city=&group=` | open requests page (jQuery) |
| `api_donors` | `/api/donors/` | find donors page (AngularJS). No phone numbers |
| `api_respond` | `/api/requests/<id>/respond/` | "I can donate" button (jQuery POST) |
| `api_toggle_availability` | `/api/availability/` | dashboard switch (jQuery POST) |

Things to point out:
- `request.method == "POST"`: this is how a view tells GET (show the form) from POST (save it).
- `request.GET.get("city")`: reads GET parameters from the URL.
- `@login_required`: you must be logged in, otherwise Django sends you to the login page.
- `@require_POST` / `@require_GET`: only that method is allowed.
- `JsonResponse(...)`: sends a Python dictionary back as JSON.
- `HttpResponseForbidden`: the 403 error when someone tries to change another person's request.
- `form.save(commit=False)`: create the object, set extra fields like `posted_by`, then `save()`.

### `core/matching.py`: donor ranking

1. **Filter with the database:** `Donor.objects.filter(blood_group__in=..., is_available=True)`
2. **Skip** donors who already responded or aren't eligible today.
3. **Score** each donor with `score_donor()`:

| Rule | Points |
|---|---|
| Exact blood group / compatible but different | 35 / 15 |
| Same city as the hospital | 30 |
| Verified by admin | 10 |
| Past donations | 5 each, max 15 |
| Never donated or 180+ days ago / otherwise | 10 / 5 |

4. **Sort** highest score first.

**Say:** "Exact matches get more points than compatible ones, so rare O− blood is saved for the patients who really need it."

### `core/alerts.py`: talking to Node.js

`send_alert()` converts the alert to JSON and sends a POST request to `http://127.0.0.1:4000/notify` using Python's `urllib`. If Node isn't running, the `try/except` ignores the error, so the website keeps working.

### `core/admin.py`: admin panel

- `list_display`: columns shown in the list.
- `list_filter`: the filter sidebar (blood group, city…).
- `search_fields`: the search box.
- `verify_donors`: a custom action, "Mark selected donors as verified".

### `core/management/commands/seed.py`: demo data

`python manage.py seed` reads `data/sample_data.json` with `json.load()` and creates donors and requests using the ORM. `--reset` deletes the old data first.

### `core/tests.py`: automated tests

Eight tests check blood group compatibility, the ranking order, pledging, the 90-day rule, that non-owners get 403, and that the donor API never contains phone numbers. Run with `python manage.py test core`.

---

## Frontend

### `core/templates/core/`: HTML pages (Django templates)

- `base.html`: the layout every page shares: navbar, messages, footer, and the `<script>` tags. Other pages start with `{% extends "core/base.html" %}` and fill in `{% block content %}`.
- `{% url 'request_detail' r.id %}`: builds a link from a URL name.
- `{% if %}`, `{% for %}`: template logic.
- `{% csrf_token %}`: hidden security token in every POST form.
- `_field.html`: a small reusable piece that draws one form field with its label and error.
- `request_detail.html`: shows a different box depending on who is viewing: the owner, a logged-out user, a donor who can give, a donor who isn't eligible… It also has the jQuery code for the "I can donate" button.
- `find_donors.html`: the AngularJS page. It's wrapped in `{% verbatim %}` because Django and Angular both use `{{ }}`.

HTML features used (lectures 4–9):

| Topic | Where |
|---|---|
| Headings, paragraphs, `<strong>`, comments | every page |
| Lists | `<ol>` steps on the home page, `<ul>` navbar, `<dl>` request details |
| **Tables** | "Donors who pledged" on a request page; "Your pledges" and "Your requests" on the dashboard (`<table>`, `<thead>`, `<tr>`, `<th>`, `<td>`) |
| **Images** | `<img>` logo in the navbar (`static/core/img/logo.svg`), also used as the browser tab icon |
| Internal links | navbar links built with `{% url %}` |
| **External link** | footer "World Health Organization" (`target="_blank"` opens a new tab) |
| **Email link** | footer "Email us" (`mailto:`) |
| Phone links | `tel:` links to call a family or donor |
| Forms and inputs | `text`, `email`, `password`, `date`, `number`, `select`, `checkbox`, `radio` (CGI page), `textarea` |

### `core/static/core/css/style.css`: CSS

- **External CSS**: this file, linked in `base.html`.
- **Internal CSS**: the `<style>` block inside `cgi-bin/eligibility.py`.
- **Inline CSS**: `style="width: 50%"` on the progress bars.
- Uses CSS variables (`--blood: #B3132F`), class selectors, the box model (border, padding, margin), Flexbox, CSS Grid and a media query for phones.
- Bootstrap 5 (`static/core/vendor/`) gives the navbar, grid (`row`, `col-lg-6`), form styles, alerts, toasts and progress bars.

### `core/static/core/js/main.js`: plain JavaScript (every page)

| Function | What it does | Topic |
|---|---|---|
| `getCookie()` | reads the CSRF token for AJAX POSTs (from the Django docs) | cookies |
| `setupCompatibilityChart()` | creates the buttons with `createElement`, adds click listeners, toggles classes | DOM + events |
| `loadStats()` | `fetch("/api/stats/")` then `.json()`, writes the numbers and bar chart | fetch + JSON |
| `checkField()` / `setupValidation()` | checks each field on `blur`; on `submit`, `event.preventDefault()` stops the form if anything is wrong | form validation |
| `setupEligibilityPreview()` | shows "You can donate today" while you type | events |
| `listenForAlerts()` | `new EventSource(...)` keeps a connection to Node.js open; `showPopup()` shows a Bootstrap toast | live alerts |

**Say:** "When I click a blood group, the click event calls `showGroup()`, which adds or removes the `on` class on each cell. That's DOM manipulation."

### `core/static/core/js/requests.js`: jQuery + AJAX

- `loadRequests()` collects the filter values and calls `$.getJSON("/api/requests/", filters, ...)`. That's a **GET** request with the filters in the URL.
- The callback empties the list (`$("#req-list").empty()`) and adds one row per result with `makeRow()`.
- `.on("change", loadRequests)` reloads whenever a filter changes, so the page never reloads.
- `.text()` is used instead of `.html()`, so a patient name can never inject HTML (prevents XSS).

The **POST** examples are in the templates: `$.ajax({ method: "POST", ... })` in `request_detail.html` (pledge) and `dashboard.html` (availability switch). Both send `X-CSRFToken`.

### `core/static/core/js/finder.js`: AngularJS

- `angular.module("finderApp", [])`: creates the app; `ng-app="finderApp"` in the HTML starts it.
- `app.controller("FinderCtrl", function ($http) {...})`: the controller; `ng-controller="FinderCtrl as vm"` connects it.
- `$http.get("/api/donors/")`: loads the donors as JSON.
- `vm.results()`: filters and sorts the list. Angular re-runs it whenever a bound value changes.

In `find_donors.html`:
- `ng-model="vm.city"`: **two-way binding**: typing updates `vm.city`, and `vm.city` updates the box.
- `ng-repeat="d in vm.results()"`: draws one card per donor.
- `ng-options`: fills the blood group dropdown.
- `ng-if`, `ng-class`: show/hide text, grey out donors who can't give.
- `{{ d.next_eligible | date:'d MMM' }}`: Angular's built-in date filter.

---

## Node.js: `node-alerts/server.js`

Uses only built-in modules: `http` (the server), `events` (`EventEmitter`) and `fs` (writes `alerts.log`).

1. Every browser opens `GET /events` and the connection **stays open** (`Content-Type: text/event-stream`). That's Server-Sent Events.
2. For each browser, `alerts.on("alert", sendToBrowser)` registers a listener.
3. When Django posts to `POST /notify`, the server reads the body, then `alerts.emit("alert", alert)` sends it to **every** listener, which means every open browser.
4. When a tab closes, `req.on("close")` removes its listener.

**Say:** "Django can't push data to the browser by itself, so Node keeps a connection open with each browser and forwards each event."

---

## CGI: `cgi-bin/eligibility.py`

Started with `python -m http.server --cgi 8001`, Python's built-in web server with CGI support.

1. For every request, the server **runs this file as a new program**.
2. It passes the request in **environment variables**: `REQUEST_METHOD`, `QUERY_STRING`, `CONTENT_LENGTH`.
3. **GET:** data is read from `os.environ["QUERY_STRING"]`, the part after `?` in the URL.
   **POST:** data is read from `sys.stdin`, the request body.
4. `parse_qs()` turns `age=21&weight=58` into a dictionary.
5. `check_eligibility()` applies the rules.
6. `count_requests()` uses **MySQL Connector** to count open requests. The `%s` placeholders keep the query safe from SQL injection.
7. It prints `Content-Type: text/html`, a **blank line**, then the HTML. Everything printed goes to the browser.

**Say:** "Fill in the form and it's a POST request; click the link at the bottom and it's a GET request. The page says which one it received."

---

## MySQL, MySQL Connector, JSON

- `sql/setup.sql`: creates the database and the `bloodlink` user.
- `sql/crud_demo.sql`: **C**reate (`INSERT`), **R**ead (`SELECT` with `GROUP BY` and `JOIN`), **U**pdate (`UPDATE`), **D**elete (`DELETE`) on the real tables.
- `scripts/export_stats.py`: `mysql.connector.connect(...)` → `cursor.execute(...)` → `fetchall()` → `json.dump()` to a file, then `json.load()` to read it back.
- `scripts/import_donors.py`: `json.load()` reads new donors, `INSERT`s them, and `conn.commit()` saves.
- `data/sample_data.json`: demo data in JSON.

---

## Quick answers

| Question | Answer |
|---|---|
| GET vs POST? | GET reads data and puts it in the URL. POST changes data and sends it in the body. All my saves use POST + CSRF. |
| What is CSRF? | A trick where another site submits a form as you. Django's hidden token stops it. |
| How is the password stored? | Hashed by Django (PBKDF2), never as plain text. |
| What's AJAX? | Sending a request from JavaScript and updating part of the page without reloading. |
| Why Node.js for alerts? | It handles many open connections at once, which is ideal for live updates. |
| Why one CGI page? | To show how CGI works. Django is better for a full site because CGI starts a new process for every request. |
| What if Node is off? | The site still works; only the live pop-ups stop. |
| How do you stop SQL injection? | The ORM, and `%s` placeholders in MySQL Connector. |
| How do you stop XSS? | Django escapes templates; jQuery uses `.text()`; CGI uses `html.escape()`. |
