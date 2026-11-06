from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from django.shortcuts import redirect, render

from .forms import CustomUserCreationForm
from .models import Perfil


def registrar_usuario(request):
    if request.user.is_authenticated:
        return redirect("inicio")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                Perfil.objects.create(user=user)

            return redirect("iniciar_sesion")
    else:
        form = CustomUserCreationForm()

    return render(
        request,
        "registro/registrar_usuario.html",
        {"form": form},
    )


def iniciar_sesion(request):
    if request.user.is_authenticated:
        return redirect("inicio")

    if request.method == "POST":
        form = AuthenticationForm(
            request=request,
            data=request.POST,
        )

        if form.is_valid():
            user = form.get_user()
            Perfil.objects.get_or_create(user=user)
            login(request, user)

            return redirect("inicio")
    else:
        form = AuthenticationForm(request=request)

    return render(
        request,
        "registro/iniciar_sesion.html",
        {"form": form},
    )
