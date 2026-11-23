from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("registro", "0003_perfil_telefono")]

    operations = [
        migrations.AddField(
            model_name="perfil",
            name="desactivacion_solicitada_el",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="perfil",
            name="motivo_desactivacion",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
