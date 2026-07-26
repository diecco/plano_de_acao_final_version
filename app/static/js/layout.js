(function () {
    "use strict";

    const root = document.documentElement;
    const toggleButton = document.getElementById("toggleSidebar");
    const collapseButton = document.getElementById("collapseSidebar");
    const overlay = document.getElementById("sidebarOverlay");
    const searchInput = document.getElementById("sidebarSearch");
    const focusSearchButton = document.getElementById("focusSidebarSearch");
    const noResults = document.getElementById("sidebarNoResults");
    const desktopBreakpoint = 992;

    function isDesktop() {
        return window.innerWidth >= desktopBreakpoint;
    }

    function persistSidebar() {
        const state = root.classList.contains("sidebar-collapsed")
            ? "collapsed"
            : "expanded";
        localStorage.setItem("trackplan_sidebar", state);
    }

    function closeMobileSidebar() {
        root.classList.remove("sidebar-mobile-open");
    }

    function toggleSidebar() {
        if (isDesktop()) {
            root.classList.toggle("sidebar-collapsed");
            persistSidebar();
            return;
        }

        root.classList.toggle("sidebar-mobile-open");
    }

    function expandSidebarForNavigation(event) {
        if (!isDesktop() || !root.classList.contains("sidebar-collapsed")) {
            return;
        }

        const trigger = event.currentTarget;
        const targetSelector = trigger.getAttribute("data-bs-target");

        root.classList.remove("sidebar-collapsed");
        persistSidebar();

        if (targetSelector) {
            event.preventDefault();
            const target = document.querySelector(targetSelector);
            if (target && window.bootstrap) {
                bootstrap.Collapse.getOrCreateInstance(target).show();
            }
        }
    }

    function normalizeSearch(value) {
        return value
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .toLowerCase()
            .trim();
    }

    function filterMenu() {
        if (!searchInput) return;

        const query = normalizeSearch(searchInput.value);
        const modules = document.querySelectorAll(".sidebar-module");
        let visibleCount = 0;

        modules.forEach(function (module) {
            const searchable = normalizeSearch(
                module.getAttribute("data-search-label") || module.textContent
            );
            const visible = !query || searchable.includes(query);

            module.classList.toggle("d-none", !visible);
            if (visible) visibleCount += 1;

            if (query && visible && window.bootstrap) {
                const submenu = module.querySelector(".sidebar-submenu");
                if (submenu) {
                    bootstrap.Collapse.getOrCreateInstance(
                        submenu,
                        {toggle: false}
                    ).show();
                }
            }
        });

        if (noResults) {
            noResults.classList.toggle("d-none", visibleCount !== 0);
        }
    }

    function prepareFlashMessages() {
        document.querySelectorAll(".flash-messages .alert").forEach(function (alert) {
            window.setTimeout(function () {
                if (alert.isConnected && window.bootstrap) {
                    bootstrap.Alert.getOrCreateInstance(alert).close();
                }
            }, 5000);
        });
    }

    if (toggleButton) {
        toggleButton.addEventListener("click", toggleSidebar);
    }

    if (collapseButton) {
        collapseButton.addEventListener("click", function () {
            if (isDesktop()) {
                root.classList.add("sidebar-collapsed");
                persistSidebar();
            } else {
                closeMobileSidebar();
            }
        });
    }

    if (overlay) {
        overlay.addEventListener("click", closeMobileSidebar);
    }

    document.querySelectorAll(".sidebar-module-toggle[data-bs-toggle='collapse']")
        .forEach(function (trigger) {
            trigger.addEventListener("click", expandSidebarForNavigation);
        });

    document.querySelectorAll(".sidebar-link, .sidebar-direct-link")
        .forEach(function (link) {
            link.addEventListener("click", function () {
                if (!isDesktop()) closeMobileSidebar();
            });
        });

    if (searchInput) {
        searchInput.addEventListener("input", filterMenu);
    }

    if (focusSearchButton) {
        focusSearchButton.addEventListener("click", function () {
            if (isDesktop() && root.classList.contains("sidebar-collapsed")) {
                root.classList.remove("sidebar-collapsed");
                persistSidebar();
            } else if (!isDesktop()) {
                root.classList.add("sidebar-mobile-open");
            }

            window.setTimeout(function () {
                if (searchInput) searchInput.focus();
            }, 180);
        });
    }

    window.addEventListener("resize", function () {
        if (isDesktop()) closeMobileSidebar();
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") closeMobileSidebar();
    });

    prepareFlashMessages();
})();
