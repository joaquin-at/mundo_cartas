document.addEventListener("DOMContentLoaded", function () {
    const menu = document.querySelector('.perfil-lateral-menu[aria-label="Secciones del perfil"]');
    if (!menu) return;
    const enlaces = [...menu.querySelectorAll('a[href^="#"]')];

    function activar(hash) {
        if (hash === "#editar-perfil" || hash === "#foto-perfil") hash = "#mis-datos";
        if (!enlaces.some(enlace => enlace.hash === hash)) {
            hash = "#" + (menu.dataset.seccionInicial || "mis-datos");
        }
        enlaces.forEach(enlace => {
            const seleccionado = enlace.hash === hash;
            enlace.classList.toggle("selected", seleccionado);
            if (seleccionado) enlace.setAttribute("aria-current", "location");
            else enlace.removeAttribute("aria-current");
        });
    }
    enlaces.forEach(enlace => enlace.addEventListener("click", () => activar(enlace.hash)));
    window.addEventListener("hashchange", () => activar(window.location.hash));
    activar(window.location.hash);
});
