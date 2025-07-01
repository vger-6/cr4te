window.utils = window.utils || {};

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
  return new Date(sec * 1000).toISOString().substr(11, 8);
}

window.utils.clearUrlParam = function (paramName) {
  const params = new URLSearchParams(window.location.search);
  params.delete(paramName);
  const newUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
  window.history.replaceState({}, '', newUrl);
};

