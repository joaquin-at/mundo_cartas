from django.db import migrations, models

def guardar_puntos_historicos(apps, schema_editor):
    ResultadoTorneo = apps.get_model("torneo", "ResultadoTorneo")
    ReglaPuntuacionTorneo = apps.get_model(
        "torneo",
        "ReglaPuntuacionTorneo"
    )

    regla = ReglaPuntuacionTorneo.objects.filter(
        nombre="Puntuación estándar"
    ).first()

    if regla is not None:
        puntos_victoria = regla.puntos_victoria
        puntos_empate = regla.puntos_empate
        puntos_derrota = regla.puntos_derrota
    else:
        puntos_victoria = 3
        puntos_empate = 1
        puntos_derrota = 0

    for resultado in ResultadoTorneo.objects.filter(participo=True):
        resultado.puntos_victoria_aplicados = puntos_victoria
        resultado.puntos_empate_aplicados = puntos_empate
        resultado.puntos_derrota_aplicados = puntos_derrota

        resultado.puntos_torneo_guardados = (
            resultado.victorias * puntos_victoria
            + resultado.empates * puntos_empate
            + resultado.derrotas * puntos_derrota
        )

        resultado.save(
            update_fields=[
                "puntos_victoria_aplicados",
                "puntos_empate_aplicados",
                "puntos_derrota_aplicados",
                "puntos_torneo_guardados",
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("torneo", "0005_reglapuntuaciontorneo_resultadotorneo"),
    ]

    operations = [
        migrations.AddField(
            model_name="resultadotorneo",
            name="puntos_derrota_aplicados",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="resultadotorneo",
            name="puntos_empate_aplicados",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="resultadotorneo",
            name="puntos_torneo_guardados",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="resultadotorneo",
            name="puntos_victoria_aplicados",
            field= models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(
            guardar_puntos_historicos,
            migrations.RunPython.noop,
        ),
    ]
