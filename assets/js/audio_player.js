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
  if (!audio) return;

  const gallery = audio.closest(".audio-gallery");
  const bar = gallery.querySelector(".progress-bar");
  const timeDisplay = gallery.querySelector(".time-display");

  const percent = (audio.currentTime / audio.duration) * 100;
  if (bar) {
    bar.value = percent || 0;
    bar.style.backgroundSize = `${percent}% 100%`;
  }

  if (timeDisplay) {
    const format = sec => new Date(sec * 1000).toISOString().substr(11, 8);
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

