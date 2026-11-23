from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("registro", "0002_perfil_foto")]

    operations = [
        migrations.AddField(
            model_name="perfil", name="telefono",
            field=models.CharField(blank=True, max_length=16),
        ),
    ]
