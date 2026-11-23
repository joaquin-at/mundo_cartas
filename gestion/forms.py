from django import forms
from .models import ComentarioSugerencia




class ComentarioSugerenciaForm(forms.ModelForm):
    class Meta:
        model = ComentarioSugerencia

        fields = ["mensaje"]

        labels = {
            "mensaje": "Tu comentario",
        }

        widgets = {
            "mensaje": forms.Textarea(
                attrs={
                    "rows": 4,
                    "id": "mensaje-comentario",
                    "maxlength": 500,
                    "placeholder": "Escribe tu comentario...",
                }
            ),
        }

    def clean_mensaje(self):
        mensaje = self.cleaned_data["mensaje"].strip()

        if not mensaje:
            raise forms.ValidationError(
                "Debes escribir un comentario."
            )

        return mensaje


