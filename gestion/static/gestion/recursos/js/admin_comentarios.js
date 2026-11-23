document.addEventListener("DOMContentLoaded", function () {
    const formulario = document.getElementById("form-acciones-comentarios");
    const todos = document.getElementById("seleccionar-todos");
    const casillas = [...document.querySelectorAll(".comentario-checkbox")];
    const contador = document.getElementById("cantidad-seleccionados");
    const dialogo = document.getElementById("confirmar-eliminacion");
    const formConfirmacion = document.getElementById("form-confirmar-eliminacion");
    const aceptar = document.getElementById("aceptar-eliminacion");
    const ejecutar = document.getElementById("ejecutar-eliminacion");
    if (!formulario || !todos || !contador || !dialogo) return;

    let pendiente = null;
    const confirmados = new WeakSet();

    function actualizarSeleccion() {
        const cantidad = casillas.filter(casilla => casilla.checked).length;
        contador.textContent = cantidad;
        formulario.querySelectorAll("[data-seleccion]").forEach(boton => {
            boton.disabled = cantidad === 0;
        });
        todos.checked = cantidad > 0 && cantidad === casillas.length;
        todos.indeterminate = cantidad > 0 && cantidad < casillas.length;
        todos.disabled = casillas.length === 0;
    }

    function confirmarEliminacion(evento, cantidad) {
        const form = evento.currentTarget;
        if (confirmados.has(form)) {
            confirmados.delete(form);
            return;
        }
        evento.preventDefault();
        if (dialogo.open) return;
        pendiente = { form, boton: evento.submitter };
        document.getElementById("titulo-eliminacion").textContent =
            cantidad === 1 ? "Eliminar 1 mensaje" : `Eliminar ${cantidad} mensajes`;
        aceptar.checked = false;
        ejecutar.disabled = true;
        dialogo.showModal();
    }

    todos.addEventListener("change", function () {
        casillas.forEach(casilla => { casilla.checked = todos.checked; });
        actualizarSeleccion();
    });
    casillas.forEach(casilla => casilla.addEventListener("change", actualizarSeleccion));

    formulario.addEventListener("submit", function (evento) {
        const cantidad = casillas.filter(casilla => casilla.checked).length;
        if (!cantidad) {
            evento.preventDefault();
        } else if (evento.submitter?.dataset.accion === "eliminar") {
            confirmarEliminacion(evento, cantidad);
        }
    });
    document.querySelectorAll("[data-eliminar-comentario]").forEach(form => {
        form.addEventListener("submit", evento => confirmarEliminacion(evento, 1));
    });

    aceptar.addEventListener("change", function () {
        ejecutar.disabled = !aceptar.checked;
    });
    document.getElementById("cancelar-eliminacion").addEventListener("click", () => dialogo.close());
    dialogo.addEventListener("close", function () {
        pendiente?.boton?.focus();
        pendiente = null;
    });
    formConfirmacion.addEventListener("submit", function (evento) {
        evento.preventDefault();
        if (!aceptar.checked || !pendiente || ejecutar.disabled) return;
        ejecutar.disabled = true;
        const { form, boton } = pendiente;
        let confirmacion = form.querySelector('input[type="hidden"][name="confirmar"]');
        if (!confirmacion) {
            confirmacion = document.createElement("input");
            confirmacion.type = "hidden";
            confirmacion.name = "confirmar";
            form.append(confirmacion);
        }
        confirmacion.value = "on";
        confirmados.add(form);
        dialogo.close();
        form.requestSubmit(boton);
    });
    actualizarSeleccion();
});