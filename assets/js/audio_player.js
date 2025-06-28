(function () {
  let isSeeking = false;
  let currentList = null;
  let currentIndex = -1;

  function playTrack(audio, liElement) {
    const gallery = audio.closest(".audio-gallery");
    const listItems = [...liElement.parentElement.querySelectorAll("li")];

    currentList = listItems;
    currentIndex = listItems.indexOf(liElement);

    audio.src = liElement.dataset.src;
    audio.play();

    highlightCurrent(liElement);
    updateUIOnPlay(gallery);
  }

  function playNextTrack(audio) {
    if (!currentList || currentIndex + 1 >= currentList.length) return;
    currentIndex++;
    const nextLi = currentList[currentIndex];
    playTrack(audio, nextLi);
  }

  function prevTrack(btn) {
    if (!currentList || currentIndex <= 0) return;
    const gallery = btn.closest(".audio-gallery");
    const audio = gallery.querySelector("audio");

    currentIndex--;
    const prevLi = currentList[currentIndex];
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

  function stopAudio(btn) {
    const gallery = btn.closest(".audio-gallery");
    const audio = gallery.querySelector("audio");
    if (!audio) return;

    audio.pause();
    audio.currentTime = 0;
    audio.removeAttribute("src");
    audio.load();

    currentIndex = -1;
    currentList = null;

    gallery.querySelectorAll(".track-title").forEach(el => el.classList.remove("playing"));
    updatePlayPauseIcon(gallery, false);
    resetProgressUI(gallery);
  }

  function highlightCurrent(liElement) {
    document.querySelectorAll(".track-title").forEach(el => el.classList.remove("playing"));
    liElement.classList.add("playing");
  }

  function seekAudio(input) {
    if (input.disabled) return;
    const audio = input.closest(".audio-gallery").querySelector("audio");
    const percent = input.value / 100;
    audio.currentTime = percent * audio.duration;
  }

  function setVolume(input) {
    const audio = input.closest(".audio-gallery").querySelector("audio");
    audio.volume = input.value;

    input.style.backgroundSize = `${input.value * 100}% 100%`;
  }

  function updateProgress(audio) {
    if (!audio || isSeeking) return; // prevent jump while seeking

    const gallery = audio.closest(".audio-gallery");
    const bar = gallery.querySelector(".progress-bar");
    const timeDisplay = gallery.querySelector(".time-display");

    const percent = (audio.currentTime / audio.duration) * 100;
    if (bar) {
      bar.value = percent || 0;
      bar.style.backgroundSize = `${percent}% 100%`;
    }

    if (timeDisplay) {
      const format = sec => window.utils.formatTime(sec);
      timeDisplay.textContent = `${format(audio.currentTime)} / ${format(audio.duration || 0)}`;
    }
  }

  function updatePlayPauseIcon(gallery, isPlaying) {
    const svg = gallery.querySelector(".play-toggle-icon");
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
        bar.style.backgroundSize = "0% 100%";
      }
    }
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
  }

  // Initialize audio players
  document.querySelectorAll(".audio-gallery audio").forEach(audio => {
    const gallery = audio.closest(".audio-gallery");

    audio.addEventListener("timeupdate", () => updateProgress(audio));

    audio.addEventListener("play", () => {
      updateUIOnPlay(gallery);
      if (currentIndex === -1) {
        const li = gallery.querySelector("li");
        if (li) playSelectedTrack(li);
      }
    });

    audio.addEventListener("pause", () => {
      updatePlayPauseIcon(gallery, false);
    });
  });

  // Initial UI reset on load
  document.querySelectorAll(".audio-gallery .progress-bar").forEach(bar => {
    bar.disabled = true;
    bar.value = 0;
  });

  document.querySelectorAll(".audio-gallery .volume-slider").forEach(slider => {
    slider.style.backgroundSize = `${slider.value * 100}% 100%`;
  });

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".audio-gallery .progress-bar").forEach(bar => {
      // Disable initially
      bar.disabled = true;
      bar.value = 0;

      // Listen for user interaction
      bar.addEventListener("mousedown", () => { isSeeking = true; });
      bar.addEventListener("touchstart", () => { isSeeking = true; });
      bar.addEventListener("mouseup", () => { isSeeking = false; });
      bar.addEventListener("touchend", () => { isSeeking = false; });
      bar.addEventListener("mouseleave", () => { isSeeking = false; });
      bar.addEventListener("blur", () => { isSeeking = false; });
    });

    const audioSections = document.querySelectorAll('.section-box.audio-section');
    const threshold = 100;
    let currentScrollContainer = null;
      
    // Set initial state
    audioSections.forEach(section => {
      const controls = section.querySelector('.audio-controls');
      if (controls) {
        controls.style.opacity = '0';
        controls.style.pointerEvents = 'none';
      }
    });

    function getScrollContainer() {
      const breakpoint = window.utils.getBreakpointPx();
      if (window.innerWidth <= breakpoint) {
        return (
          document.querySelector('.project-layout') ||
          document.querySelector('.creator-layout')
        );
      } else {
        return (
          document.querySelector('.project-right') ||
          document.querySelector('.creator-right')
        );
      }
    }

    function updateAudioControlsVisibility() {
      const scrollContainer = getScrollContainer();
      const containerTop = scrollContainer.getBoundingClientRect().top;

      audioSections.forEach(section => {
        const controls = section.querySelector('.audio-controls');
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
        // Remove old listener
        if (currentScrollContainer) {
          currentScrollContainer.removeEventListener('scroll', updateAudioControlsVisibility);
        }

        // Add new listener
        newScrollContainer.addEventListener('scroll', updateAudioControlsVisibility);
        currentScrollContainer = newScrollContainer;
      }
    }

    // Optional: debounce resize for performance
    let resizeTimeout;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        setupScrollListener();
        updateAudioControlsVisibility();
      }, 150);
    });

    // Initial setup
    setupScrollListener();
    updateAudioControlsVisibility();
  });
    
  window.playSelectedTrack = playSelectedTrack;
  window.togglePlay = togglePlay;
  window.stopAudio = stopAudio;
  window.prevTrack = prevTrack;
  window.nextTrack = nextTrack;
  window.seekAudio = seekAudio;
  window.setVolume = setVolume;
  window.playNextTrack = playNextTrack;
})();
