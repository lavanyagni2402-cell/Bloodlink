// BloodLink live alert server (Node.js)
// Uses only Node's built-in modules, so no "npm install" is needed.
//
//   GET  /events   browsers connect here and wait for alerts (Server-Sent Events)
//   POST /notify   Django sends a new alert here as JSON
//
// Run with:  node server.js

const http = require("http");
const EventEmitter = require("events");
const fs = require("fs");

const PORT = 4000;
const alerts = new EventEmitter();   // used to pass an alert to every connected browser
let connectedBrowsers = 0;

const server = http.createServer(function (req, res) {
  // allow the Django website (port 8000) to connect to this server (port 4000)
  res.setHeader("Access-Control-Allow-Origin", "*");

  // ---- a browser connects and keeps the connection open
  if (req.method === "GET" && req.url === "/events") {
    res.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
    });
    connectedBrowsers++;

    // when an alert happens, send it to this browser
    function sendToBrowser(alert) {
      res.write("data: " + JSON.stringify(alert) + "\n\n");
    }
    alerts.on("alert", sendToBrowser);

    // when the browser tab is closed, stop sending to it
    req.on("close", function () {
      connectedBrowsers--;
      alerts.off("alert", sendToBrowser);
    });
    return;
  }

  // ---- Django sends a new alert
  if (req.method === "POST" && req.url === "/notify") {
    let body = "";
    req.on("data", function (chunk) {
      body += chunk;
    });
    req.on("end", function () {
      const alert = JSON.parse(body);
      alerts.emit("alert", alert);   // passes it to every connected browser

      // keep a log of all alerts in a file
      fs.appendFile("alerts.log", body + "\n", function () {});
      console.log(alert.type + " -> sent to " + connectedBrowsers + " browser(s)");

      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ ok: true }));
    });
    return;
  }

  res.writeHead(404);
  res.end("Not found");
});

server.listen(PORT, function () {
  console.log("BloodLink alerts running on http://127.0.0.1:" + PORT);
});
