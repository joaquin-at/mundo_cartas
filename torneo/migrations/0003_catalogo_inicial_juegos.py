import unicodedata

from django.db import migrations


CATALOGO = (
    ("Magic: The Gathering", ("magic", "magicthegathering")),
    ("Pokémon TCG", ("pokemon", "pokemontcg")),
    ("Yu-Gi-Oh!", ("yugioh", "yugiohtcg")),
    ("Mitos y Leyendas", ("mitosyleyendas",)),
    ("One Piece Card Game", ("onepiece", "onepiececardgame")),
    ("Gundam Card Game", ("gundam", "gundamcardgame")),
    ("Digimon Card Game", ("digimon", "digimoncardgame")),
    ("Warhammer 40k", ("warhammer40k", "warhammer40000")),
    ("Riftbound: League of Legends TCG", ("riftbound", "riftboundleagueoflegends", "riftboundleagueoflegendstcg")),
)


def normalizar(nombre):
    texto = unicodedata.normalize("NFKD", nombre).casefold()
    return "".join(letra for letra in texto if letra.isalnum())


def precargar_juegos(apps, schema_editor):
    Juego = apps.get_model("torneo", "Juego")
    juegos = Juego.objects.using(schema_editor.connection.alias)
    for nombre, alias in CATALOGO:
        juego = juegos.filter(juego_nombre=nombre).first()
        if juego is None:
            juego = next((existente for existente in juegos.order_by("pk") if normalizar(existente.juego_nombre) in alias), None)
        if juego is None:
            juegos.create(juego_nombre=nombre, juego_activo=True)
        elif juego.juego_nombre != nombre:
            juego.juego_nombre = nombre
            juego.save(using=schema_editor.connection.alias, update_fields=["juego_nombre"])


class Migration(migrations.Migration):
    dependencies = [("torneo", "0002_juego_imagen")]
    operations = [migrations.RunPython(precargar_juegos, migrations.RunPython.noop)]
