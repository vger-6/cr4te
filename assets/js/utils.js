window.utils = window.utils || {};

window.utils.parseGapValue = function (value) {
  if (value.endsWith('rem')) {
    const rem = parseFloat(value);
    return rem * parseFloat(getComputedStyle(document.documentElement).fontSize);
  }
  return parseFloat(value);
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

