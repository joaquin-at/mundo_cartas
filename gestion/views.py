from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from registro.models import Perfil

def inicioView(request):
    return render(request, "gestion/index.html")

@login_required
def panel_administrador(request):
    es_administrador = Perfil.objects.filter(
        user=request.user,
        rol__nombre="Administrador",
    ).exists()

    if not es_administrador:
        return redirect("inicio")

    return render(request, "gestion/panel_administrador.html")

@login_required
def mi_perfil(request):
    return render(request, "gestion/mi_perfil.html")