from django import template

from torneo.presentacion import presentacion_juego

register = template.Library()


@register.filter
def imagen_juego(juego):
    return presentacion_juego(juego)["imagen_url"]