// Client-side filter. No network calls, no storage.
(function () {
  var input = document.getElementById("q");
  var status = document.getElementById("q-status");
  if (!input) return;
  var cards = Array.prototype.slice.call(document.querySelectorAll(".card"));
  var sections = Array.prototype.slice.call(document.querySelectorAll("main section"));

  input.addEventListener("input", function () {
    var terms = input.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    var shown = 0;
    cards.forEach(function (c) {
      var hay = c.getAttribute("data-search") || "";
      var match = terms.every(function (t) { return hay.indexOf(t) !== -1; });
      c.hidden = !match;
      if (match) shown++;
    });
    sections.forEach(function (s) {
      s.hidden = !s.querySelector(".card:not([hidden])");
    });
    status.textContent = terms.length ? shown + " of " + cards.length + " resources shown" : "";
  });
})();
