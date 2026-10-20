# Connects to MySQL with MySQL Connector, runs some queries
# and saves the results in a JSON file.
#
# Run from the project folder:  python scripts/export_stats.py

import json
from datetime import datetime

import mysql.connector

# 1. connect to the database
conn = mysql.connector.connect(
    host="127.0.0.1",
    user="bloodlink",
    password="bloodlink123",
    database="bloodlink",
)
cursor = conn.cursor(dictionary=True)   # each row comes back as a dictionary

# 2. how many donors in each blood group
cursor.execute("SELECT blood_group, COUNT(*) AS donors FROM core_donor GROUP BY blood_group")
donors_by_group = cursor.fetchall()

# 3. open requests in each city (%s is a placeholder, safe from SQL injection)
cursor.execute(
    "SELECT city, COUNT(*) AS open_requests FROM core_bloodrequest WHERE status = %s GROUP BY city",
    ("open",),
)
requests_by_city = cursor.fetchall()

# 4. critical requests that are still open
cursor.execute(
    "SELECT patient_name, blood_group, units_needed, hospital, city "
    "FROM core_bloodrequest WHERE status = 'open' AND urgency = 'critical'"
)
critical = cursor.fetchall()

conn.close()

# 5. save everything as JSON
report = {
    "generated_at": str(datetime.now()),
    "donors_by_group": donors_by_group,
    "open_requests_by_city": requests_by_city,
    "critical_requests": critical,
}
with open("data/stats_export.json", "w") as f:
    json.dump(report, f, indent=2)
print("Saved data/stats_export.json")

# 6. read the JSON file back to show JSON parsing
with open("data/stats_export.json") as f:
    data = json.load(f)

total = 0
for row in data["donors_by_group"]:
    total = total + row["donors"]
print("Total donors:", total)
print("Critical requests open:", len(data["critical_requests"]))
