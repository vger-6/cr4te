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
    
    // Hide arrows if only one image
    const single = currentGroup.length <= 1;
    elements.leftArrow.style.display = single ? 'none' : 'block';
    elements.rightArrow.style.display = single ? 'none' : 'block';
  }

  function updateLightboxImage() {
    const img = elements.img;
    if (img && currentGroup[currentIndex]) {
      img.src = currentGroup[currentIndex];
    }
  }

  function closeLightbox() {
    showElements(false);
    if (elements.img) {
      elements.img.src = ''; // Clear the image source to prevent flashing
    }
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
    const galleries = document.querySelectorAll('.image-gallery--justified[data-lightbox="true"], .image-gallery--aspect[data-lightbox="true"]');

    galleries.forEach(gallery => {
      const links = Array.from(gallery.querySelectorAll('.image-wrapper a')).filter(a => a.href);

      links.forEach((link, index) => {
        link.onclick = (e) => {
          e.preventDefault();

          // Re-scope current group to only this gallery’s current links
          const currentGroupLinks = Array.from(gallery.querySelectorAll('.image-wrapper a')).filter(a => a.href);
          const group = currentGroupLinks.map(a => a.href);
          const startIndex = currentGroupLinks.indexOf(link);

          openLightbox(group, startIndex);
        };
      });
    });
  };
  
  window.rebindSingleLightbox = function () {
    document.querySelectorAll('a[data-lightbox-single="true"]').forEach(link => {
      link.onclick = (e) => {
        e.preventDefault();
        openLightbox([link.href], 0); // Use a group of one image
      };
    });
  };

  window.addEventListener('DOMContentLoaded', () => {
    rebindLightbox(); // Initial bind
    rebindSingleLightbox();
  });
})();

