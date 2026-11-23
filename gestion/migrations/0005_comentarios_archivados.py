from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("gestion", "0004_initial")]

    operations = [
        migrations.AddField(
            model_name="comentariosugerencia",
            name="archivado",
            field=models.BooleanField(default=False, db_index=True),
        ),
    ]
