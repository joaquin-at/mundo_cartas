import django.core.validators
import registro.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("registro", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="perfil",
            name="foto",
            field=models.ImageField(
                blank=True,
                upload_to=registro.models.ruta_foto_perfil,
                validators=[django.core.validators.FileExtensionValidator(
                    allowed_extensions=["jpg", "jpeg", "png", "webp"]
                )],
            ),
        ),
    ]
