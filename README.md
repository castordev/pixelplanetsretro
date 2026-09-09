# Pixel Planets

Una aplicación web de Django para explorar y visualizar órbitas de planetas con astronomía avanzada.

## 🚀 Inicio Rápido

### Requisitos previos
- Python 3.14+ (o cualquier versión compatible con Django 6.0)
- pip (gestor de paquetes de Python)
- Git

### 1. Clonar el repositorio

```bash
git clone <URL-DEL-REPOSITORIO>
cd pixelplanetsretro
```

### 2. Crear un entorno virtual (recomendado)

#### En Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

#### En macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar la base de datos

```bash
python manage.py migrate
```

### 5. Crear un superusuario (administrador) - Opcional

```bash
python manage.py createsuperuser
```

Esto te pedirá que ingreses un nombre de usuario, email y contraseña.

### 6. Iniciar el servidor de desarrollo

```bash
python manage.py runserver
```

La aplicación estará disponible en: **http://localhost:8000**

El panel de administración está en: **http://localhost:8000/admin**

## 📁 Estructura del Proyecto

```
pixelplanetsretro/
├── manage.py                 # Script de administración de Django
├── requirements.txt          # Dependencias del proyecto
├── planets_web/              # Configuración principal
│   ├── settings.py           # Configuración de Django
│   ├── urls.py               # URLs principales
│   ├── wsgi.py               # WSGI para producción
│   └── asgi.py               # ASGI para Vercel
├── planets/                  # App principal
│   ├── models.py             # Modelos de datos
│   ├── views.py              # Vistas
│   ├── urls.py               # URLs de la app
│   ├── templates/            # Archivos HTML
│   └── static/               # CSS, JS, imágenes
└── db.sqlite3                # Base de datos SQLite (local)
```

## 🛠️ Tecnologías Utilizadas

- **Django 6.0** - Framework web
- **Skyfield** - Astronomía y cálculos orbitales
- **Astroquery** - Consultas astronómicas
- **NumPy** - Cálculos numéricos
- **WhiteNoise** - Servir archivos estáticos
- **Django Browser Reload** - Recarga automática en desarrollo

## ⚙️ Configuración Avanzada

### Variables de Entorno

Puedes crear un archivo `.env` en la raíz del proyecto (junto a `manage.py`) para configurar:

```env
DJANGO_DEBUG=1
DJANGO_SECRET_KEY=tu-clave-secreta-aqui
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

Ver `.env.example` para más detalles.

### Descargar datos de efemérides (en despliegue)

El script `build_files.sh` descarga automáticamente los datos de efemérides de Skyfield durante el despliegue en Vercel.

## 📝 Comandos Útiles

```bash
# Crear migraciones
python manage.py makemigrations

# Ver estado de migraciones
python manage.py showmigrations

# Shell interactivo de Django
python manage.py shell

# Recopilar archivos estáticos (producción)
python manage.py collectstatic

# Ejecutar tests
python manage.py test
```

## 🌐 Despliegue

La aplicación está configurada para desplegarse en **Vercel** (ver `vercel.json`).

### Pasos para desplegar en Vercel:

1. Conecta tu repositorio a Vercel
2. Configura las variables de entorno en el dashboard de Vercel
3. Vercel ejecutará automáticamente `build_files.sh` y migraciones

## 📞 Soporte

Si encuentras problemas:

1. Verifica que Python 3.14+ esté instalado: `python --version`
2. Asegúrate de estar en el entorno virtual activado
3. Reinstala dependencias: `pip install -r requirements.txt --upgrade`
4. Recrea la base de datos: `rm db.sqlite3 && python manage.py migrate`

## 📄 Licencia

MIT
