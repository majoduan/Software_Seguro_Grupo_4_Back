# 🐳 Guía Docker - Backend Software Seguro

Esta guía explica cómo levantar el backend localmente usando Docker con PostgreSQL en contenedor.

## 📋 Prerequisitos

- Docker Desktop instalado y ejecutándose
- Docker Compose (incluido en Docker Desktop)

## 🚀 Inicio Rápido

### 1. Levantar los servicios

```bash
# Con archivo .env.local (desarrollo local - recomendado)
docker-compose --env-file .env.local up --build

# O con .env por defecto (usa NEON)
docker-compose up --build
```

El flag `--build` reconstruye la imagen. Úsalo la primera vez o después de cambios en dependencias.

### 2. Verificar que todo funciona

Los servicios deberían estar disponibles en:

- **Backend API**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Documentación API**: http://localhost:8000/docs

### 3. Detener los servicios

```bash
# Detener y eliminar contenedores
docker-compose down

# Detener, eliminar contenedores Y volúmenes (⚠️ elimina la base de datos)
docker-compose down -v
```

## 📁 Configuración de Archivos

### `.env.local` (Desarrollo Local)

```env
# PostgreSQL local en Docker
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=fastapidb
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/fastapidb

# Sin SSL para desarrollo local
COOKIE_SECURE=false
```

### `.env` (Producción/NEON)

```env
# NEON cloud database con SSL
DATABASE_URL=postgresql+asyncpg://user:pass@host.neon.tech/db?sslmode=require&channel_binding=require

# SSL habilitado para producción
COOKIE_SECURE=true
```

## 🔧 Comandos Útiles

### Ver logs en tiempo real

```bash
# Todos los servicios
docker-compose logs -f

# Solo el backend
docker-compose logs -f web

# Solo la base de datos
docker-compose logs -f db
```

### Entrar a los contenedores

```bash
# Acceder al contenedor del backend
docker-compose exec web bash

# Acceder a PostgreSQL
docker-compose exec db psql -U postgres -d fastapidb
```

### Ejecutar migraciones manualmente

```bash
# Las migraciones se ejecutan automáticamente al iniciar
# Pero si necesitas ejecutarlas manualmente:
docker-compose exec web alembic upgrade head

# Revertir última migración
docker-compose exec web alembic downgrade -1

# Ver historial de migraciones
docker-compose exec web alembic history
```

### Verificar estado de la base de datos

```bash
# Verificar que PostgreSQL está listo
docker-compose exec db pg_isready -U postgres

# Ver bases de datos
docker-compose exec db psql -U postgres -c "\l"

# Ver tablas en la base de datos
docker-compose exec db psql -U postgres -d fastapidb -c "\dt"
```

## 🔄 Workflow de Desarrollo

### Desarrollo Local con Hot Reload

El volumen montado en `docker-compose.yml` permite que los cambios en el código se reflejen automáticamente:

```yaml
volumes:
  - .:/app # Sincroniza tu código local con el contenedor
```

Simplemente edita los archivos y Uvicorn recargará automáticamente.

### Cambiar entre Local y NEON

**Para desarrollo local:**

```bash
docker-compose --env-file .env.local up
```

**Para probar con NEON:**

```bash
docker-compose --env-file .env up
```

El código en `app/database.py` detecta automáticamente si necesita SSL basándose en la URL.

## 🐛 Troubleshooting

### Puerto 5432 ya está en uso

Si tienes PostgreSQL instalado localmente:

```bash
# Detener PostgreSQL local
# Windows (en Services)
net stop postgresql-x64-15

# O cambiar el puerto en docker-compose.yml
ports:
  - "5433:5432"  # Usa puerto 5433 externamente
```

### Error "database does not exist"

```bash
# Recrear la base de datos
docker-compose down -v
docker-compose --env-file .env.local up --build
```

### Migraciones no se ejecutan

```bash
# Ver logs del contenedor web
docker-compose logs web

# Ejecutar migraciones manualmente
docker-compose exec web alembic upgrade head
```

### Contenedor sale inmediatamente

```bash
# Ver por qué falló
docker-compose logs web

# Revisar variables de entorno
docker-compose --env-file .env.local config
```

## 📊 Estructura de Servicios

```mermaid
graph LR
    A[docker-compose.yml] --> B[Servicio: db]
    A --> C[Servicio: web]
    B --> D[PostgreSQL 15]
    C --> E[FastAPI + Uvicorn]
    C --> B
    D --> F[Puerto 5432]
    E --> G[Puerto 8000]
```

## 🔐 Seguridad

- ⚠️ **NUNCA** commitees `.env.local` al repositorio
- ✅ Ya está en `.gitignore` como `.env.*`
- ✅ Usa credenciales fuertes en producción
- ✅ Las credenciales de desarrollo local son solo para desarrollo local

## 📝 Notas Importantes

1. **Migraciones automáticas**: El `Dockerfile` ejecuta `alembic upgrade head` automáticamente al iniciar
2. **Health checks**: El servicio `web` espera a que `db` esté listo antes de iniciar
3. **Persistencia de datos**: Los datos de PostgreSQL persisten entre reinicios (hasta ejecutar `down -v`)
4. **SSL inteligente**: El código detecta automáticamente si usar SSL según la URL de conexión

## 🆘 ¿Necesitas ayuda?

Revisa los logs primero:

```bash
docker-compose logs -f
```

O contacta al equipo de desarrollo.
