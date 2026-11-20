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

// Big MAYA shrinks into the nav logo as the page scrolls (styles.css "flies into").
(function () {
  var word = document.querySelector(".hero-word");
  var brand = document.querySelector(".site-head .brand");
  if (!word || !brand) return;
  var mq = window.matchMedia("(min-width: 760px) and (prefers-reduced-motion: no-preference)");
  var root = document.documentElement;


  function reset() {
    root.classList.remove("js-fly");
    ["--fly-x", "--fly-y", "--fly-s", "--brand-on", "--word-on"].forEach(function (k) {
      word.style.removeProperty(k); brand.style.removeProperty(k);
    });
  }

  function update() {

    if (!mq.matches) { reset(); return; }
    root.classList.add("js-fly");
    // Natural position of the word, without the current transform.
    word.style.setProperty("--fly-x", "0px");
    word.style.setProperty("--fly-y", "0px");
    word.style.setProperty("--fly-s", "1");
    var w = word.getBoundingClientRect();
    var b = brand.getBoundingClientRect();
    // Finish within about half the word height of scroll so the flight over the nav is brief.
    var dist = Math.max(120, w.height * 0.55);
    var p = Math.min(1, Math.max(0, window.scrollY / dist));
    var e = 1 - (1 - p) * (1 - p);
    // Scale by font size (the boxes differ: line-height 0.8 vs normal) and meet at the
    // vertical centre, so the swap to the logo does not jump.
    var end = parseFloat(getComputedStyle(brand).fontSize) / parseFloat(getComputedStyle(word).fontSize);
    var s = 1 + e * (end - 1);
    var dy = (b.top + b.height / 2) - (w.top + w.height * end / 2);
    word.style.setProperty("--fly-x", e * (b.left - w.left) + "px");
    word.style.setProperty("--fly-y", e * dy + "px");
    word.style.setProperty("--fly-s", String(s));
    var done = p >= 0.999;
    brand.style.setProperty("--brand-on", done ? "1" : "0");
    word.style.setProperty("--word-on", done ? "0" : "1");
  }

  // Direct on scroll, not via requestAnimationFrame: two rect reads per event, and rAF
  // stalls in background tabs, which left the word half-shrunk there.
  window.addEventListener("scroll", update, { passive: true });
  window.addEventListener("resize", update);
  if (mq.addEventListener) mq.addEventListener("change", update);
  update();
})();
