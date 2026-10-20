// Open requests page (jQuery + AJAX)
// When a filter changes, we send a GET request to /api/requests/ and
// rebuild the list from the JSON answer, without reloading the page.

// makes one row of the list for one request
function makeRow(r) {
  var row = $("<a>").addClass("req-row urg-" + r.urgency + " status-" + r.status).attr("href", r.url);

  // .text() is used everywhere so that user input is never treated as HTML
  var tag = $("<span>").addClass("group-tag").text(pretty(r.blood_group));
  var title = $("<span>").addClass("req-title").text(r.patient_name + " needs " + r.units_needed + " unit(s)");
  var meta = $("<span>").addClass("req-meta").text(r.hospital + ", " + r.city + ". Needed by " + r.needed_by);
  var bar = $("<span>").addClass("progress req-progress")
    .append($("<span>").addClass("progress-bar").css("width", r.progress + "%"));
  var main = $("<span>").addClass("req-main").append(title, meta, bar);

  var badge = $("<span>").addClass("urg-badge").text(r.urgency_label);
  var pledged = $("<span>").addClass("req-pledged").text(r.units_pledged + " of " + r.units_needed + " pledged");
  var side = $("<span>").addClass("req-side").append(badge, pledged);

  return row.append(tag, main, side);
}

function loadRequests() {
  var filters = {
    city: $("#f-city").val(),
    group: $("#f-group").val(),
    urgency: $("#f-urgency").val(),
    status: $("#f-status").val()
  };

  $.getJSON("/api/requests/", filters, function (data) {
    $("#req-list").empty();

    if (data.count === 0) {
      $("#req-list").append($("<p>").addClass("empty").text("No requests match these filters."));
    }
    for (var i = 0; i < data.results.length; i++) {
      $("#req-list").append(makeRow(data.results[i]));
    }
    $("#result-count").text(data.count + " request(s)");
  });
}

$(document).ready(function () {
  window.loadRequests = loadRequests;   // so main.js can refresh the list on a live alert

  // reload the list whenever a filter changes
  $("#f-city").on("input", loadRequests);
  $("#f-group, #f-urgency, #f-status").on("change", loadRequests);

  loadRequests();
});
