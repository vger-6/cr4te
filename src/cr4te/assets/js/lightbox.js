(function () {
  const cr4te = window.cr4te = window.cr4te || {};
  cr4te.lightbox = cr4te.lightbox || {};

  let currentIndex = 0;
  let currentGroup = [];
  let elements = {};
  let previouslyFocusedElement = null;

  function createLightboxElements() {
    const overlay = document.createElement('div');
    overlay.id = 'lightbox-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', 'Image lightbox');
    overlay.setAttribute('aria-describedby', 'lightbox-caption');
    overlay.tabIndex = -1;
    overlay.hidden = true;
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

    const content = document.createElement('figure');
    content.id = 'lightbox-content';
    content.style = `
      display: flex;
      flex-direction: column;
      align-items: center;
      max-width: 90vw;
      max-height: 90vh;
      margin: 0;
    `;

    const img = document.createElement('img');
    img.id = 'lightbox-image';
    img.style = `
      max-width: 90vw;
      max-height: 90vh;
      box-shadow: 0 0 15px black;
    `;

    const caption = document.createElement('figcaption');
    caption.id = 'lightbox-caption';
    caption.setAttribute('aria-live', 'polite');

    img.addEventListener('click', (event) => {
      event.stopPropagation();
      if (currentGroup.length > 1) {
        showNext();
      }
    });

    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.id = 'lightbox-close';
    closeBtn.setAttribute('aria-label', 'Close lightbox');
    closeBtn.textContent = 'x';
    closeBtn.style = `
      position: fixed;
      top: 1rem;
      right: 1rem;
      font-size: 2rem;
      cursor: pointer;
      z-index: 10000;
    `;
    closeBtn.addEventListener('click', closeLightbox);

    const leftArrow = document.createElement('button');
    leftArrow.type = 'button';
    leftArrow.id = 'lightbox-left';
    leftArrow.setAttribute('aria-label', 'Previous image');
    leftArrow.textContent = '❮';
    leftArrow.style = arrowStyle('left');
    leftArrow.addEventListener('click', showPrevious);

    const rightArrow = document.createElement('button');
    rightArrow.type = 'button';
    rightArrow.id = 'lightbox-right';
    rightArrow.setAttribute('aria-label', 'Next image');
    rightArrow.textContent = '❯';
    rightArrow.style = arrowStyle('right');
    rightArrow.addEventListener('click', showNext);

    content.appendChild(img);
    content.appendChild(caption);
    overlay.appendChild(content);
    overlay.appendChild(closeBtn);
    overlay.appendChild(leftArrow);
    overlay.appendChild(rightArrow);
    document.body.appendChild(overlay);

    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) closeLightbox();
    });

    elements = { overlay, img, caption, closeBtn, leftArrow, rightArrow };

    document.addEventListener('keydown', handleKey);
  }

  function arrowStyle(position) {
    return `
      position: fixed;
      top: 50%;
      ${position}: 1rem;
      font-size: 3rem;
      cursor: pointer;
      user-select: none;
      transform: translateY(-50%);
      z-index: 10000;
    `;
  }

  function openLightbox(images, index, trigger) {
    currentGroup = images;
    currentIndex = index;
    previouslyFocusedElement = trigger || document.activeElement;

    if (!elements.overlay) {
      createLightboxElements();
    }

    updateLightboxImage();
    showElements(true);

    const single = currentGroup.length <= 1;
    elements.leftArrow.hidden = single;
    elements.rightArrow.hidden = single;
    elements.overlay.focus();
  }

  function updateLightboxImage() {
    const item = normalizeLightboxItem(currentGroup[currentIndex]);
    if (!elements.img || !item) return;

    elements.img.src = item.src;
    elements.img.alt = item.title;
    elements.caption.textContent = item.title;
  }

  function normalizeLightboxItem(item) {
    if (!item) return null;
    if (typeof item === 'string') return { src: item, title: '' };
    return {
      src: item.src,
      title: item.title || ''
    };
  }

  function closeLightbox() {
    showElements(false);
    if (elements.img) {
      elements.img.src = '';
      elements.img.alt = '';
    }
    if (elements.caption) {
      elements.caption.textContent = '';
    }
    if (previouslyFocusedElement?.isConnected) {
      previouslyFocusedElement.focus();
    }
    previouslyFocusedElement = null;
  }

  function showElements(visible) {
    if (!elements.overlay) return;

    elements.overlay.hidden = !visible;
    elements.overlay.style.display = visible ? 'flex' : 'none';
  }

  function showPrevious() {
    currentIndex = (currentIndex - 1 + currentGroup.length) % currentGroup.length;
    updateLightboxImage();
  }

  function showNext() {
    currentIndex = (currentIndex + 1) % currentGroup.length;
    updateLightboxImage();
  }

  function trapFocus(event) {
    const controls = [
      elements.closeBtn,
      elements.leftArrow,
      elements.rightArrow
    ].filter(control => control && !control.hidden && !control.disabled);
    if (!controls.length) return;

    const first = controls[0];
    const last = controls[controls.length - 1];
    const focusIsInside = elements.overlay.contains(document.activeElement);

    if (!focusIsInside || document.activeElement === elements.overlay) {
      event.preventDefault();
      (event.shiftKey ? last : first).focus();
    } else if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function handleKey(event) {
    if (!elements.overlay || elements.overlay.hidden) return;

    if (event.key === 'Tab') {
      trapFocus(event);
      return;
    }

    switch (event.key) {
      case 'Escape':
        event.preventDefault();
        closeLightbox();
        break;
      case 'ArrowLeft':
        if (currentGroup.length > 1) {
          event.preventDefault();
          showPrevious();
        }
        break;
      case 'ArrowRight':
        if (currentGroup.length > 1) {
          event.preventDefault();
          showNext();
        }
        break;
    }
  }

  function buildLightboxItem(link) {
    return {
      src: link.href,
      title: getLightboxTitle(link)
    };
  }

  function getLightboxTitle(link) {
    const img = link.querySelector('img');
    const values = [
      link.dataset.lightboxTitle,
      link.querySelector('.image-caption')?.textContent,
      img?.getAttribute('title'),
      link.getAttribute('title'),
      img?.getAttribute('alt')
    ];

    return values
      .map(value => (value || '').trim())
      .find(Boolean) || '';
  }

  function rebindLightbox() {
    const galleries = document.querySelectorAll('.image-gallery--justified[data-lightbox="true"], .image-gallery--aspect[data-lightbox="true"]');

    galleries.forEach(gallery => {
      const links = Array.from(gallery.querySelectorAll('.image-wrapper a')).filter(anchor => anchor.href);

      links.forEach(link => {
        link.onclick = (event) => {
          event.preventDefault();

          const currentGroupLinks = Array.from(gallery.querySelectorAll('.image-wrapper a')).filter(anchor => anchor.href);
          const group = currentGroupLinks.map(buildLightboxItem);
          const startIndex = currentGroupLinks.indexOf(link);

          openLightbox(group, startIndex, link);
        };
      });
    });
  }

  function rebindSingleLightbox() {
    document.querySelectorAll('a[data-lightbox-single="true"]').forEach(link => {
      link.onclick = (event) => {
        event.preventDefault();
        openLightbox([buildLightboxItem(link)], 0, link);
      };
    });
  }

  cr4te.lightbox.rebind = rebindLightbox;
  cr4te.lightbox.rebindSingle = rebindSingleLightbox;

  cr4te.onReady(() => {
    rebindLightbox();
    rebindSingleLightbox();
  });
})();
