window.cr4te = window.cr4te || {};
window.cr4te.utils = window.cr4te.utils || {};
window.cr4te.galleries = window.cr4te.galleries || {};
window.cr4te.lightbox = window.cr4te.lightbox || {};
window.cr4te.pagination = window.cr4te.pagination || {};
window.cr4te.media = window.cr4te.media || {};
window.utils = window.cr4te.utils;

window.cr4te.readyCallbacks = window.cr4te.readyCallbacks || [];

window.cr4te.onReady = function (callback) {
  if (document.readyState === 'loading') {
    window.cr4te.readyCallbacks.push(callback);
    return;
  }

  callback();
};

document.addEventListener('DOMContentLoaded', () => {
  const callbacks = window.cr4te.readyCallbacks.splice(0);
  callbacks.forEach(callback => callback());
});

window.utils.parseCssLength = function (value, contextElement = document.documentElement) {
  if (typeof value !== 'string') return NaN;

  const trimmed = value.trim().toLowerCase();

  if (trimmed.endsWith('px')) {
    return parseFloat(trimmed);
  }

  if (trimmed.endsWith('rem')) {
    const rem = parseFloat(trimmed);
    const rootFontSize = parseFloat(getComputedStyle(document.documentElement).fontSize);
    return rem * rootFontSize;
  }

  if (trimmed.endsWith('em')) {
    const em = parseFloat(trimmed);
    const fontSize = parseFloat(getComputedStyle(contextElement).fontSize);
    return em * fontSize;
  }

  if (trimmed.endsWith('vw')) {
    const vw = parseFloat(trimmed);
    return (vw / 100) * window.innerWidth;
  }

  if (trimmed.endsWith('vh')) {
    const vh = parseFloat(trimmed);
    return (vh / 100) * window.innerHeight;
  }

  // Add more units here if needed: e.g., vmin, vmax, etc.

  // Attempt to parse as a raw number
  const numeric = parseFloat(trimmed);
  return isNaN(numeric) ? NaN : numeric;
};

window.utils.getBreakpointPx = function (varName = '--mobile-breakpoint') {
  const rootStyles = getComputedStyle(document.documentElement);
  const value = rootStyles.getPropertyValue(varName).trim();
  return window.utils.parseCssLength(value);
};

window.utils.getExplicitScrollableAncestor = function (el) {
  let parent = el.parentElement;
  while (parent) {
    const style = window.getComputedStyle(parent);
    const overflowY = style.getPropertyValue('overflow-y');
    const isScrollable = (overflowY === 'auto' || overflowY === 'scroll');
    const canScroll = parent.scrollHeight > parent.clientHeight;

    if (isScrollable && canScroll) {
      return parent;
    }

    parent = parent.parentElement;
  }
  return null;
}

window.utils.formatTime = function (sec) {
  const totalSeconds = Math.max(0, Math.floor(Number(sec) || 0));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const pad = value => String(value).padStart(2, '0');

  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
}

window.utils.rangeFillFrameIds = window.utils.rangeFillFrameIds || new WeakMap();

window.utils.setRangeFillNow = function (input) {
  const min = Number(input.min || 0);
  const max = Number(input.max || 100);
  const value = Number(input.value || 0);
  const percent = max === min ? 0 : ((value - min) / (max - min)) * 100;

  // Keep this in sync with the `.media-slider` background gradient in base.css.
  input.style.backgroundSize = `${Math.max(0, Math.min(100, percent))}% 100%`;
};

window.utils.setRangeFill = function (input) {
  if (window.utils.rangeFillFrameIds.has(input)) {
    return;
  }

  const frameId = requestAnimationFrame(() => {
    window.utils.rangeFillFrameIds.delete(input);
    window.utils.setRangeFillNow(input);
  });

  window.utils.rangeFillFrameIds.set(input, frameId);
};

window.cr4te.media.updateProgress = function (media, bar, display) {
  const percent = (media.currentTime / media.duration) * 100;

  if (bar) {
    bar.value = percent || 0;
    window.utils.setRangeFill(bar);
  }

  if (display) {
    display.textContent = `${window.utils.formatTime(media.currentTime)} / ${window.utils.formatTime(media.duration || 0)}`;
  }
};

