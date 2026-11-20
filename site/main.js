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
