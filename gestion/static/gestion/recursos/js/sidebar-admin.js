
document.addEventListener("DOMContentLoaded", function () {
    const layout = document.getElementById("adminLayout");
    const sidebarToggle = document.getElementById("sidebarToggle");
    const mobileToggle = document.getElementById("mobileMenuToggle");
    const overlay = document.getElementById("adminOverlay");

    const torneosToggle = document.getElementById("torneosMenuToggle");
    const torneosSubmenu = document.getElementById("torneosSubmenu");

    if (!layout) {
        return;
    }

    function esMovil() {
        return window.matchMedia("(max-width: 768px)").matches;
    }

    function cerrarMenuMovil() {
        layout.classList.remove("sidebar-open");

        if (mobileToggle) {
            mobileToggle.setAttribute("aria-expanded", "false");
        }
    }

    function actualizarBotonLateral() {
        if (!sidebarToggle) {
            return;
        }

        const contraido = layout.classList.contains(
            "sidebar-collapsed"
        );

        sidebarToggle.setAttribute(
            "aria-expanded",
            String(!contraido)
        );

        sidebarToggle.setAttribute(
            "aria-label",
            contraido ? "Expandir menú" : "Contraer menú"
        );
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener("click", function () {
            if (esMovil()) {
                cerrarMenuMovil();
                return;
            }

            layout.classList.toggle("sidebar-collapsed");
            actualizarBotonLateral();
        });
    }

    if (mobileToggle) {
        mobileToggle.setAttribute("aria-expanded", "false");

        mobileToggle.addEventListener("click", function () {
            const abierto = layout.classList.toggle(
                "sidebar-open"
            );

            mobileToggle.setAttribute(
                "aria-expanded",
                String(abierto)
            );
        });
    }

    if (overlay) {
        overlay.addEventListener("click", cerrarMenuMovil);
    }

    if (torneosToggle && torneosSubmenu) {
        torneosToggle.addEventListener("click", function () {
            if (
                layout.classList.contains("sidebar-collapsed")
                && !esMovil()
            ) {
                layout.classList.remove("sidebar-collapsed");
                actualizarBotonLateral();
            }

            const oculto = torneosSubmenu.classList.toggle(
                "hidden"
            );

            torneosToggle.setAttribute(
                "aria-expanded",
                String(!oculto)
            );
        });
    }

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            cerrarMenuMovil();
        }
    });

    window.addEventListener("resize", function () {
        if (!esMovil()) {
            cerrarMenuMovil();
        }
    });

    actualizarBotonLateral();
});
