from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import ssl

"""
Configuración del motor de base de datos asíncrono con cifrado SSL
Objetivo:
    Establecer una conexión segura y asíncrona con la base de datos PostgreSQL
    utilizando SQLAlchemy y SSL. Esta configuración garantiza la confidencialidad
    e integridad de los datos transmitidos entre la aplicación y el servidor de base de datos.

Parámetros:
    DATABASE_URL (str): Cadena de conexión obtenida desde las variables de entorno. 
    Contiene las credenciales y dirección del servidor.
    ssl_context (ssl.SSLContext): Contexto SSL predeterminado que configura parámetros 
    seguros para la conexión.

Operación:
    - Obtiene la URL de conexión desde el entorno del sistema.
    - Elimina parámetros innecesarios de la URL para evitar conflictos con `connect_args`.
    - Crea un contexto SSL seguro utilizando la configuración predeterminada de Python.
    - Inicializa un motor de base de datos asíncrono (`create_async_engine`) usando el contexto SSL.
    - Configura la sesión local (`SessionLocal`) para el manejo de transacciones asincrónicas 
    con SQLAlchemy.

Retorna:
    - engine (AsyncEngine): Motor asíncrono configurado con conexión cifrada.
    - SessionLocal (sessionmaker).
"""

DATABASE_URL = os.getenv("DATABASE_URL")

# Detectar si la URL requiere SSL (NEON/producción) o no (local/Docker)
# NEON usa URLs con parámetros SSL en la cadena de conexión
requires_ssl = "sslmode=require" in DATABASE_URL or "neon.tech" in DATABASE_URL

# Limpiar parámetros SSL de la URL si existen
clean_url = DATABASE_URL.replace("?sslmode=require&channel_binding=require", "")

# Configurar connect_args según si se requiere SSL
if requires_ssl:
    ssl_context = ssl.create_default_context()
    connect_args = {"ssl": ssl_context}
else:
    connect_args = {}

engine = create_async_engine(
    clean_url,
    echo=True,
    connect_args=connect_args
)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

"""
Obtener una sesión de base de datos asíncrona

Objetivo:
    Proveer una sesión de base de datos asincrónica a las rutas o servicios que la requieran,
    garantizando el manejo adecuado de recursos y el uso del motor previamente configurado con 
    seguridad SSL.

Parámetros:
    No recibe parámetros directamente. Utiliza la configuración de `SessionLocal` previamente 
    definida.

Operación:
    - Crea una sesión utilizando `SessionLocal`.
    - Utiliza `async with` para garantizar la liberación de recursos tras finalizar la operación.
    - Utiliza `yield` para permitir la inyección de dependencias en frameworks asincrónicos.

Retorna:
    - AsyncSession: Sesión de base de datos con soporte para operaciones asincrónicas.
"""

async def get_db():
    async with SessionLocal() as session:
        yield session