document.addEventListener("DOMContentLoaded", function () {
    const mensaje = document.getElementById("mensaje-comentario");
    const contador = document.getElementById("contador-comentario");


    if (!mensaje || !contador) {
        return;
    }


    function actualizarContador() {
        const cantidad = mensaje.value.length;

        contador.textContent = cantidad + " / 500 caracteres";


        contador.classList.toggle(
            "limite-cerca",
            cantidad >= 450 && cantidad < 500
        );


        contador.classList.toggle(
            "limite-alcanzado",
            cantidad >= 500
        );


        mensaje.classList.toggle(
            "limite-alcanzado",
            cantidad >= 500
        );
    }


    mensaje.addEventListener("input", actualizarContador);


    actualizarContador();
});