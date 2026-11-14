
from django import forms
from .models import Torneo


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
