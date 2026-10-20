// main.js - plain JavaScript used on every page of BloodLink
//   1. getCookie()              reads the CSRF token for AJAX POST requests
//   2. Compatibility chart      on the home page (events + DOM)
//   3. Live numbers             on the home page (fetch + JSON)
//   4. Form validation          on every form with data-validate
//   5. Eligibility preview      while filling the donor form
//   6. Live alerts              from the Node.js server

var GROUPS = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"];

// which groups each donor group can give to (same table as core/models.py)
var CAN_DONATE_TO = {
  "O-": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
  "O+": ["O+", "A+", "B+", "AB+"],
  "A-": ["A-", "A+", "AB-", "AB+"],
  "A+": ["A+", "AB+"],
  "B-": ["B-", "B+", "AB-", "AB+"],
  "B+": ["B+", "AB+"],
  "AB-": ["AB-", "AB+"],
  "AB+": ["AB+"]
};

var NOTES = {
  "O-": "You're the universal donor. Your blood can go to anyone, which is why hospitals run out of it first.",
  "O+": "The most common group in India. You can help every positive patient.",
  "A-": "Rare in India. You can give to A and AB patients, positive or negative.",
  "A+": "You can give to A+ and AB+ patients.",
  "B-": "Rare in India. You can give to B and AB patients, positive or negative.",
  "B+": "Very common in India, so B+ requests come up often.",
  "AB-": "One of the rarest groups. You can give to AB patients.",
  "AB+": "You're the universal recipient: you can receive from every group."
};

// "O-" -> "O−" (proper minus sign for display)
function pretty(group) {
  return group.replace("-", "−");
}

// groups that can GIVE to this group
function canReceiveFrom(group) {
  var result = [];
  for (var i = 0; i < GROUPS.length; i++) {
    var donor = GROUPS[i];
    if (CAN_DONATE_TO[donor].includes(group)) {
      result.push(donor);
    }
  }
  return result;
}


// ---------------------------------------------------------- 1. CSRF token
// Django needs this token on every POST request (this function is from the Django docs)
function getCookie(name) {
  var cookies = document.cookie.split(";");
  for (var i = 0; i < cookies.length; i++) {
    var cookie = cookies[i].trim();
    if (cookie.startsWith(name + "=")) {
      return decodeURIComponent(cookie.substring(name.length + 1));
    }
  }
  return null;
}


// ------------------------------------------------- 2. compatibility chart
function setupCompatibilityChart() {
  var picker = document.getElementById("compat-picker");
  if (!picker) return;   // we are not on the home page

  var giveRow = document.getElementById("compat-give");
  var receiveRow = document.getElementById("compat-receive");
  var note = document.getElementById("compat-note");

  // create one button and two cells for every blood group
  for (var i = 0; i < GROUPS.length; i++) {
    var group = GROUPS[i];

    var button = document.createElement("button");
    button.type = "button";
    button.textContent = pretty(group);
    button.dataset.group = group;
    button.addEventListener("click", function () {
      showGroup(this.dataset.group);
    });
    picker.appendChild(button);

    var giveCell = document.createElement("span");
    giveCell.className = "compat-cell";
    giveCell.textContent = pretty(group);
    giveRow.appendChild(giveCell);

    var receiveCell = document.createElement("span");
    receiveCell.className = "compat-cell";
    receiveCell.textContent = pretty(group);
    receiveRow.appendChild(receiveCell);
  }

  function showGroup(group) {
    var buttons = picker.querySelectorAll("button");
    var giveCells = giveRow.querySelectorAll(".compat-cell");
    var receiveCells = receiveRow.querySelectorAll(".compat-cell");
    var receivers = CAN_DONATE_TO[group];
    var givers = canReceiveFrom(group);

    for (var i = 0; i < GROUPS.length; i++) {
      // highlight the clicked button
      buttons[i].setAttribute("aria-pressed", GROUPS[i] === group);
      // colour the cells this group can give to / receive from
      giveCells[i].classList.toggle("on", receivers.includes(GROUPS[i]));
      receiveCells[i].classList.toggle("on-recv", givers.includes(GROUPS[i]));
    }
    note.textContent = NOTES[group];
  }

  showGroup("O+");   // show O+ when the page opens
}


