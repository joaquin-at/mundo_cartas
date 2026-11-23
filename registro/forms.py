from django import forms
from django.contrib.auth.forms import UserCreationForm, UsernameField
from django.contrib.auth.models import User
from django.db import transaction
import re
import unicodedata
from .models import Perfil


class NombrePersonaField(forms.CharField):
    def to_python(self, value):
        nombre = unicodedata.normalize("NFC", super().to_python(value))
        nombre = " ".join(nombre.split())
        if nombre and (
            not any(letra.isalpha() for letra in nombre)
            or any(not letra.isalpha() and letra not in " -'’." for letra in nombre)
        ):
            raise forms.ValidationError("Escribe un nombre válido, sin números ni símbolos especiales.")
        return nombre


class TelefonoField(forms.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label", "Teléfono")
        kwargs.setdefault("max_length", 40)
        kwargs.setdefault("help_text", "Ej.: +56 9 1234 5678. Entre 8 y 15 dígitos.")
        kwargs.setdefault("widget", forms.TextInput(attrs={
            "type": "tel", "autocomplete": "tel", "inputmode": "tel", "placeholder": "+56 9 1234 5678",
        }))
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        telefono = super().to_python(value)
        if not telefono:
            return ""
        if len(telefono) > 40 or not re.fullmatch(r"\+?[0-9 ()\.\-]+", telefono):
            raise forms.ValidationError("Escribe un teléfono válido; usa números y un prefijo + opcional.")
        digitos = re.sub(r"[^0-9]", "", telefono)
        if not 8 <= len(digitos) <= 15 or set(digitos) == {"0"}:
            raise forms.ValidationError("El teléfono debe contener entre 8 y 15 dígitos válidos.")
        return ("+" if telefono.startswith("+") else "") + digitos


class CustomUserCreationForm(UserCreationForm):
    first_name = NombrePersonaField(
        label="Nombre", max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "given-name"}),
    )
    last_name = NombrePersonaField(
        label="Apellidos (opcional)", max_length=150, required=False,
        widget=forms.TextInput(attrs={"autocomplete": "family-name"}),
    )
    telefono = TelefonoField()
    email = forms.EmailField(
        label="Correo electrónico",
        required=True,
    )

    class Meta:
        model = User
        field_classes = {"username": UsernameField}
        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
            "telefono",
            "password1",
            "password2",
        ]
        labels = {
            "username": "Nombre de usuario",
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Ya existe una cuenta con este correo electrónico."
            )

        return email

    def clean_password1(self):
        password = self.cleaned_data["password1"]
        if not password.strip():
            raise forms.ValidationError("La contraseña no puede contener solo espacios.")
        return password

    def clean_password2(self):
        password = self.cleaned_data["password2"]
        if not password.strip():
            raise forms.ValidationError("La confirmación no puede contener solo espacios.")
        return password


class PerfilUsuarioForm(forms.ModelForm):
    first_name = NombrePersonaField(
        label="Nombre", max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "given-name"}),
    )
    last_name = NombrePersonaField(
        label="Apellidos (opcional)", max_length=150, required=False,
        widget=forms.TextInput(attrs={"autocomplete": "family-name"}),
    )
    telefono = TelefonoField()
    email = forms.EmailField(label="Correo electrónico", required=True)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "telefono"]
        field_classes = {"username": UsernameField}
        labels = {"username": "Nombre de usuario"}
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = "Se usa para iniciar sesión. Si lo cambias, utiliza el nombre nuevo la próxima vez."
        if self.instance.pk:
            perfil = getattr(self.instance, "perfil", None)
            self.initial.setdefault("telefono", perfil.telefono if perfil else "")

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe una cuenta con este nombre de usuario.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        otros = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if otros.exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo electrónico.")
        return email

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if commit:
            with transaction.atomic():
                usuario.save()
                perfil, _ = Perfil.objects.get_or_create(user=usuario)
                perfil.telefono = self.cleaned_data["telefono"]
                perfil.save(update_fields=["telefono"])
        return usuario


class FotoPerfilForm(forms.ModelForm):
    quitar_foto = forms.BooleanField(label="Quitar mi foto actual", required=False)

    class Meta:
        model = Perfil
        fields = ["foto"]
        labels = {"foto": "Selecciona una foto"}
        widgets = {
            "foto": forms.FileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        }

    def clean_foto(self):
        foto = self.cleaned_data.get("foto")
        if not self.files.get("foto"):
            return foto
        if foto.size > 2 * 1024 * 1024:
            raise forms.ValidationError("La foto debe pesar como máximo 2 MB.")
        if foto.image.format not in ("JPEG", "PNG", "WEBP"):
            raise forms.ValidationError("Selecciona una imagen JPG, PNG o WEBP.")
        if foto.image.width > 4096 or foto.image.height > 4096:
            raise forms.ValidationError("La foto no puede superar los 4096 píxeles de ancho o alto.")
        return foto

    def clean(self):
        datos = super().clean()
        nueva_foto = self.files.get("foto")
        quitar = datos.get("quitar_foto")
        if nueva_foto and quitar:
            raise forms.ValidationError("Elige una nueva foto o quita la actual, pero no ambas opciones.")
        if not nueva_foto and not quitar:
            raise forms.ValidationError("Selecciona una foto o marca la opción de quitar la actual.")
        return datos
