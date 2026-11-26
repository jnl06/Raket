/* Jobs page: re-run the search when a filter or the sort order changes
   (the Search button still works too), and start with filters collapsed on phones. */
(function () {
  "use strict";

  var form = document.getElementById("job-filters");
  if (!form) return;

  form.addEventListener("change", function (e) {
    if (e.target.name === "q") return;
    form.classList.add("is-loading");
    form.submit();
  });

  var box = form.querySelector(".filters__box");
  if (box && window.matchMedia("(max-width: 860px)").matches) {
    box.open = !!form.querySelector(".chip--navy");
  }
})();
