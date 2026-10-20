# Reads new donors from a JSON file and inserts them into MySQL with MySQL Connector.
# For example, sign-ups collected at a blood donation camp.
#
# Run from the project folder:  python scripts/import_donors.py

import json

import mysql.connector

# 1. read the JSON file into a Python list of dictionaries
with open("data/new_donors.json") as f:
    new_donors = json.load(f)

# 2. connect to MySQL
conn = mysql.connector.connect(
    host="127.0.0.1",
    user="bloodlink",
    password="bloodlink123",
    database="bloodlink",
)
cursor = conn.cursor()

added = 0
for d in new_donors:
    # skip the donor if the username already exists
    cursor.execute("SELECT id FROM auth_user WHERE username = %s", (d["username"],))
    if cursor.fetchone():
        print("Skipping", d["username"], "- already exists")
        continue

    # every donor needs a login account first (password "!" means they can't log in yet)
    cursor.execute(
        "INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, "
        "is_staff, is_active, date_joined) VALUES ('!', 0, %s, '', '', %s, 0, 1, NOW())",
        (d["username"], d.get("email", "")),
    )
    user_id = cursor.lastrowid   # id of the row we just inserted

    # then the donor details, linked to that account
    cursor.execute(
        "INSERT INTO core_donor (user_id, full_name, blood_group, gender, date_of_birth, weight_kg, "
        "phone, city, last_donation, is_available, is_verified, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, 0, NOW())",
        (user_id, d["full_name"], d["blood_group"], d["gender"], d["date_of_birth"],
         d["weight_kg"], d["phone"], d["city"].title(), d.get("last_donation")),
    )
    added = added + 1

conn.commit()   # save all the changes
conn.close()
print("Imported", added, "donor(s)")
