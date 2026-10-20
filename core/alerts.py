# Sends a message to our Node.js server (node-alerts/server.js).
# Node then passes it to every open browser, which shows a pop-up.

import json
import urllib.request

from django.conf import settings


def send_alert(alert_type, data):
    body = json.dumps({"type": alert_type, "data": data}).encode("utf-8")
    url = settings.NODE_ALERTS_URL + "/notify"
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        # Node.js is not running. That's okay, the website still works without live alerts.
        pass
