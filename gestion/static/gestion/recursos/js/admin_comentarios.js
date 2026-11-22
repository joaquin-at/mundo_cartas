document.addEventListener("DOMContentLoaded", function () {

    const formularioVarios = document.getElementById(
        "form-eliminar-varios"
    );

    const seleccionarTodos = document.getElementById(
        "seleccionar-todos"
    );

    const casillas = document.querySelectorAll(
        ".comentario-checkbox"
    );

    const botonEliminar = document.getElementById(
        "btn-eliminar-varios"
    );

    const contador = document.getElementById(
        "cantidad-seleccionados"
    );


    if (
        !formularioVarios ||
        !seleccionarTodos ||
        !botonEliminar ||
        !contador
    ) {
        return;
    }


    function actualizarSeleccion() {
        const seleccionados = Array.from(casillas).filter(
            function (casilla) {
                return casilla.checked;
            }
        ).length;


        contador.textContent = seleccionados;


        botonEliminar.disabled = seleccionados === 0;


        seleccionarTodos.checked =
            casillas.length > 0 &&
            seleccionados === casillas.length;


        seleccionarTodos.indeterminate =
            seleccionados > 0 &&
            seleccionados < casillas.length;
    }


    seleccionarTodos.disabled = casillas.length === 0;


    seleccionarTodos.addEventListener("change", function () {
        casillas.forEach(function (casilla) {
            casilla.checked = seleccionarTodos.checked;
        });

        actualizarSeleccion();
    });


    casillas.forEach(function (casilla) {
        casilla.addEventListener("change", actualizarSeleccion);
    });


    formularioVarios.addEventListener("submit", function (evento) {
        const cantidad = Array.from(casillas).filter(
            function (casilla) {
                return casilla.checked;
            }
        ).length;

        if (cantidad === 0) {
            evento.preventDefault();
            return;
        }

        const confirmar = window.confirm(
            "¿Estás seguro de que deseas eliminar " +
            cantidad +
            " mensaje(s)? Esta acción no se puede deshacer."
        );

        if (!confirmar) {
            evento.preventDefault();
        }
    });


    const formulariosIndividuales = document.querySelectorAll(
        ".form-eliminar-individual"
    );

    formulariosIndividuales.forEach(function (formulario) {
        formulario.addEventListener("submit", function (evento) {
            const confirmar = window.confirm(
                "¿Estás seguro de que deseas eliminar este mensaje? " +
                "Esta acción no se puede deshacer."
            );

            if (!confirmar) {
                evento.preventDefault();
            }
        });
    });


    actualizarSeleccion();
});