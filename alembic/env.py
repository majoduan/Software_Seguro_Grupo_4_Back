from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context
from dotenv import load_dotenv
import os
import sys

# Cargar variables del .env
""""Cargar las variables de entorno desde el archivo .env para la configuración de la base 
de datos.Esto permite que Alembic use las credenciales y la URL de conexión definidas en el 
archivo .env."""

load_dotenv()

# Configuración de Alembic
config = context.config
fileConfig(config.config_file_name)

# Agregar la ruta del proyecto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Importar Base y modelos
"""Importar la clase Base y los modelos de la aplicación para que Alembic pueda acceder 
a ellos.Esto es necesario para que Alembic pueda generar las migraciones basadas en los 
modelos definidos."""

from app.database import Base
from app.models import (
    TipoPOA,
    TipoProyecto,
    Usuario,
    Proyecto,
    EstadoProyecto,
    EstadoPOA,
    Periodo,
    Rol,
    LimiteProyectosTipo,
    Poa,
    ItemPresupuestario,
    DetalleTarea,
    TipoPoaDetalleTarea,
    LimiteActividadesTipoPoa,
    Actividad,
    Tarea,
    Permiso,
    PermisoRol,
    ReformaPoa,
    ControlPresupuestario,
    EjecucionPresupuestaria,
    HistoricoProyecto,
    HistoricoPoa,
)

# Asignar metadata de los modelos
target_metadata = Base.metadata

# 🔒 Obtener URL de base de datos desde variables de entorno
# En desarrollo local: usa DATABASE_URL del .env
# En producción (Render): usa DATABASE_URL inyectada por Render
database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/fastapidb")

# Convertir URL de asyncpg a psycopg2 (Alembic requiere driver síncrono)
# Render usa: postgresql+asyncpg://...?sslmode=require&channel_binding=require
# Alembic necesita: postgresql://...
if database_url.startswith("postgresql+asyncpg://"):
    # Reemplazar asyncpg por psycopg2
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    # Remover parámetros de asyncpg que psycopg2 no soporta
    # channel_binding=require no es compatible con psycopg2
    database_url = database_url.replace("&channel_binding=require", "")
    database_url = database_url.replace("channel_binding=require&", "")
    database_url = database_url.replace("?channel_binding=require", "")

url = database_url


def run_migrations_offline():
    """Ejecutar migraciones en modo offline"""
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Ejecutar migraciones en modo online"""
    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
