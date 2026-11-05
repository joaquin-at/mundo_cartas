from django.shortcuts import render

# Create your views here.

def inicioView(request):
    return render(request, 'gestion/index.html')


