from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.db.models import Q
from .models import Juego, Torneo
from .presentacion import normalizar_nombre


class TorneoForm(forms.ModelForm):
    class Meta:
        model = Torneo

        fields = [
            "torneo_nombre",
            "torneo_inicio",
            "torneo_precio",
            "torneo_cupoMaximo",
            "torneo_estado",
            "torneo_juego",
            "torneo_liga",
        ]

        labels = {
            "torneo_nombre": "Nombre del torneo",
            "torneo_inicio": "Fecha y hora",
            "torneo_precio": "Precio de inscripción",
            "torneo_cupoMaximo": "Cupo máximo",
            "torneo_estado": "Estado",
            "torneo_juego": "Juego",
            "torneo_liga": "Liga (opcional)",
        }

        widgets = {
            "torneo_inicio": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        juegos_permitidos = Q(juego_activo=True)
        if self.instance.pk and self.instance.torneo_juego_id:
            juegos_permitidos |= Q(pk=self.instance.torneo_juego_id)
        self.fields["torneo_juego"].queryset = Juego.objects.filter(
            juegos_permitidos
        ).order_by("juego_nombre")

        self.fields["torneo_inicio"].input_formats = [
            "%Y-%m-%dT%H:%M",
        ]

        for campo in self.fields.values():
            campo.widget.attrs["class"] = "torneo-input"

    def clean_torneo_estado(self):
        estado = self.cleaned_data["torneo_estado"]

        if (
            self.instance.pk
            and self.instance.torneo_estado == "Cancelado"
            and estado != "Cancelado"
        ):
            raise forms.ValidationError(
                "No puedes reactivar un torneo cancelado."
            )

        return estado


class JuegoForm(forms.ModelForm):
    class Meta:
        model = Juego
        fields = ["juego_nombre", "juego_imagen", "juego_activo"]
        labels = {"juego_nombre": "Nombre del juego", "juego_imagen": "Imagen del juego", "juego_activo": "Juego activo"}
        help_texts = {"juego_imagen": "Opcional. PNG, JPG o WebP, hasta 5 MB. Si existe una imagen predeterminada para este juego, se mostrará; de lo contrario, quedará sin imagen.", "juego_activo": "Los juegos activos aparecen en el catálogo y se pueden seleccionar para nuevos torneos."}
        widgets = {
            "juego_nombre": forms.TextInput(attrs={"class": "torneo-input", "autofocus": True}),
            "juego_imagen": forms.ClearableFileInput(attrs={"accept": "image/png,image/jpeg,image/webp", "class": "admin-game-file"}),
        }

    def clean_juego_nombre(self):
        nombre = self.cleaned_data["juego_nombre"].strip()
        juegos = Juego.objects.all()
        if self.instance.pk:
            juegos = juegos.exclude(pk=self.instance.pk)
        nombre_normalizado = normalizar_nombre(nombre)
        if any(
            normalizar_nombre(existente) == nombre_normalizado
            for existente in juegos.values_list("juego_nombre", flat=True)
        ):
            raise forms.ValidationError("Ya existe un juego con ese nombre.")
        return nombre


    def clean_juego_imagen(self):
        imagen = self.cleaned_data.get("juego_imagen")
        if isinstance(imagen, UploadedFile):
            if imagen.size > 5 * 1024 * 1024:
                raise forms.ValidationError("La imagen no puede superar los 5 MB.")
            if getattr(getattr(imagen, "image", None), "format", None) not in {"PNG", "JPEG", "WEBP"}:
                raise forms.ValidationError("Selecciona una imagen PNG, JPG o WebP.")
        return imagen

class ConfirmarEliminarTorneoForm(forms.Form):
    confirmar_eliminacion = forms.BooleanField(
        label="Entiendo que el torneo se eliminará definitivamente y esta acción no se puede deshacer.",
        required=True,
        error_messages={"required": "Debes confirmar la eliminación definitiva del torneo."},
    )