window.cr4te.media.bindSeekSlider = function (bar, setSeeking) {
  bar.addEventListener("mousedown", () => { setSeeking(true); });
  bar.addEventListener("mouseup", () => { setSeeking(false); });
  bar.addEventListener("touchstart", () => { setSeeking(true); });
  bar.addEventListener("touchend", () => { setSeeking(false); });
  bar.addEventListener("input", () => { window.utils.setRangeFill(bar); });
  bar.addEventListener("mouseleave", () => { setSeeking(false); });
  bar.addEventListener("blur", () => { setSeeking(false); });
  window.utils.setRangeFill(bar);
};

window.utils.MEDIA_VOLUME_KEY = 'cr4te_media_volume';
window.utils.MEDIA_MUTED_KEY = 'cr4te_media_muted';

window.utils.normalizeVolume = function (value, fallback = 1) {
  const volume = Number(value);

  if (!Number.isFinite(volume)) {
    return fallback;
  }

  return Math.max(0, Math.min(1, volume));
};

window.utils.getMediaVolume = function () {
  try {
    const storedVolume = localStorage.getItem(window.utils.MEDIA_VOLUME_KEY);

    if (storedVolume !== null) {
      return window.utils.normalizeVolume(storedVolume);
    }
  } catch (err) {
    console.warn('Unable to read saved media volume:', err);
  }

  return 1;
};

window.utils.saveMediaVolume = function (value) {
  const volume = window.utils.normalizeVolume(value);

  try {
    localStorage.setItem(window.utils.MEDIA_VOLUME_KEY, String(volume));
  } catch (err) {
    console.warn('Unable to save media volume:', err);
  }

  return volume;
};

window.utils.getMediaMuted = function () {
  try {
    return localStorage.getItem(window.utils.MEDIA_MUTED_KEY) === 'true';
  } catch (err) {
    console.warn('Unable to read saved media muted state:', err);
    return false;
  }
};

window.utils.saveMediaMuted = function (isMuted) {
  const muted = Boolean(isMuted);

  try {
    localStorage.setItem(window.utils.MEDIA_MUTED_KEY, String(muted));
  } catch (err) {
    console.warn('Unable to save media muted state:', err);
  }

  return muted;
};

window.utils.updateMuteControls = function (isMuted = window.utils.getMediaMuted()) {
  document.querySelectorAll('.volume-toggle-btn').forEach(button => {
    const label = isMuted ? button.dataset.unmuteLabel : button.dataset.muteLabel;

    if (label) {
      button.title = label;
      button.setAttribute('aria-label', label);
    }

    const volumeIcon = button.querySelector('[data-volume]');
    const mutedIcon = button.querySelector('[data-muted]');

    if (volumeIcon) volumeIcon.style.display = isMuted ? 'none' : 'inline';
    if (mutedIcon) mutedIcon.style.display = isMuted ? 'inline' : 'none';
  });
};

window.utils.setMediaMuted = function (isMuted, persist = true) {
  const muted = persist ? window.utils.saveMediaMuted(isMuted) : Boolean(isMuted);

  document.querySelectorAll('audio, video').forEach(media => {
    media.muted = muted;
  });

  window.utils.updateMuteControls(muted);

  return muted;
};

window.utils.applyMediaVolume = function (value = window.utils.getMediaVolume()) {
  const volume = window.utils.normalizeVolume(value);
  const muted = window.utils.getMediaMuted();

  document.querySelectorAll('audio, video').forEach(media => {
    media.volume = volume;
    media.muted = muted;
  });

  document.querySelectorAll('.volume-slider').forEach(slider => {
    slider.value = volume;
    window.utils.setRangeFill(slider);
  });

  window.utils.updateMuteControls(muted);

  return volume;
};

window.cr4te.media.toggleMute = function () {
  return window.utils.setMediaMuted(!window.utils.getMediaMuted());
};

document.addEventListener('click', event => {
  const button = event.target.closest('[data-media-action="toggle-mute"]');
  if (!button) return;

  event.preventDefault();
  window.cr4te.media.toggleMute();
});

if (!window.utils.mediaVolumeSyncInitialized) {
  window.addEventListener('pageshow', () => {
    window.utils.applyMediaVolume();
  });

  window.utils.mediaVolumeSyncInitialized = true;
}

window.utils.clearUrlParam = function (paramName) {
  const params = new URLSearchParams(window.location.search);
  params.delete(paramName);
  const newUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
  window.history.replaceState({}, '', newUrl);
};

