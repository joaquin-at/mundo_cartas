from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render

from .models import Perfil


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
