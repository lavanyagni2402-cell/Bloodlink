# BloodLink

A blood donor matching website. A family posts a blood request, BloodLink finds donors with a
compatible blood group who are eligible to donate today, ranks them, and alerts everyone online.

AIM3140 Web Technologies end-term project.

Uses: HTML, CSS, Bootstrap, JavaScript, jQuery + AJAX, AngularJS, Python CGI (GET/POST),
MySQL, MySQL Connector, JSON, Node.js and Django.

See **CODE_GUIDE.md** for what every file does.

---

## One-time setup (Mac)

```
brew install mysql node
brew services start mysql
mysql -u root < sql/setup.sql

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
chmod +x cgi-bin/eligibility.py
python manage.py migrate
python manage.py seed
```

## Running it (every time)

Open three terminals in VS Code (the **+** button in the terminal panel):

| Terminal | Commands | What it is |
|---|---|---|
| 1 | `source .venv/bin/activate` then `python manage.py runserver` | Django website, port 8000 |
| 2 | `cd node-alerts` then `node server.js` | Node.js live alerts, port 4000 |
| 3 | `source .venv/bin/activate` then `python -m http.server --cgi 8001` | CGI server for "Am I eligible?", port 8001 |

Open **http://127.0.0.1:8000**

| Login | Username | Password |
|---|---|---|
| Donor | `demo` | `demo1234` |
| Another donor | `kabirv1` | `donor1234` |
| Admin (`/admin`) | `admin` | `admin123` |

Fresh demo data: `python manage.py seed --reset`

## Other commands

```
python manage.py test core                            # 8 automated tests
mysql -u bloodlink -pbloodlink123 bloodlink < sql/crud_demo.sql   # MySQL CRUD
python scripts/export_stats.py                        # MySQL Connector -> JSON
python scripts/import_donors.py                       # JSON -> MySQL
```
