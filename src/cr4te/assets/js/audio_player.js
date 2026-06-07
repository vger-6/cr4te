(function () {
  const cr4te = window.cr4te = window.cr4te || {};
  cr4te.audio = cr4te.audio || {};

  let isSeeking = false;

  function setGalleryState(gallery, list, index) {
    gallery._currentList = list;
    gallery.dataset.currentIndex = index;
  }

  function getGalleryState(gallery) {
    return {
      list: gallery._currentList || [],
      index: parseInt(gallery.dataset.currentIndex || "-1", 10),
    };
  }

  function playTrack(audio, liElement) {
    const gallery = audio.closest(".audio-gallery");
    const listItems = [...gallery.querySelectorAll("[data-audio-action='select-track']")];

    const currentIndex = listItems.indexOf(liElement);
    setGalleryState(gallery, listItems, currentIndex);

    audio.src = liElement.dataset.src;
    audio.play();

    highlightCurrent(gallery, liElement);
    updateUIOnPlay(gallery);
  }

  function playNextTrack(audio) {
    const gallery = audio.closest(".audio-gallery");
    const { list, index } = getGalleryState(gallery);

    if (!list || index + 1 >= list.length) return;

    const nextIndex = index + 1;
    const nextLi = list[nextIndex];
    setGalleryState(gallery, list, nextIndex);
    playTrack(audio, nextLi);
  }

  function prevTrack(btn) {
    const gallery = btn.closest(".audio-gallery");
    const audio = gallery.querySelector("audio");
    const { list, index } = getGalleryState(gallery);

    if (!list || index <= 0) return;

    const prevIndex = index - 1;
    const prevLi = list[prevIndex];
    setGalleryState(gallery, list, prevIndex);
    playTrack(audio, prevLi);
  }

  function nextTrack(btn) {
    const audio = btn.closest(".audio-gallery").querySelector("audio");
    playNextTrack(audio);
  }

  function playSelectedTrack(liElement) {
    const gallery = liElement.closest(".audio-gallery");
    const audio = gallery.querySelector("audio");
    playTrack(audio, liElement);
  }

  function getTrackButtons(gallery) {
    return [...gallery.querySelectorAll("[data-audio-action='select-track']")];
  }

  function setTrackTabStop(track) {
    const gallery = track.closest(".audio-gallery");
    getTrackButtons(gallery).forEach(button => {
      button.tabIndex = button === track ? 0 : -1;
    });
  }

  function focusTrack(track) {
    setTrackTabStop(track);
    track.focus();
  }

  function handleTrackNavigation(event, track) {
    const tracks = getTrackButtons(track.closest(".audio-gallery"));
    const currentIndex = tracks.indexOf(track);
    let nextIndex = currentIndex;

    if (event.key === "ArrowDown") {
      nextIndex = Math.min(currentIndex + 1, tracks.length - 1);
    } else if (event.key === "ArrowUp") {
      nextIndex = Math.max(currentIndex - 1, 0);
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = tracks.length - 1;
    } else {
      return;
    }

    event.preventDefault();
    focusTrack(tracks[nextIndex]);
  }

  function togglePlay(btn) {
    const gallery = btn.closest(".audio-gallery");
    const audio = gallery.querySelector("audio");
    if (!audio) return;

    if (audio.paused) {
      audio.play().then(() => updateUIOnPlay(gallery))
        .catch(err => console.error("Playback error:", err));
    } else {
      audio.pause();
      updatePlayPauseIcon(gallery, false);
    }
  }
  
  function stopAudioControls(gallery, audio) {
    if (!gallery || !audio) return;

    audio.pause();
    audio.currentTime = 0;
    audio.removeAttribute("src");
    audio.load();

    setGalleryState(gallery, null, -1);

    gallery.querySelectorAll(".track-title").forEach(el => el.classList.remove("playing"));
    updatePlayPauseIcon(gallery, false);
    resetProgressUI(gallery);
    updateButtonStates(gallery, false);
  }

  function stopAudio(btn) {
    const gallery = btn.closest(".audio-gallery");
    const audio = gallery?.querySelector("audio");
    stopAudioControls(gallery, audio);
  }

  function stopAudioFromAudioElement(audio) {
    const gallery = audio.closest(".audio-gallery");
    stopAudioControls(gallery, audio);
  }

  function highlightCurrent(gallery, liElement) {
    gallery.querySelectorAll(".track-title").forEach(el => el.classList.remove("playing"));
    liElement.classList.add("playing");
  }

  function seekAudio(input) {
    if (input.disabled) return;
    const audio = input.closest(".audio-gallery").querySelector("audio");
    const percent = input.value / 100;
    audio.currentTime = percent * audio.duration;
  }

  function setVolume(input) {
    const volume = window.utils.saveMediaVolume(input.value);
    window.utils.setMediaMuted(false);
    window.utils.applyMediaVolume(volume);
  }

  function updateProgress(audio) {
    if (!audio || isSeeking) return;

    const gallery = audio.closest(".audio-gallery");
    const bar = gallery.querySelector(".progress-bar");
    const timeDisplay = gallery.querySelector(".time-display");

    cr4te.media.updateProgress(audio, bar, timeDisplay);
  }

  function updatePlayPauseIcon(gallery, isPlaying) {
    const svg = gallery.querySelector(".play-toggle-icon");
    const button = gallery.querySelector("[data-audio-action='toggle-play']");

    if (button) {
      const label = isPlaying ? button.dataset.pauseLabel : button.dataset.playLabel;
      if (label) {
        button.title = label;
        button.setAttribute("aria-label", label);
      }
    }

    if (!svg) return;

    const playIcon = svg.querySelector("[data-play]");
    const pauseIcon = svg.querySelector("[data-pause]");

    playIcon.style.display = isPlaying ? "none" : "inline";
    pauseIcon.style.display = isPlaying ? "inline" : "none";
  }

  function setProgressBarEnabled(gallery, isEnabled) {
    const bar = gallery.querySelector(".progress-bar");

    if (bar) {
      bar.disabled = !isEnabled;
      if (!isEnabled) {
        bar.value = 0;
        window.utils.setRangeFill(bar);
      }
    }
  }

  function updateButtonStates(gallery, isPlaying) {
    const nextBtn = gallery.querySelector("[data-audio-action='next']");
    const prevBtn = gallery.querySelector("[data-audio-action='previous']");
    const stopBtn = gallery.querySelector("[data-audio-action='stop']");
    const { list, index } = getGalleryState(gallery);
    const hasTrack = isPlaying && Array.isArray(list) && index >= 0;
    const isFirstTrack = hasTrack && index === 0;
    const isLastTrack = hasTrack && index >= list.length - 1;

    [
      [prevBtn, !hasTrack || isFirstTrack],
      [nextBtn, !hasTrack || isLastTrack],
      [stopBtn, !isPlaying],
    ].forEach(([btn, isDisabled]) => {
      if (btn) {
        btn.disabled = isDisabled;
        btn.classList.toggle("disabled", isDisabled);
      }
    });
  }

  function resetProgressUI(gallery) {
    setProgressBarEnabled(gallery, false);
    const timeDisplay = gallery.querySelector(".time-display");
    if (timeDisplay) {
      timeDisplay.textContent = "00:00:00 / 00:00:00";
    }
  }

  function updateUIOnPlay(gallery) {
    updatePlayPauseIcon(gallery, true);
    setProgressBarEnabled(gallery, true);
    updateButtonStates(gallery, true);
  }

  function bindAudioElements() {
    document.querySelectorAll(".audio-gallery audio").forEach(audio => {
      const gallery = audio.closest(".audio-gallery");

      audio.addEventListener("timeupdate", () => updateProgress(audio));

      audio.addEventListener("play", () => {
        updateUIOnPlay(gallery);
        const { index } = getGalleryState(gallery);
        if (index === -1) {
          const li = gallery.querySelector("[data-audio-action='select-track']");
          if (li) playSelectedTrack(li);
        }
      });

      audio.addEventListener("pause", () => {
        updatePlayPauseIcon(gallery, false);
      });

      audio.addEventListener("ended", () => {
        const { list, index } = getGalleryState(gallery);
        if (!list || index + 1 >= list.length) {
          stopAudioFromAudioElement(audio);
        } else {
          playNextTrack(audio);
        }
      });
    });
  }

  function initAudioPlayers() {
    bindAudioElements();

    document.querySelectorAll(".audio-gallery").forEach(gallery => {
      const tracks = getTrackButtons(gallery);
      tracks.forEach((track, index) => {
        track.tabIndex = index === 0 ? 0 : -1;
      });
      updatePlayPauseIcon(gallery, false);
      updateButtonStates(gallery, false);
    });

    document.querySelectorAll(".audio-gallery .progress-bar").forEach(bar => {
      bar.disabled = true;
      bar.value = 0;
      cr4te.media.bindSeekSlider(bar, seeking => { isSeeking = seeking; });
    });

    window.utils.applyMediaVolume();

    const audioSections = document.querySelectorAll('.section-box.audio-gallery-section');
    const threshold = 100;
    let currentScrollContainer = null;

    audioSections.forEach(section => {
      const controls = section.querySelector('.audio-controls-wrapper');
      if (controls) {
        controls.style.opacity = '0';
        controls.style.pointerEvents = 'none';
      }
    });

    function getScrollContainer() {
      const firstGallery = document.querySelector('.audio-gallery');
      return firstGallery ? window.utils.getExplicitScrollableAncestor(firstGallery) || window : window;
    }

    function updateAudioControlsVisibility() {
      audioSections.forEach(section => {
        const controls = section.querySelector('.audio-controls-wrapper');
        if (!controls) return;

        const sectionRect = section.getBoundingClientRect();
        const controlsRect = controls.getBoundingClientRect();
        const verticalDistance = controlsRect.top - sectionRect.top;

        if (verticalDistance >= threshold) {
          controls.style.opacity = '1';
          controls.style.pointerEvents = 'auto';
        } else {
          controls.style.opacity = '0';
          controls.style.pointerEvents = 'none';
        }
      });
    }

    function setupScrollListener() {
      const newScrollContainer = getScrollContainer();

      if (newScrollContainer !== currentScrollContainer) {
        if (currentScrollContainer) {
          currentScrollContainer.removeEventListener('scroll', updateAudioControlsVisibility);
        }
        newScrollContainer.addEventListener('scroll', updateAudioControlsVisibility);
        currentScrollContainer = newScrollContainer;
      }
    }

    let resizeTimeout;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        setupScrollListener();
        updateAudioControlsVisibility();
      }, 150);
    });

    setupScrollListener();
    updateAudioControlsVisibility();
  }

  cr4te.onReady(initAudioPlayers);

  document.addEventListener("click", event => {
    const target = event.target.closest("[data-audio-action]");
    if (!target) return;

    const action = target.dataset.audioAction;
    if (!["select-track", "toggle-play", "stop", "previous", "next"].includes(action)) return;

    event.preventDefault();

    if (action === "select-track") {
      setTrackTabStop(target);
      playSelectedTrack(target);
    }
    if (action === "toggle-play") togglePlay(target);
    if (action === "stop") stopAudio(target);
    if (action === "previous") prevTrack(target);
    if (action === "next") nextTrack(target);
  });

  document.addEventListener("keydown", event => {
    const track = event.target.closest("[data-audio-action='select-track']");
    if (!track) return;

    handleTrackNavigation(event, track);
  });

  document.addEventListener("focusin", event => {
    const track = event.target.closest("[data-audio-action='select-track']");
    if (!track) return;

    setTrackTabStop(track);
  });

  document.addEventListener("change", event => {
    const input = event.target.closest("[data-audio-action='seek']");
    if (!input) return;

    seekAudio(input);
  });

  document.addEventListener("input", event => {
    const input = event.target.closest("[data-audio-action='volume']");
    if (!input) return;

    setVolume(input);
  });

  cr4te.audio.playSelectedTrack = playSelectedTrack;
  cr4te.audio.togglePlay = togglePlay;
  cr4te.audio.stop = stopAudio;
  cr4te.audio.previous = prevTrack;
  cr4te.audio.next = nextTrack;
  cr4te.audio.seek = seekAudio;
  cr4te.audio.setVolume = setVolume;
  cr4te.audio.playNextTrack = playNextTrack;
})();

