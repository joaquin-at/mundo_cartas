from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("torneo", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="juego",
            name="juego_imagen",
            field=models.ImageField(blank=True, upload_to="juegos/"),
        ),
    ]
