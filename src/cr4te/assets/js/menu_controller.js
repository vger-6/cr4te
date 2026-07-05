(function () {
  const cr4te = window.cr4te = window.cr4te || {};
  cr4te.menus = cr4te.menus || {};

  function menuOptions(panel) {
    return [...panel.querySelectorAll('[role="menuitem"], [role="menuitemradio"]')];
  }

  const activeMenus = new Set();

  function closeOtherMenus(currentMenu) {
    activeMenus.forEach(menu => {
      if (menu !== currentMenu) {
        menu.close();
      }
    });
  }

  function bindMenu({
    toggle,
    panel,
    options = null,
    initialFocusIndex = () => 0,
    onOptionSelected = null,
  }) {
    if (!toggle || !panel) return null;
    options = options || menuOptions(panel);

    function isOpen() {
      return toggle.getAttribute("aria-expanded") === "true";
    }

    function focusOption(index) {
      if (!options.length) return;
      options[(index + options.length) % options.length].focus();
    }

    function openMenu(focusIndex = null) {
      closeOtherMenus(menuApi);
      panel.style.display = "block";
      toggle.setAttribute("aria-expanded", "true");
      if (focusIndex !== null) {
        focusOption(focusIndex);
      }
    }

    function closeMenu(returnFocus = false) {
      panel.style.display = "none";
      toggle.setAttribute("aria-expanded", "false");
      if (returnFocus) {
        toggle.focus();
      }
    }

    toggle.addEventListener("click", () => {
      if (isOpen()) {
        closeMenu();
      } else {
        openMenu();
      }
    });

    toggle.addEventListener("keydown", event => {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        openMenu(initialFocusIndex());
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        openMenu(options.length - 1);
      } else if (event.key === "Escape") {
        event.preventDefault();
        closeMenu(true);
      }
    });

    panel.addEventListener("keydown", event => {
      const currentIndex = options.indexOf(document.activeElement);

      if (event.key === "ArrowDown") {
        event.preventDefault();
        focusOption(currentIndex + 1);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        focusOption(currentIndex - 1);
      } else if (event.key === "Home") {
        event.preventDefault();
        focusOption(0);
      } else if (event.key === "End") {
        event.preventDefault();
        focusOption(options.length - 1);
      } else if (event.key === "Escape") {
        event.preventDefault();
        closeMenu(true);
      } else if (event.key === "Tab") {
        closeMenu();
      }
    });

    document.addEventListener("click", event => {
      if (!toggle.contains(event.target) && !panel.contains(event.target)) {
        closeMenu();
      }
    });

    if (onOptionSelected) {
      options.forEach(option => {
        option.addEventListener("click", () => {
          onOptionSelected(option, { closeMenu });
        });
      });
    }

    const menuApi = {
      close: closeMenu,
      focusOption,
      isOpen,
      open: openMenu,
    };
    activeMenus.add(menuApi);
    return menuApi;
  }

  cr4te.menus.bindMenu = bindMenu;
})();
