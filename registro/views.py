from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

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
        es_administrador = Perfil.objects.filter(
            user=request.user,
            rol__nombre="Administrador"
        ).exists()

        if es_administrador:
            return redirect("panel_administrador")

        return redirect("inicio")

    if request.method == "POST":
        form = AuthenticationForm(
            request=request,
            data=request.POST,
        )

        if form.is_valid():
            user = form.get_user()

            perfil, creado = Perfil.objects.get_or_create(
                user=user
            )

            login(request, user)

            if perfil.rol.nombre == "Administrador":
                return redirect("panel_administrador")

            return redirect("inicio")
    else:
        form = AuthenticationForm(request=request)

    return render(request,"registro/iniciar_sesion.html",
    {"form": form},
)



@require_POST
def cerrar_sesion(request):
    logout(request)
    return redirect("inicio")