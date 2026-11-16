import unicodedata

from django.templatetags.static import static


def normalizar_nombre(nombre):
    texto = unicodedata.normalize("NFKD", str(nombre or "")).casefold()
    return "".join(letra for letra in texto if letra.isalnum())


def presentacion_juego(juego):
    nombre = normalizar_nombre(getattr(juego, "juego_nombre", ""))
    imagenes = (
        ("pokemon", "pokemon.png", "pokemon"),
        ("magic", "magic.png", "magic"),
        ("yugioh", "yu-gi-oh.png", "yugioh"),
        ("onepiece", "one-piece.png", "onepiece"),
    )
    imagen_subida = getattr(juego, "juego_imagen", None)
    for palabra, archivo, tema in imagenes:
        if palabra in nombre:
            ruta = f"gestion/recursos/assets/juegos/{archivo}"
            return {"juego": juego, "imagen": ruta, "imagen_url": imagen_subida.url if imagen_subida else static(ruta), "tema": tema}
    return {"juego": juego, "imagen": "", "imagen_url": imagen_subida.url if imagen_subida else "", "tema": "general"}