from django import forms
from .models import ComentarioSugerencia




class ComentarioSugerenciaForm(forms.ModelForm):
    class Meta:
        model = ComentarioSugerencia

        fields = ["tipo", "mensaje"]

        labels = {
            "tipo": "Tipo de mensaje",
            "mensaje": "Mensaje",
        }

        widgets = {
            "tipo": forms.Select(),
            "mensaje": forms.Textarea(
                attrs={
                    "rows": 4,
                    "maxlength": 500,
                    "placeholder": "Escribe tu comentario o sugerencia...",
                }
            ),
        }

    def clean_mensaje(self):
        mensaje = self.cleaned_data["mensaje"].strip()

        if not mensaje:
            raise forms.ValidationError(
                "Debes escribir un comentario o sugerencia."
            )

        return mensaje