// ------------------------------------------------------- 3. live numbers
function loadStats() {
  var line = document.getElementById("live-stats");
  var bars = document.getElementById("group-bars");
  if (!line) return;   // we are not on the home page

  fetch("/api/stats/")
    .then(function (response) { return response.json(); })
    .then(function (stats) {
      line.innerHTML = '<span class="live-dot"></span>' +
        stats.available + " donors available now. " +
        stats.open_requests + " open requests, " + stats.critical + " critical. " +
        stats.lives_touched + " donations made through BloodLink.";

      // bar chart of donors per blood group
      var biggest = 1;
      for (var i = 0; i < GROUPS.length; i++) {
        biggest = Math.max(biggest, stats.by_group[GROUPS[i]]);
      }
      var html = "";
      for (var j = 0; j < GROUPS.length; j++) {
        var count = stats.by_group[GROUPS[j]];
        var width = count * 100 / biggest;
        var rare = count <= biggest * 0.15 ? " gbar-scarce" : "";
        html += '<div class="gbar' + rare + '">' +
                '<span class="gbar-label">' + pretty(GROUPS[j]) + '</span>' +
                '<span class="gbar-track"><span class="gbar-fill" style="width:' + width + '%"></span></span>' +
                '<span class="gbar-n">' + count + '</span></div>';
      }
      bars.innerHTML = html;
    })
    .catch(function () {
      line.textContent = "Live numbers are unavailable right now.";
    });
}


// ------------------------------------------------------ 4. form validation
function ageFromDate(value) {
  var birth = new Date(value);
  var today = new Date();
  var age = today.getFullYear() - birth.getFullYear();
  var birthdayNotYet = today.getMonth() < birth.getMonth() ||
    (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate());
  if (birthdayNotYet) age = age - 1;
  return age;
}

function todayString() {
  var today = new Date();
  var month = String(today.getMonth() + 1).padStart(2, "0");
  var day = String(today.getDate()).padStart(2, "0");
  return today.getFullYear() + "-" + month + "-" + day;   // "2026-10-20"
}

// returns an error message for one field, or "" if it is fine
function checkField(input, form) {
  var name = input.name;
  var value = input.value.trim();

  if (input.required && value === "") return "This field is required.";
  if (value === "") return "";

  if (name === "phone" || name === "contact_phone") {
    if (!/^[6-9][0-9]{9}$/.test(value)) return "Enter a 10-digit mobile number starting with 6, 7, 8 or 9.";
  }
  if (name === "email") {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return "Enter an email address like name@example.com.";
  }
  if (name === "password1" && value.length < 6) return "Use at least 6 characters.";
  if (name === "password2" && value !== form.querySelector("[name=password1]").value) {
    return "The two passwords don't match.";
  }
  if (name === "date_of_birth") {
    var age = ageFromDate(value);
    if (age < 18) return "Donors must be at least 18.";
    if (age > 65) return "Donors must be 65 or younger.";
  }
  if (name === "weight_kg" && (value < 30 || value > 250)) return "Enter your weight in kilograms.";
  if (name === "last_donation" && value > todayString()) return "This date can't be in the future.";
  if (name === "needed_by" && value < todayString()) return "This date can't be in the past.";
  if (name === "units_needed" && (value < 1 || value > 20)) return "Enter between 1 and 20 units.";
  return "";
}

function showFieldError(input, form) {
  if (input.type === "checkbox" || input.type === "hidden") return true;
  var message = checkField(input, form);
  var errorBox = form.querySelector('.js-error[data-for="' + input.name + '"]');
  if (errorBox) errorBox.textContent = message;
  if (message) {
    input.classList.add("is-invalid");
  } else {
    input.classList.remove("is-invalid");
  }
  return message === "";
}

function setupValidation() {
  var forms = document.querySelectorAll("form[data-validate]");
  forms.forEach(function (form) {
    var inputs = form.querySelectorAll("input, select, textarea");

    // check a field when the user leaves it
    inputs.forEach(function (input) {
      input.addEventListener("blur", function () { showFieldError(input, form); });
    });

    // check every field before submitting; stop the submit if any is wrong
    form.addEventListener("submit", function (event) {
      var allGood = true;
      inputs.forEach(function (input) {
        if (!showFieldError(input, form)) allGood = false;
      });
      if (!allGood) event.preventDefault();
    });
  });
}


