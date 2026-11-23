from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST, require_http_methods
from django.utils.http import url_has_allowed_host_and_scheme

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
                Perfil.objects.create(user=user, telefono=form.cleaned_data["telefono"])

            return redirect("iniciar_sesion")
    else:
        form = CustomUserCreationForm()

    return render(
        request,
        "registro/registrar_usuario.html",
        {"form": form},
    )



@require_http_methods(["GET", "POST"])
def iniciar_sesion(request):
    siguiente = request.POST.get("next") or request.GET.get("next", "")
    if not url_has_allowed_host_and_scheme(
        siguiente,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        siguiente = ""

    if request.user.is_authenticated:
        if siguiente:
            return redirect(siguiente)
        es_administrador = Perfil.objects.filter(
            user=request.user,
            rol__nombre="Administrador",
        ).exists()
        if es_administrador:
            return redirect("panel_administrador")
        return redirect("inicio")

    if request.method == "POST":
        form = AuthenticationForm(request=request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            perfil, _ = Perfil.objects.get_or_create(user=user)
            login(request, user)
            if siguiente:
                return redirect(siguiente)
            if perfil.rol.nombre == "Administrador":
                return redirect("panel_administrador")
            return redirect("inicio")
    else:
        form = AuthenticationForm(request=request)

    return render(request, "registro/iniciar_sesion.html", {
        "form": form,
        "siguiente": siguiente,
    })


@require_POST
def cerrar_sesion(request):
    logout(request)
    return redirect("inicio")
