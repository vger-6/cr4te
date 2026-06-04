(function () {
  const cr4te = window.cr4te = window.cr4te || {};
  cr4te.video = cr4te.video || {};

  const CONTROL_HIDE_DELAY = 2000;
  let isVideoSeeking = false;

  function updatePlayPauseButton(wrapper, isPlaying) {
    const button = wrapper.querySelector("[data-video-action='toggle-play']");
    if (!button) return;

    const label = isPlaying ? button.dataset.pauseLabel : button.dataset.playLabel;
    if (label) {
      button.title = label;
      button.setAttribute("aria-label", label);
    }

    const svg = button.querySelector(".play-toggle-icon");
    if (!svg) return;

    svg.querySelector("[data-play]").style.display = isPlaying ? "none" : "inline";
    svg.querySelector("[data-pause]").style.display = isPlaying ? "inline" : "none";
  }

  function toggleVideoPlay(btn) {
    const wrapper = btn.closest(".video-wrapper");
    const video = wrapper.querySelector("video");

    if (video.paused) {
      video.play();
      updatePlayPauseButton(wrapper, true);
    } else {
      video.pause();
      updatePlayPauseButton(wrapper, false);
    }
  }

  function seekVideo(input) {
    const video = input.closest(".video-wrapper").querySelector("video");
    video.currentTime = (input.value / 100) * video.duration;

    isVideoSeeking = false;
  }

  function setVideoVolume(input) {
    const volume = window.utils.saveMediaVolume(input.value);
    window.utils.setMediaMuted(false);
    window.utils.applyMediaVolume(volume);
  }

  function toggleFullscreen(btn) {
    const wrapper = btn.closest(".video-wrapper");

    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      wrapper.requestFullscreen().catch(err => console.error("Fullscreen failed", err));
    }
  }

  function updateVideoProgress(video) {
    if (!video || isVideoSeeking) return;

    const wrapper = video.closest(".video-wrapper");
    const bar = wrapper.querySelector(".progress-bar");
    const display = wrapper.querySelector(".time-display");

    cr4te.media.updateProgress(video, bar, display);
  }

  function bindVideoElement(video) {
    const wrapper = video.closest(".video-wrapper");
    updatePlayPauseButton(wrapper, false);

    video.addEventListener("timeupdate", () => updateVideoProgress(video));
    video.addEventListener("loadedmetadata", () => {
      const wrapper = video.closest(".video-wrapper");
      const bar = wrapper.querySelector(".progress-bar");

      if (bar) {
        bar.disabled = false;
      }

      const display = wrapper.querySelector(".time-display");
      cr4te.media.updateProgress(video, bar, display);
    });
    video.addEventListener("pause", () => {
      updatePlayPauseButton(wrapper, false);
    });
    video.addEventListener("play", () => {
      updatePlayPauseButton(wrapper, true);
    });
    video.addEventListener("click", () => {
      const wrapper = video.closest(".video-wrapper");

      if (video.paused) {
        video.play();
        updatePlayPauseButton(wrapper, true);
      } else {
        video.pause();
        updatePlayPauseButton(wrapper, false);
      }
    });
  }

  function bindControlVisibility(wrapper) {
    let hideTimeout;
    const video = wrapper.querySelector("video");

    const showControls = () => {
      wrapper.classList.remove("hide-controls");
      wrapper.classList.remove("hide-cursor");

      clearTimeout(hideTimeout);

      if (!video.paused) {
        hideTimeout = setTimeout(() => {
          wrapper.classList.add("hide-controls");

          // Only hide cursor if in fullscreen
          if (document.fullscreenElement === wrapper) {
            wrapper.classList.add("hide-cursor");
          }
        }, CONTROL_HIDE_DELAY);
      }
    };

    wrapper.addEventListener("mousemove", showControls);
    wrapper.addEventListener("click", showControls);

    wrapper.addEventListener("mouseleave", () => {
      if (!video.paused) {
        wrapper.classList.add("hide-controls");
      }
    });

    video.addEventListener("play", showControls);
    video.addEventListener("pause", () => {
      clearTimeout(hideTimeout);
      wrapper.classList.remove("hide-controls");
      wrapper.classList.remove("hide-cursor");
    });

    document.addEventListener("fullscreenchange", () => {
      if (document.fullscreenElement !== wrapper) {
        wrapper.classList.remove("hide-cursor");
      }
    });
  }

  function initVideoPlayers() {
    document.querySelectorAll(".video-wrapper video").forEach(bindVideoElement);
    document.querySelectorAll(".video-wrapper").forEach(bindControlVisibility);
    window.utils.applyMediaVolume();

    document.querySelectorAll(".video-wrapper .progress-bar").forEach(bar => {
      cr4te.media.bindSeekSlider(bar, seeking => { isVideoSeeking = seeking; });
    });
  }

  cr4te.onReady(initVideoPlayers);

  document.addEventListener("click", event => {
    const button = event.target.closest("[data-video-action]");
    if (!button) return;

    const action = button.dataset.videoAction;
    if (!["toggle-play", "fullscreen"].includes(action)) return;

    event.preventDefault();

    if (action === "toggle-play") toggleVideoPlay(button);
    if (action === "fullscreen") toggleFullscreen(button);
  });

  document.addEventListener("change", event => {
    const input = event.target.closest("[data-video-action='seek']");
    if (!input) return;

    seekVideo(input);
  });

  document.addEventListener("input", event => {
    const input = event.target.closest("[data-video-action='volume']");
    if (!input) return;

    setVideoVolume(input);
  });

  cr4te.video.togglePlay = toggleVideoPlay;
  cr4te.video.seek = seekVideo;
  cr4te.video.setVolume = setVideoVolume;
  cr4te.video.toggleFullscreen = toggleFullscreen;
})();
