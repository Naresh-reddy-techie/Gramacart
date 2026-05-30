(() => {
    "use strict";

    /* =========================
       CONFIG
    ========================= */
    const BREAKPOINT = 992;

    const SELECTORS = {
        sidebar: "#sidebar",
        wrapper: "#mainWrapper",
        overlay: "#sidebarOverlay",
        menuItems: ".menu-item",
        salesChart: "#salesChart",
        syncTime: "#sync-time",
    };

    const $ = (s) => document.querySelector(s);
    const $$ = (s) => document.querySelectorAll(s);

    const sidebar = $(SELECTORS.sidebar);
    const wrapper = $(SELECTORS.wrapper);
    const overlay = $(SELECTORS.overlay);

    let chartInstance = null;

    /* =========================
       STATE ENGINE (IMPORTANT)
    ========================= */

    const state = {
        isDesktop: () => window.innerWidth >= BREAKPOINT,
        sidebarCollapsed: false,
    };

    function applyLayout() {
        if (!sidebar || !wrapper) return;

        if (state.isDesktop()) {
            if (state.sidebarCollapsed) {
                sidebar.classList.add("collapsed");
                wrapper.classList.add("expanded");
            } else {
                sidebar.classList.remove("collapsed");
                wrapper.classList.remove("expanded");
            }
        } else {
            sidebar.classList.remove("collapsed", "active");
            wrapper.classList.remove("expanded");
            overlay?.classList.remove("active");
        }
    }

    /* =========================
       SIDEBAR ACTIONS
    ========================= */

    function toggleSidebar() {
        if (!sidebar || !wrapper) return;

        if (state.isDesktop()) {
            state.sidebarCollapsed = !state.sidebarCollapsed;
            localStorage.setItem("gc_sidebar_collapsed", state.sidebarCollapsed);
            applyLayout();
        } else {
            const isOpen = sidebar.classList.toggle("active");
            overlay?.classList.toggle("active", isOpen);
            document.body.style.overflow = isOpen ? "hidden" : "";
        }
    }

    function restoreState() {
        const saved = localStorage.getItem("gc_sidebar_collapsed");
        state.sidebarCollapsed = saved === "true";
        applyLayout();
    }

    /* =========================
       MENU ACTIVE STATE
    ========================= */

    function activateMenu() {
        const path = window.location.pathname;

        $$(SELECTORS.menuItems).forEach((el) => {
            const href = el.getAttribute("href");

            if (!href || href === "#") return;

            el.classList.toggle(
                "active",
                path === href || (href !== "/" && path.startsWith(href))
            );
        });
    }

    /* =========================
       MOBILE CLOSE
    ========================= */

    function bindMobileClose() {
        $$(SELECTORS.menuItems).forEach((el) => {
            el.addEventListener("click", () => {
                if (!state.isDesktop()) {
                    sidebar?.classList.remove("active");
                    overlay?.classList.remove("active");
                    document.body.style.overflow = "";
                }
            });
        });
    }

    /* =========================
       RESIZE HANDLER (FIXED)
    ========================= */

    let lastWidth = window.innerWidth;

    function handleResize() {
        window.addEventListener("resize", () => {
            const width = window.innerWidth;

            if (width === lastWidth) return;
            lastWidth = width;

            applyLayout();
        });
    }

    /* =========================
       TOOLTIP
    ========================= */

    function initTooltips() {
        if (!window.bootstrap) return;

        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((el) => {
            new bootstrap.Tooltip(el);
        });
    }

    /* =========================
       CLOCK
    ========================= */

    function updateClock() {
        const el = $(SELECTORS.syncTime);
        if (!el) return;

        const now = new Date();
        el.innerText = now.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        });
    }

    /* =========================
       INIT
    ========================= */

    document.addEventListener("DOMContentLoaded", () => {
        restoreState();
        activateMenu();
        bindMobileClose();
        handleResize();
        initTooltips();

        updateClock();
        setInterval(updateClock, 1000);

        window.toggleSidebar = toggleSidebar;
    });
})();