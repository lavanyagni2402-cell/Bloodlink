#!/usr/bin/env python3
# "Am I eligible to donate blood?" - a Python CGI program
#
# Start the CGI server from the project folder with:
#     python -m http.server --cgi 8001
# Then open http://127.0.0.1:8001/cgi-bin/eligibility.py
#
# How CGI works: for every request the web server runs this file as a new program.
# It puts the request details in environment variables (REQUEST_METHOD, QUERY_STRING,
# CONTENT_LENGTH), sends POST data on stdin, and whatever we print goes to the browser.

import os
import sys
from datetime import date, datetime
from html import escape
from urllib.parse import parse_qs

import mysql.connector

GROUPS = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
CAN_DONATE_TO = {
    "O-": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
    "O+": ["O+", "A+", "B+", "AB+"],
    "A-": ["A-", "A+", "AB-", "AB+"],
    "A+": ["A+", "AB+"],
    "B-": ["B-", "B+", "AB-", "AB+"],
    "B+": ["B+", "AB+"],
    "AB-": ["AB-", "AB+"],
    "AB+": ["AB+"],
}


# ---------------------------------------------- 1. read the GET or POST data
method = os.environ.get("REQUEST_METHOD", "GET")

if method == "POST":
    length = int(os.environ.get("CONTENT_LENGTH", 0))
    raw_data = sys.stdin.read(length)          # POST data comes in the request body
else:
    raw_data = os.environ.get("QUERY_STRING", "")   # GET data comes after "?" in the URL

form = {}
for key, values in parse_qs(raw_data).items():
    form[key] = values[0]


# ------------------------------------------------------ 2. check the rules
def check_eligibility(form):
    """Returns (can_donate, list_of_messages)."""
    messages = []
    try:
        age = int(form.get("age", ""))
        weight = float(form.get("weight", ""))
    except ValueError:
        return False, ["Please enter your age and weight as numbers."]

    can_donate = True
    if age < 18 or age > 65:
        can_donate = False
        messages.append("Donors must be 18 to 65 years old.")
    if weight < 45:
        can_donate = False
        messages.append("Donors must weigh at least 45 kg.")
    if form.get("last"):
        last = datetime.strptime(form["last"], "%Y-%m-%d").date()
        days = (date.today() - last).days
        if days < 90:
            can_donate = False
            messages.append("Wait 90 days between donations. You can donate again in " + str(90 - days) + " days.")
    if form.get("unwell") == "yes":
        can_donate = False
        messages.append("Wait until you have been well for at least a week.")

    if can_donate:
        messages.append("You meet the basic criteria. The blood bank will do a quick check-up before you donate.")
    return can_donate, messages


# ------------------------------- 3. live numbers from MySQL (MySQL Connector)
def count_requests(group, city):
    conn = mysql.connector.connect(host="127.0.0.1", user="bloodlink",
                                   password="bloodlink123", database="bloodlink")
    cursor = conn.cursor()

    # open requests this group can help with. %s placeholders keep the query safe
    patient_groups = CAN_DONATE_TO[group]
    placeholders = ", ".join(["%s"] * len(patient_groups))
    sql = "SELECT COUNT(*) FROM core_bloodrequest WHERE status = 'open' AND blood_group IN (" + placeholders + ")"
    cursor.execute(sql, patient_groups)
    total = cursor.fetchone()[0]

    in_city = 0
    if city:
        cursor.execute(sql + " AND city = %s", patient_groups + [city])
        in_city = cursor.fetchone()[0]

    conn.close()
    return total, in_city


# ---------------------------------------------------- 4. build the result
result_html = ""
if form:
    group = form.get("group", "")
    city = form.get("city", "").strip().title()
    can_donate, messages = check_eligibility(form)

    if can_donate:
        result_html = '<div class="result good"><h2>You can donate</h2><ul>'
    else:
        result_html = '<div class="result bad"><h2>Not right now</h2><ul>'
    for message in messages:
        result_html += "<li>" + escape(message) + "</li>"
    result_html += "</ul>"

    if group in GROUPS:
        try:
            total, in_city = count_requests(group, city)
            result_html += "<p>Right now there are <strong>" + str(total) + "</strong> open requests that " + group + " blood can help"
            if city:
                result_html += ", <strong>" + str(in_city) + "</strong> of them in " + escape(city)
            result_html += ".</p>"
        except mysql.connector.Error:
            result_html += "<p>(Could not connect to the database for live numbers.)</p>"

    if can_donate:
        result_html += '<p><a class="btn" href="http://127.0.0.1:8000/signup/">Register as a donor on BloodLink</a></p>'
    result_html += "</div>"
    result_html += '<p class="meta">Handled by Python CGI using a ' + method + " request.</p>"

