# Mundo Cartas

Aplicación con Django y SQLite para administrar juegos, torneos y usuarios.

## Funciones

- Registro, inicio y cierre de sesión con roles Jugador y Administrador.
- Catálogo de juegos con imágenes y búsqueda; gestión de juegos y torneos.
- Edición del nombre, apellidos y correo del usuario conectado.

Pendientes: clasificación, inscripciones, historial, puntos y administración de ligas.

## Requisitos

Python 3.12, Git y Pipenv. Si no tienes Pipenv:

```powershell
py -m pip install pipenv
```

## Instalación

Comandos para PowerShell en Windows.

### 1. Clonar e instalar dependencias

```powershell
git clone https://github.com/joaquin-at/mundo_cartas.git
cd mundo_cartas
pipenv sync
```

Ejecuta los siguientes comandos desde la carpeta que contiene `manage.py`.

### 2. Configurar el entorno

Si todavía no tienes `.env`, créalo desde el ejemplo:

```powershell
Copy-Item .env.example .env
```

Genera una clave:

```powershell
pipenv run python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Completa `.env` con el resultado y habilita el modo de desarrollo local:

```dotenv
SECRET_KEY=pega_aqui_la_clave_generada
DEBUG=True
```

### 3. Crear la base de datos y el administrador

```powershell
pipenv run python manage.py migrate
pipenv run python manage.py createsuperuser
```

Las migraciones también precargan los nueve juegos. El superusuario accede a `/admin/`; para usar el panel de Mundo Cartas, asígnale el rol `Administrador`:

```powershell
pipenv run python manage.py shell
```

En la consola de Python, reemplaza `TU_USUARIO` por el nombre creado:

```python
from django.contrib.auth import get_user_model
from registro.models import Perfil, Rol

usuario = get_user_model().objects.get(username="TU_USUARIO")
rol, _ = Rol.objects.get_or_create(nombre="Administrador")
Perfil.objects.update_or_create(user=usuario, defaults={"rol": rol})
exit()
```

Las cuentas del registro público reciben el rol `Jugador`.

### 4. Iniciar la aplicación

```powershell
pipenv run python manage.py check
pipenv run python manage.py runserver
```

Abre `http://127.0.0.1:8000/`. Detén el servidor con `Ctrl + C`.

## Estructura

- `mundoCartas/`: configuración y rutas generales.
- `gestion/`: vistas públicas, perfil y plantillas compartidas.
- `registro/`: autenticación, formularios de usuario y roles.
- `torneo/`: modelos y administración de juegos y torneos.

Git excluye `.env`, `db.sqlite3`, `media/`, `__pycache__/` y `*.pyc`. Cada integrante mantiene su configuración, base de datos e imágenes subidas en su equipo.