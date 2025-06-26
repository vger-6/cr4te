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

