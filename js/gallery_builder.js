function rebuildAllImageGalleries() {
  const galleries = document.querySelectorAll('.image-gallery');

  galleries.forEach(gallery => {
    const allWrappers = Array.from(gallery.querySelectorAll('.image-wrapper'));
    gallery.innerHTML = '';

    const imagesPerRow = 5;
    const gap = 16;

    function createRow() {
      const row = document.createElement('div');
      row.classList.add('image-row');
      return row;
    }

    const rows = [];
    for (let i = 0; i < allWrappers.length; i += imagesPerRow) {
      const rowWrappers = allWrappers.slice(i, i + imagesPerRow);
      const row = createRow();
      rowWrappers.forEach(w => row.appendChild(w));
      rows.push(row);
      gallery.appendChild(row);
    }

    const loadPromises = allWrappers.map(wrapper => {
      const img = wrapper.querySelector('img');
      return img.complete ? Promise.resolve() : new Promise(res => img.onload = res);
    });

    Promise.all(loadPromises).then(() => {
      rows.forEach(row => {
        const wrappers = Array.from(row.querySelectorAll('.image-wrapper'));
        const ratios = wrappers.map(w => {
          const img = w.querySelector('img');
          return img.naturalWidth / img.naturalHeight;
        });

        const totalRatio = ratios.reduce((a, b) => a + b, 0);
        const totalGap = gap * (wrappers.length - 1);
        const rowWidth = row.clientWidth - totalGap;
        const commonHeight = rowWidth / totalRatio;

        wrappers.forEach((wrapper, idx) => {
          const width = commonHeight * ratios[idx];
          wrapper.style.width = `${width}px`;
          wrapper.style.height = `${commonHeight}px`;
        });
      });
    });
  });
}

window.addEventListener('load', rebuildAllImageGalleries);
window.addEventListener('resize', rebuildAllImageGalleries);

