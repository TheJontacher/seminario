# Sistema de control de servicios

Guía para preparar y ejecutar el proyecto en una computadora nueva con Windows.

## Requisitos

Instala estas herramientas antes de continuar:

- **Git:** https://git-scm.com/downloads
- **Python 3.10 o superior:** https://www.python.org/downloads/
- **Docker Desktop:** https://www.docker.com/products/docker-desktop/

Durante la instalación de Python, habilita la opción **Add Python to PATH**. Al terminar, abre Docker Desktop y espera a que indique que está iniciado.

## Descargar el proyecto

Abre PowerShell y ejecuta:

```powershell
git clone https://github.com/TheJontacher/seminario.git
cd seminario
```

## Configurar el entorno

Crea el entorno virtual e instala las dependencias:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Crea el archivo local de variables de entorno:

```powershell
Copy-Item .env.example .env
```

`.env` contiene valores solo para desarrollo local y no se debe subir al repositorio.

## Iniciar PostgreSQL

Con Docker Desktop iniciado, ejecuta:

```powershell
docker compose up -d postgres
docker compose ps
```

Espera a que el contenedor aparezca como `Up`. Confirma que PostgreSQL ya acepta conexiones:

```powershell
docker compose exec postgres pg_isready -U postgres -d taller
```

Si todavía no está listo, repite `pg_isready` después de unos segundos.

## Preparar y ejecutar Django

Aplica las migraciones, crea un usuario de acceso y arranca el servidor:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

`createsuperuser` solicitará nombre de usuario y contraseña. No muestra los caracteres de la contraseña mientras se escribe.

Abre la aplicación en:

```text
http://127.0.0.1:8000/
```

El acceso administrativo está en:

```text
http://127.0.0.1:8000/admin/
```

## Detener y volver a iniciar

Para detener Django, vuelve a la terminal del servidor y presiona `Ctrl+C`. Para detener PostgreSQL conservando la base de datos:

```powershell
docker compose down
```

En el siguiente uso, vuelve a iniciar PostgreSQL con `docker compose up -d postgres` y luego ejecuta `runserver`. Los datos persisten en un volumen local de Docker. **No uses `docker compose down -v`** salvo que quieras borrar ese volumen y todos sus datos.

## Datos en otras computadoras

Git descarga el código, pero no copia los datos de PostgreSQL ni los usuarios creados en otra computadora. Cada instalación tiene su propia base de datos y debe crear su propio superusuario. Para compartir registros existentes, se necesita exportar e importar un respaldo de PostgreSQL por separado.

## Solución rápida de problemas

- Si PowerShell no reconoce `docker`, inicia Docker Desktop y abre una terminal nueva.
- Si el puerto `5432` está ocupado, PostgreSQL no podrá iniciar; cierra el servicio que lo usa antes de continuar.
- Si `py` no se reconoce, reinstala Python activando **Add Python to PATH**.