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


class IdentificadoresComentariosField(forms.Field):
    widget = forms.SelectMultiple

    def to_python(self, value):
        valores = value or []
        if len(valores) > 20:
            raise forms.ValidationError("Selecciona como máximo 20 mensajes por operación.")
        campo = forms.IntegerField(min_value=1, max_value=9223372036854775807)
        try:
            return list(dict.fromkeys(campo.clean(valor) for valor in valores))
        except forms.ValidationError:
            raise forms.ValidationError("La selección contiene un identificador inválido.")


class SeleccionComentariosForm(forms.Form):
    ids = IdentificadoresComentariosField(
        error_messages={"required": "Debes seleccionar al menos un mensaje."}
    )


class EliminarComentariosForm(SeleccionComentariosForm):
    confirmar = forms.BooleanField(
        error_messages={"required": "Confirma la eliminación definitiva de los mensajes archivados."}
    )


class RespuestaComentarioForm(forms.ModelForm):
    respuesta = forms.CharField(
        label="Respuesta para el jugador",
        max_length=1000,
        widget=forms.Textarea(attrs={
            "rows": 6, "maxlength": 1000,
            "placeholder": "Escribe una respuesta clara para el jugador…",
        }),
        error_messages={"required": "Escribe una respuesta antes de enviarla."},
    )

    class Meta:
        model = ComentarioSugerencia
        fields = ["respuesta"]


class ConfirmarAccionJugadorForm(forms.Form):
    confirmar = forms.BooleanField(
        label="Confirmo esta acción",
        error_messages={"required": "Debes confirmar la acción para continuar."},
    )


class SolicitudDesactivacionForm(ConfirmarAccionJugadorForm):
    field_order = ["motivo", "confirmar"]
    motivo = forms.CharField(
        label="Motivo (opcional)",
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": 500}),
    )
