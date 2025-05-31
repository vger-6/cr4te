let currentList = null;
let currentIndex = -1;

function playSelectedTrack(liElement) {
  const audio = liElement.closest(".audio-gallery").querySelector("audio");
  const listItems = [...liElement.parentElement.querySelectorAll("li")];

  currentList = listItems;
  currentIndex = listItems.indexOf(liElement);

  const src = liElement.dataset.src;
  audio.src = src;
  audio.play();
  highlightCurrent(liElement);
}

function playNextTrack(audio) {
  if (!currentList || currentIndex === -1) return;

  currentIndex++;
  if (currentIndex < currentList.length) {
    const nextLi = currentList[currentIndex];
    audio.src = nextLi.dataset.src;
    audio.play();
    highlightCurrent(nextLi);
  }
}

function highlightCurrent(liElement) {
  document.querySelectorAll(".track-title").forEach(el => el.classList.remove("playing"));
  liElement.classList.add("playing");
}

document.querySelectorAll(".audio-gallery audio").forEach(audio => {
  audio.addEventListener("play", () => {
    if (currentIndex === -1) {
      const li = audio.closest(".audio-gallery").querySelector("li");
      if (li) {
        playSelectedTrack(li);
      }
    }
  });
});

