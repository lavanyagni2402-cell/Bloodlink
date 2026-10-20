// Find donors page (AngularJS)
// The HTML for this page is in templates/core/find_donors.html

var app = angular.module("finderApp", []);

app.controller("FinderCtrl", function ($http) {
  var vm = this;   // "vm" = view model, used as vm.something in the HTML

  vm.groups = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"];
  vm.donors = [];
  vm.cities = [];
  vm.patientGroup = null;
  vm.city = "";
  vm.readyOnly = false;
  vm.sortKey = "best";
  vm.loading = true;
  vm.error = "";

  // "O-" -> "O−"
  vm.label = function (group) {
    return group ? group.replace("-", "−") : "";
  };

  // load all donors once from our JSON API
  $http.get("/api/donors/").then(function (response) {
    vm.donors = response.data.results;
    vm.donors.forEach(function (d) {
      d.label = vm.label(d.blood_group);
      if (!vm.cities.includes(d.city)) vm.cities.push(d.city);
    });
    vm.cities.sort();
    vm.loading = false;
  }, function () {
    vm.error = "Couldn't load donors. Check that the server is running.";
    vm.loading = false;
  });

  // Angular calls this again every time a filter changes (two-way binding)
  vm.results = function () {
    var city = vm.city.toLowerCase();

    var list = vm.donors.filter(function (d) {
      if (vm.patientGroup && !d.can_donate_to.includes(vm.patientGroup)) return false;
      if (city && !d.city.toLowerCase().includes(city)) return false;
      if (vm.readyOnly && !(d.eligible && d.available)) return false;
      return true;
    });

    if (vm.sortKey === "name") {
      list.sort(function (a, b) { return a.name.localeCompare(b.name); });
    } else if (vm.sortKey === "donations") {
      list.sort(function (a, b) { return b.donations - a.donations; });
    } else {
      // "best match": donors who can give today first, then exact group, then verified
      list.sort(function (a, b) { return points(b) - points(a); });
    }
    return list;
  };

  function points(d) {
    var p = 0;
    if (d.eligible && d.available) p += 100;
    if (d.blood_group === vm.patientGroup) p += 30;
    if (d.verified) p += 10;
    return p + d.donations;
  }
});