// ----------------------------------------------- 5. eligibility preview
function setupEligibilityPreview() {
  var output = document.getElementById("eligibility-preview");
  if (!output) return;

  var form = output.closest("form");
  var dob = form.querySelector("[name=date_of_birth]");
  var weight = form.querySelector("[name=weight_kg]");
  var last = form.querySelector("[name=last_donation]");

  function update() {
    output.className = "eligibility-preview";
    if (dob.value === "" || weight.value === "") {
      output.textContent = "";
      return;
    }
    var age = ageFromDate(dob.value);
    if (age < 18 || age > 65) {
      output.textContent = "Donors need to be between 18 and 65.";
      output.classList.add("wait");
    } else if (weight.value < 45) {
      output.textContent = "Donors need to weigh at least 45 kg to give blood.";
      output.classList.add("wait");
    } else if (last.value !== "" && (new Date() - new Date(last.value)) / 86400000 < 90) {
      output.textContent = "You need to wait 90 days after your last donation.";
      output.classList.add("wait");
    } else {
      output.textContent = "You can donate today.";
      output.classList.add("ok");
    }
  }

  dob.addEventListener("change", update);
  weight.addEventListener("input", update);
  last.addEventListener("change", update);
  update();
}

// on the "Request blood" form, show which groups can donate
function setupRequestHint() {
  var output = document.getElementById("request-compat");
  if (!output) return;
  var select = output.closest("form").querySelector("[name=blood_group]");
  select.addEventListener("change", function () {
    if (select.value) {
      output.textContent = "Donors who can give: " + canReceiveFrom(select.value).map(pretty).join(", ") + ".";
    }
  });
}

// the "Am I eligible?" page runs on the CGI server (port 8001)
function setupCgiLink() {
  var link = document.getElementById("cgi-link");
  if (link) link.href = "http://" + location.hostname + ":8001/cgi-bin/eligibility.py";
}


// ------------------------------------------------------ 6. live alerts
function showPopup(title, text, link) {
  var popup = document.createElement("div");
  popup.className = "toast alert-toast";
  popup.innerHTML =
    '<div class="toast-header"><span class="me-auto"></span>' +
    '<button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button></div>' +
    '<div class="toast-body"><span></span> <a>View request</a></div>';
  popup.querySelector(".me-auto").textContent = title;
  popup.querySelector(".toast-body span").textContent = text;
  popup.querySelector(".toast-body a").href = link;

  document.getElementById("toasts").appendChild(popup);
  new bootstrap.Toast(popup, { delay: 9000 }).show();   // Bootstrap toast
}

function listenForAlerts() {
  // keep a connection open to the Node.js server (Server-Sent Events)
  var events = new EventSource("http://" + location.hostname + ":4000/events");

  events.onmessage = function (event) {
    var alert = JSON.parse(event.data);
    var d = alert.data;

    if (alert.type === "new_request") {
      showPopup("New request: " + pretty(d.blood_group) + " needed",
        d.units_needed + " unit(s) at " + d.hospital + ", " + d.city + ".", d.url);
    } else if (alert.type === "pledge") {
      showPopup("A donor stepped up",
        d.donor + " pledged for " + d.patient_name + " (" + pretty(d.blood_group) + ").", d.url);
    } else if (alert.type === "fulfilled") {
      showPopup("Request fulfilled", d.patient_name + " has the blood they needed.", d.url);
    }

    loadStats();   // refresh the numbers on the home page
    if (window.loadRequests) window.loadRequests();   // refresh the requests list
  };

  // if Node.js is not running, stop trying (the site works without it)
  events.onerror = function () {
    if (events.readyState === EventSource.CONNECTING) events.close();
  };
}


// run everything when the page has loaded
document.addEventListener("DOMContentLoaded", function () {
  setupCompatibilityChart();
  loadStats();
  setupValidation();
  setupEligibilityPreview();
  setupRequestHint();
  setupCgiLink();
  listenForAlerts();
});
