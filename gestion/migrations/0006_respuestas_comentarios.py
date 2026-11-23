import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gestion", "0005_comentarios_archivados"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="comentariosugerencia", name="respuesta",
            field=models.TextField(blank=True, default="", max_length=1000),
        ),
        migrations.AddField(
            model_name="comentariosugerencia", name="fecha_respuesta",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="comentariosugerencia", name="respondido_por",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="respuestas_comentarios", to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
