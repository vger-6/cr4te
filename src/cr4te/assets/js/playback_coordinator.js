(function () {
  let activeMedia = null;

  function isMediaElement(target) {
    return target instanceof HTMLMediaElement;
  }

  document.addEventListener("play", event => {
    const media = event.target;
    if (!isMediaElement(media)) return;

    if (activeMedia && activeMedia !== media) {
      activeMedia.pause();
    }

    activeMedia = media;
  }, true);

  function clearActiveMedia(event) {
    if (event.target === activeMedia) {
      activeMedia = null;
    }
  }

  document.addEventListener("pause", clearActiveMedia, true);
  document.addEventListener("ended", clearActiveMedia, true);
})();
