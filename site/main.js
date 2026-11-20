// Highlights the line Maya is speaking in each transcript, and lets only one clip play at a time.
(function () {
  var HOLD_S = 2.5;
  var videos = Array.prototype.slice.call(document.querySelectorAll("video"));

  videos.forEach(function (video) {
    var list = document.querySelector('.lines[data-video="' + video.id + '"]');
    var items = list ? Array.prototype.slice.call(list.querySelectorAll("li[data-t]")) : [];

    function mark() {
      var t = video.currentTime;
      items.forEach(function (li) {
        var start = parseFloat(li.getAttribute("data-t"));
        li.classList.toggle("now", t >= start && t < start + HOLD_S);
      });
    }

    video.addEventListener("timeupdate", mark);
    video.addEventListener("seeked", mark);
    video.addEventListener("play", function () {
      videos.forEach(function (other) {
        if (other !== video && !other.paused) other.pause();
      });
    });
  });
})();

// The ticker only moves when the reader allows motion, and the button stops it.
(function () {
  var ticker = document.querySelector(".ticker");
  var button = ticker && ticker.querySelector(".ticker-toggle");
  if (!ticker || !button || !window.matchMedia) return;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)");

  function apply() {
    var moving = !reduce.matches;
    ticker.classList.toggle("is-moving", moving);
    button.hidden = !moving;
  }

  button.addEventListener("click", function () {
    var paused = ticker.classList.toggle("is-paused");
    button.textContent = paused ? "Play scrolling" : "Pause scrolling";
  });

  if (reduce.addEventListener) reduce.addEventListener("change", apply);
  else if (reduce.addListener) reduce.addListener(apply);
  apply();
})();
