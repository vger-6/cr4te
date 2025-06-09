(function () {
  let currentIndex = 0;
  let currentGroup = [];
  let elements = {};
  let allImageLinks = [];
  let lastBoundLinks = [];
  
  function arraysEqual(arr1, arr2) {
    return arr1.length === arr2.length && arr1.every((v, i) => v === arr2[i]);
  }

  function createLightboxElements() {
    const overlay = document.createElement('div');
    overlay.id = 'lightbox-overlay';
    overlay.style = `
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.85);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 9999;
      cursor: default;
    `;

    const img = document.createElement('img');
    img.id = 'lightbox-image';
    img.style = `
      max-width: 90vw;
      max-height: 90vh;
      box-shadow: 0 0 15px black;
    `;

    const closeBtn = document.createElement('div');
    closeBtn.id = 'lightbox-close';
    closeBtn.textContent = '×';
    closeBtn.style = `
      position: fixed;
      top: 1rem;
      right: 1rem;
      font-size: 2rem;
      color: white;
      cursor: pointer;
      z-index: 10000;
    `;
    closeBtn.addEventListener('click', closeLightbox);

    const leftArrow = document.createElement('div');
    leftArrow.id = 'lightbox-left';
    leftArrow.textContent = '❮';
    leftArrow.style = arrowStyle('left');
    leftArrow.addEventListener('click', showPrevious);

    const rightArrow = document.createElement('div');
    rightArrow.id = 'lightbox-right';
    rightArrow.textContent = '❯';
    rightArrow.style = arrowStyle('right');
    rightArrow.addEventListener('click', showNext);

    overlay.appendChild(img);
    document.body.appendChild(overlay);
    document.body.appendChild(closeBtn);
    document.body.appendChild(leftArrow);
    document.body.appendChild(rightArrow);

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeLightbox();
    });

    elements = { overlay, img, closeBtn, leftArrow, rightArrow };

    document.addEventListener('keydown', handleKey);
  }

  function arrowStyle(position) {
    return `
      position: fixed;
      top: 50%;
      ${position}: 1rem;
      font-size: 3rem;
      color: white;
      cursor: pointer;
      user-select: none;
      transform: translateY(-50%);
      z-index: 10000;
    `;
  }

  function openLightbox(images, index) {
    currentGroup = images;
    currentIndex = index;

    if (!elements.overlay) {
      createLightboxElements();
    }

    updateLightboxImage();
    showElements(true);
  }

  function updateLightboxImage() {
    const img = elements.img;
    if (img && currentGroup[currentIndex]) {
      img.src = currentGroup[currentIndex];
    }
  }

  function closeLightbox() {
    showElements(false);
  }

  function showElements(visible) {
    const display = visible ? 'flex' : 'none';
    if (!elements.overlay) return;

    elements.overlay.style.display = display;
    elements.closeBtn.style.display = visible ? 'block' : 'none';
    elements.leftArrow.style.display = visible ? 'block' : 'none';
    elements.rightArrow.style.display = visible ? 'block' : 'none';
  }

  function showPrevious() {
    currentIndex = (currentIndex - 1 + currentGroup.length) % currentGroup.length;
    updateLightboxImage();
  }

  function showNext() {
    currentIndex = (currentIndex + 1) % currentGroup.length;
    updateLightboxImage();
  }

  function handleKey(e) {
    const overlay = document.getElementById('lightbox-overlay');
    if (!overlay || overlay.style.display !== 'flex') return;

    switch (e.key) {
      case 'Escape': closeLightbox(); break;
      case 'ArrowLeft': showPrevious(); break;
      case 'ArrowRight': showNext(); break;
    }
  }

  // Expose this globally so gallery pagination can rebind image click handlers
  window.rebindLightbox = function () {
    const gallery = document.getElementById('imageGallery');
    const lightboxEnabled = gallery?.dataset.lightbox !== "false";

    const galleries = document.querySelectorAll('.image-gallery[data-lightbox="true"]');
    galleries.forEach(gallery => {
      const links = Array.from(gallery.querySelectorAll('.image-wrapper a')).filter(a => a.href);
      links.forEach((link, index) => {
        link.onclick = (e) => {
          e.preventDefault();
          const currentGroup = links.map(a => a.href);
          openLightbox(currentGroup, index);
        };
      });
    });

    const newImageLinks = links.map(a => a.href);

    if (!lightboxEnabled) {
      // Remove existing lightbox bindings if disabled
      links.forEach(link => {
        link.onclick = null;
      });
      return;
    }

    if (arraysEqual(newImageLinks, lastBoundLinks)) return;

    lastBoundLinks = newImageLinks;
    allImageLinks = newImageLinks;

    links.forEach((link, index) => {
      link.onclick = (e) => {
        e.preventDefault();
        openLightbox(allImageLinks, index);
      };
    });
  };

  window.addEventListener('DOMContentLoaded', () => {
    rebindLightbox(); // Initial bind
  });
})();