options = ""
for g in GROUPS:
    selected = " selected" if form.get("group") == g else ""
    options += '<option value="' + g + '"' + selected + ">" + g + "</option>"

no_checked = "" if form.get("unwell") == "yes" else "checked"
yes_checked = "checked" if form.get("unwell") == "yes" else ""


# ------------------------------------- 5. build the page and print it
page = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Am I eligible? | BloodLink</title>
<style>
  /* internal CSS */
  body { font-family: Archivo, Arial, sans-serif; background: #F5F7FA; color: #15233B; margin: 0; }
  .wrap { max-width: 620px; margin: 0 auto; padding: 2rem 1rem; }
  h1 { font-size: 2.2rem; margin: .5rem 0; }
  a { color: #B3132F; }
  form { background: #fff; border: 1px solid #D9DFE8; border-radius: 10px; padding: 1.5rem; }
  label { display: block; font-weight: 600; margin: .9rem 0 .3rem; }
  input, select { width: 100%; padding: .55rem .7rem; font: inherit; border: 1px solid #C3CBD8; border-radius: 6px; box-sizing: border-box; }
  .row { display: grid; grid-template-columns: 1fr 1fr; gap: 0 1rem; }
  .radio label { display: inline; font-weight: normal; margin-right: 1rem; }
  .radio input { width: auto; }
  button, .btn { display: inline-block; margin-top: 1.2rem; background: #B3132F; color: #fff; border: 0; border-radius: 6px;
                 padding: .7rem 1.2rem; font: inherit; font-weight: bold; cursor: pointer; text-decoration: none; }
  .result { margin-top: 1.5rem; padding: 1.2rem 1.4rem; border-radius: 10px; border-left: 6px solid; background: #fff; }
  .good { border-color: #1E7457; } .good h2 { color: #1E7457; }
  .bad { border-color: #D98A1C; } .bad h2 { color: #7A4A06; }
  .meta { color: #55627A; font-size: .9rem; }
</style>
</head>
<body>
<div class="wrap">
  <p><a href="http://127.0.0.1:8000/">Back to BloodLink</a></p>
  <h1>Am I eligible to donate blood?</h1>
  <p>A quick check against the basic Indian guidelines.</p>

  <form method="post" action="/cgi-bin/eligibility.py">
    <div class="row">
      <div><label for="age">Age</label><input id="age" name="age" type="number" value="{age}" required></div>
      <div><label for="weight">Weight (kg)</label><input id="weight" name="weight" type="number" value="{weight}" required></div>
      <div><label for="group">Blood group</label><select id="group" name="group" required><option value="">Choose</option>{options}</select></div>
      <div><label for="city">City (optional)</label><input id="city" name="city" value="{city}"></div>
    </div>
    <label for="last">Last donation (leave blank if never)</label>
    <input id="last" name="last" type="date" value="{last}">
    <label>Have you been unwell in the last week?</label>
    <div class="radio">
      <input id="no" type="radio" name="unwell" value="no" {no_checked}><label for="no">No</label>
      <input id="yes" type="radio" name="unwell" value="yes" {yes_checked}><label for="yes">Yes</label>
    </div>
    <button type="submit">Check eligibility</button>
  </form>

  {result}

  <p class="meta">This page also works with GET:
    <a href="?age=21&amp;weight=58&amp;group=O%2B&amp;city=Jaipur">?age=21&amp;weight=58&amp;group=O+&amp;city=Jaipur</a></p>
</div>
</body>
</html>"""

# put the user's values into the page (replace each {placeholder})
page = page.replace("{age}", escape(form.get("age", "")))
page = page.replace("{weight}", escape(form.get("weight", "")))
page = page.replace("{options}", options)
page = page.replace("{city}", escape(form.get("city", "")))
page = page.replace("{last}", escape(form.get("last", "")))
page = page.replace("{no_checked}", no_checked)
page = page.replace("{yes_checked}", yes_checked)
page = page.replace("{result}", result_html)

print("Content-Type: text/html; charset=utf-8")
print()   # a blank line ends the headers
print(page)
