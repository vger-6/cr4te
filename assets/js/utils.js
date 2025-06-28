window.utils = window.utils || {};

window.utils.parseGapValue = function (value) {
  if (value.endsWith('rem')) {
    const rem = parseFloat(value);
    return rem * parseFloat(getComputedStyle(document.documentElement).fontSize);
  }
  return parseFloat(value);
};

window.utils.getBreakpointPx = function (varName = '--mobile-breakpoint') {
  const rootStyles = getComputedStyle(document.documentElement);
  const value = rootStyles.getPropertyValue(varName).trim();
  return window.utils.parseGapValue(value);
};

window.utils.formatTime = function (sec) {
  return new Date(sec * 1000).toISOString().substr(11, 8);
}

window.utils.clearUrlParam = function (paramName) {
  const params = new URLSearchParams(window.location.search);
  params.delete(paramName);
  const newUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
  window.history.replaceState({}, '', newUrl);
};

