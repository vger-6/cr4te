(function () {
  const cr4te = window.cr4te = window.cr4te || {};
  cr4te.menus = cr4te.menus || {};

  function initTagActionMenus() {
    document.querySelectorAll(".tag-menu").forEach(menu => {
      const toggle = menu.querySelector("[data-menu-toggle]");
      const panel = menu.querySelector("[data-menu-panel]");
      if (!toggle || !panel || typeof cr4te.menus.bindMenu !== "function") return;

      cr4te.menus.bindMenu({ toggle, panel });
    });
  }

  cr4te.onReady(initTagActionMenus);
})();
