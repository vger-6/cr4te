function rebuildJustifiedImageGallery() {
  document.querySelectorAll('.image-gallery--justified').forEach(gallery => {
    const maxHeight = parseFloat(gallery.dataset.imageMaxHeight) || 200;
    const gap = 16;
    const galleryWidth = gallery.clientWidth;

    const allWrappers = Array.from(gallery.querySelectorAll('.image-wrapper'));

    // Load all images and collect aspect ratios
    const loadPromises = allWrappers.map(wrapper => {
      const img = wrapper.querySelector('img');
      return new Promise(resolve => {
        if (img.complete) {
          resolve({ wrapper, img, ratio: img.naturalWidth / img.naturalHeight });
        } else {
          img.onload = () => resolve({ wrapper, img, ratio: img.naturalWidth / img.naturalHeight });
        }
      });
    });

    Promise.all(loadPromises).then(items => {
      // Remove all children before layout
      gallery.innerHTML = '';

      const rows = [];
      let row = [];
      let totalRatio = 0;

      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        row.push(item);
        totalRatio += item.ratio;

        const totalGap = gap * (row.length - 1);
        const rowHeight = (galleryWidth - totalGap) / totalRatio;

        if (rowHeight <= maxHeight) {
          rows.push([...row]);
          row = [];
          totalRatio = 0;
        }
      }

      // Handle remaining images in the last row
      if (row.length > 0) {
        let paddedRow = [...row];
        let ratioSum = totalRatio;

        const lastItem = row[row.length - 1];
        while (true) {
          const totalGap = gap * (paddedRow.length - 1);
          const rowHeight = (galleryWidth - totalGap) / ratioSum;

          if (rowHeight <= maxHeight) break;

          const clone = lastItem.wrapper.cloneNode(true);

          // Make the clone invisible and non-interactive
          clone.style.opacity = '0';
          clone.style.pointerEvents = 'none';
          clone.style.userSelect = 'none';

          const link = clone.querySelector('a');
          if (link) {
            link.removeAttribute('href');
            link.style.pointerEvents = 'none';
          }
          
          paddedRow.push({
            wrapper: null,       // no DOM element
            img: null,
            ratio: lastItem.ratio,
            isVirtual: true      // mark as virtual
          });
          ratioSum += lastItem.ratio;
        }

        rows.push(paddedRow);
      }

      // Render rows
      rows.forEach(row => {
        const rowEl = document.createElement('div');
        rowEl.classList.add('image-row');
        gallery.appendChild(rowEl);

        const totalRatio = row.reduce((sum, item) => sum + item.ratio, 0);
        const totalGap = gap * (row.length - 1);
        const rowHeight = (galleryWidth - totalGap) / totalRatio;

        row.forEach(item => {
          const width = item.ratio * rowHeight;

          if (item.wrapper && !item.isVirtual) {
            item.wrapper.style.width = `${width}px`;
            item.img.style.height = `${rowHeight}px`;
            rowEl.appendChild(item.wrapper);
          }
        });
      });
    });
  });
}

//TODO: Debounce the resize events e.g., using setTimeout
window.addEventListener('load', rebuildJustifiedImageGallery);
window.addEventListener('resize', rebuildJustifiedImageGallery);

