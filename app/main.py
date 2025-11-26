from datetime import datetime,timezone,timedelta
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException,UploadFile, File, Form, Body, Query, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app import models, schemas, auth
from app.database import engine, get_db
from app.middlewares import add_middlewares
from app.scripts.init_data import seed_all_data
from app.auth import COOKIE_SECURE, COOKIE_SAMESITE, COOKIE_HTTPONLY, get_current_user
from app.business_validators import (
    validate_proyecto_business_rules,
    validate_poa_business_rules,
    validate_periodo_business_rules,
    validate_tarea_business_rules,
    validate_usuario_business_rules,
    validate_programacion_mensual_business_rules
)
from passlib.context import CryptContext
import uuid
from typing import List
from dateutil.relativedelta import relativedelta
import re
from fastapi.responses import JSONResponse, StreamingResponse
from app.scripts.transformador_excel import transformar_excel
from app.utils import eliminar_tareas_y_actividades
import io
import pandas as pd
import xlsxwriter
from sqlalchemy import func, delete

from reportlab.lib.pagesizes import letter,landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.styles import ParagraphStyle
import unicodedata
from sqlalchemy.orm import selectinload

"""Inicializar el contexto de hashing de contraseñas
Objetivo:
    Configurar un contexto seguro para el almacenamiento de contraseñas utilizando el 
    algoritmo bcrypt,garantizando que las contraseñas se almacenen de forma cifrada y no reversible.

Parámetros:
    schemes (list): Lista de algoritmos de hashing permitidos. En este caso, solo 'bcrypt'.
    deprecated (str): Define cómo manejar algoritmos obsoletos. 'auto' utiliza el algoritmo 
    más seguro disponible.

Operación:
    - Crea una instancia de CryptContext para hashear y verificar contraseñas.
    - Se utiliza posteriormente en los procesos de registro y autenticación.

Retorna:
    - CryptContext: Objeto utilizado para operaciones de hash y verificación de contraseñas.
"""
# Initialize the password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()
#middlewares
# CORS middleware
add_middlewares(app)

# Manejador global de excepciones para asegurar que CORS headers se envíen siempre
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Manejador global de HTTPException que asegura que las cabeceras CORS
    se envíen incluso cuando hay errores de autenticación o autorización.
    """
    # Obtener el origen de la petición
    origin = request.headers.get("origin")

    # Headers CORS que siempre deben estar presentes
    cors_headers = {}

    # Solo añadir CORS headers si el origen está permitido
    allowed_origins = ["https://software-seguro-grupo-4-front.vercel.app"]
    if origin in allowed_origins:
        cors_headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Accept, Content-Type, Authorization, Cookie, X-Requested-With",
        }

    # Combinar headers de CORS con headers existentes de la excepción
    response_headers = {**cors_headers, **(exc.headers if exc.headers else {})}

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=response_headers
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Manejador global de excepciones generales para evitar errores 500 sin CORS headers.
    """
    # Obtener el origen de la petición
    origin = request.headers.get("origin")

    # Headers CORS que siempre deben estar presentes
    cors_headers = {}

    # Solo añadir CORS headers si el origen está permitido
    allowed_origins = ["https://software-seguro-grupo-4-front.vercel.app"]
    if origin in allowed_origins:
        cors_headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Accept, Content-Type, Authorization, Cookie, X-Requested-With",
        }

    return JSONResponse(
        status_code=500,
        content={"detail": f"Error interno del servidor: {str(exc)}"},
        headers=cors_headers
    )

def quitar_tildes(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

def normalizar_texto(texto):
    # Quita tildes, pasa a minúsculas, elimina espacios extra y números
    texto = quitar_tildes(texto).lower()
    texto = re.sub(r'\d+', '', texto)         # Elimina todos los números
    texto = re.sub(r'\s+', ' ', texto)        # Reemplaza múltiples espacios por uno solo
    texto = texto.strip()                     # Quita espacios al inicio y final
    return texto

@app.get("/")
async def root():
    return {"message": "Backend activo en Render"}

@app.on_event("startup")
async def on_startup():

    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

    # llenar la base de datos con datos iniciales
    print("Insertando roles iniciales...")
    await seed_all_data()

# Endpoint de inicio de sesión (autenticación con token JWT cifrado)
"""Autenticar usuario y generar token JWT cifrado (login)
Objetivo:
    Validar las credenciales del usuario, verificar su estado y generar un token JWT
    cifrado para su uso en autenticación basada en cookies seguras.

Parámetros:
    response (Response): Objeto de respuesta HTTP donde se insertará la cookie.
    form_data (OAuth2PasswordRequestForm): Datos del formulario con username (email) y password.
    db (AsyncSession): Conexión a la base de datos para obtener datos del usuario.

Operación:
    - Verifica si el usuario existe y si la contraseña ingresada coincide con el hash almacenado.
    - Verifica si el usuario está activo.
    - Genera un token JWT cifrado con identificadores del usuario.
    - Inserta el token en una cookie segura (httponly, secure, samesite).

Retorna:
    - dict: Respuesta con un token dummy. El token real es enviado por cookie segura.
"""
# Modificar el endpoint /login
@app.post("/login", response_model=schemas.Token)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(models.Usuario).filter(models.Usuario.email == form_data.username)
    )
    usuario = result.scalars().first()
    
    if not usuario or not auth.verificar_password(form_data.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    if not usuario.activo:
        raise HTTPException(status_code=403, detail="Usuario inactivo")
    
    # 🔧 NUEVO: Crear token JWT cifrado
    encrypted_token = auth.crear_token_cifrado(
        data={"sub": str(usuario.id_usuario), "id_rol": str(usuario.id_rol)},
        expires_delta=timedelta(days=7)
    )

    # Configurar cookie segura con token cifrado
    response.set_cookie(
        key="auth_token",
        value=encrypted_token,  # ← Token JWT cifrado (ilegible)
        max_age=7 * 24 * 60 * 60,  # 7 días en segundos (604800)
        httponly=COOKIE_HTTPONLY,
        secure=COOKIE_SECURE,
        # samesite=COOKIE_SAMESITE if COOKIE_SAMESITE in ("lax", "strict", "none") else "lax"
        samesite="none"
    )
    
    return {
        "access_token": "cookie_auth",  # Token dummy para respuesta
        "token_type": "bearer"
    }

#Usar para validar el usuario
"""Autenticación de usuario mediante dependencia

    Objetivo:
        Garantizar que solo usuarios autenticados puedan acceder a las rutas protegidas del sistema.
        Esta dependencia utiliza el token JWT previamente generado y almacenado en el encabezado 
        Authorization para validar la identidad del usuario que realiza la petición.

    Parámetros:
        Ninguno explícito en la función — se invoca automáticamente mediante `Depends`.

    Operación:
        - Extrae el token JWT del encabezado de la solicitud.
        - Verifica su validez y decodifica el contenido.
        - Recupera la información del usuario desde la base de datos utilizando el identificador
        extraído del token.
        - Devuelve una instancia del usuario autenticado para su uso dentro de la ruta protegida.

    Retorna:
        - models.Usuario: Objeto del usuario autenticado.
"""

@app.get("/perfil")
async def perfil_usuario(
    usuario: models.Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 🔧 CORRECCIÓN: Obtener información completa del rol
    result = await db.execute(
        select(models.Rol).filter(models.Rol.id_rol == usuario.id_rol)
    )
    rol = result.scalars().first()
    
    # 🔧 CORRECCIÓN: Retornar estructura que espera el frontend
    return {
        "id": usuario.id_usuario,
        "nombre_usuario": usuario.nombre_usuario,
        "email": usuario.email,
        "id_rol": usuario.id_rol,
        "rol": {
            "id_rol": rol.id_rol,
            "nombre_rol": rol.nombre_rol
        } if rol else None,
        "activo": usuario.activo
    }

#Registro de usuarios con contraseña hasheada
"""Registrar nuevo usuario con almacenamiento seguro de contraseña
Objetivo:
    Crear un nuevo usuario en la base de datos asegurando que su contraseña se almacene 
    mediante un algoritmo de hash seguro.

Parámetros:
    user (schemas.UserCreate): Objeto con los datos del nuevo usuario incluyendo la contraseña.
    db (AsyncSession): Conexión a la base de datos para insertar el nuevo usuario.

Operación:
    - Verifica si ya existe un usuario con el mismo correo.
    - Aplica hashing a la contraseña usando bcrypt antes de almacenarla.
    - Inserta el nuevo usuario con la contraseña hasheada en la base de datos.

Retorna:
    - Usuario creado, con la información definida en el esquema de salida.
"""
@app.post("/register", response_model=schemas.UserOut)
async def register_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Endpoint de registro de usuarios con validaciones completas.

    Validaciones aplicadas (replicadas del frontend):
    - Formato de email válido (Pydantic EmailStr)
    - Nombre de usuario: 3-100 caracteres, solo alfanuméricos (Pydantic + validator)
    - Contraseña: mín 8 caracteres, 1 mayúscula, 1 número (Pydantic + validator)
    - Email único (business validator)
    - Rol existe (business validator)
    """
    # Validar reglas de negocio (email único, rol existe)
    await validate_usuario_business_rules(db, user)

    # Hash de contraseña
    hashed_final = pwd_context.hash(user.password)

    # Crear usuario
    nuevo_usuario = models.Usuario(
        nombre_usuario=user.nombre_usuario,
        email=user.email.lower(),  # Normalizar email a minúsculas
        password_hash=hashed_final,
        id_rol=user.id_rol,
        activo=True,
    )

    db.add(nuevo_usuario)
    await db.commit()
    await db.refresh(nuevo_usuario)
    return nuevo_usuario

#Limpiar cookie

# Endpoint de cierre de sesión (logout)
"""Cerrar sesión eliminando cookie de autenticación segura
Objetivo:
    Eliminar la cookie que contiene el token JWT cifrado para invalidar la sesión del usuario.

Parámetros:
    response (Response): Objeto de respuesta HTTP donde se eliminará la cookie.

Operación:
    - Llama a delete_cookie sobre la clave 'auth_token' con las mismas condiciones de seguridad
    usadas en la creación.

Retorna:
    - dict: Mensaje de confirmación de cierre de sesión.
"""
# Modificar el endpoint /logout
@app.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="auth_token",
        httponly=COOKIE_HTTPONLY,
        secure=COOKIE_SECURE,
        # samesite=COOKIE_SAMESITE if COOKIE_SAMESITE in ("lax", "strict", "none") else "lax"
        samesite="none"
    )
    return {"message": "Logout exitoso"}


#Periodos

@app.post("/periodos/", response_model=schemas.PeriodoOut)
async def crear_periodo(data: schemas.PeriodoCreate, db: AsyncSession = Depends(get_db),usuario: models.Usuario = Depends(get_current_user)):
    """
    Endpoint de creación de periodos con validaciones completas.

    Validaciones aplicadas (replicadas del frontend):
    - codigo_periodo: 3-150 caracteres (Pydantic)
    - nombre_periodo: 5-180 caracteres (Pydantic)
    - fecha_fin > fecha_inicio (Pydantic validator)
    - anio: 4 dígitos si está presente (Pydantic)
    - Código único (business validator)
    - Permisos de rol (Admin o Director de Investigación)
    """
    # Obtener el rol del usuario
    result = await db.execute(select(models.Rol).where(models.Rol.id_rol == usuario.id_rol))
    rol = result.scalars().first()

    if not rol or rol.nombre_rol not in ["Administrador", "Director de Investigacion"]:
        raise HTTPException(status_code=403, detail="No tienes permisos para crear periodos")

    # Validar reglas de negocio (código único)
    await validate_periodo_business_rules(db, data)

    nuevo = models.Periodo(
        id_periodo=uuid.uuid4(),
        codigo_periodo=data.codigo_periodo,
        nombre_periodo=data.nombre_periodo,
        fecha_inicio=data.fecha_inicio,
        fecha_fin=data.fecha_fin,
        anio=data.anio,
        mes=data.mes
    )

    db.add(nuevo)
    await db.commit()
    await db.refresh(nuevo)

    return nuevo

@app.put("/periodos/{id}", response_model=schemas.PeriodoOut)
async def editar_periodo_completo(
    id: uuid.UUID,
    data: schemas.PeriodoCreate,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    result_rol = await db.execute(select(models.Rol).where(models.Rol.id_rol == usuario.id_rol))
    rol = result_rol.scalars().first()
    if not rol or rol.nombre_rol not in ["Administrador", "Director de Investigacion"]:
        raise HTTPException(status_code=403, detail="No tienes permisos para editar periodos")

    result = await db.execute(select(models.Periodo).where(models.Periodo.id_periodo == id))
    periodo = result.scalars().first()

    if not periodo:
        raise HTTPException(status_code=404, detail="Periodo no encontrado")

    # Reemplazar todos los campos
    periodo.codigo_periodo = data.codigo_periodo
    periodo.nombre_periodo = data.nombre_periodo
    periodo.fecha_inicio = data.fecha_inicio
    periodo.fecha_fin = data.fecha_fin
    periodo.anio = data.anio
    periodo.mes = data.mes

    await db.commit()
    await db.refresh(periodo)
    return periodo

@app.get("/periodos/", response_model=List[schemas.PeriodoOut])
async def listar_periodos(
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    result = await db.execute(select(models.Periodo))
    periodos = result.scalars().all()
    return periodos


@app.get("/periodos/{id}", response_model=schemas.PeriodoOut)
async def obtener_periodo(id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Periodo).where(models.Periodo.id_periodo == id))
    periodo = result.scalars().first()

    if not periodo:
        raise HTTPException(status_code=404, detail="Periodo no encontrado")

    return periodo


#POA

@app.post("/poas/", response_model=schemas.PoaOut)
async def crear_poa(
    data: schemas.PoaCreate,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    """
    Endpoint de creación de POAs con validaciones completas.

    Validaciones aplicadas (replicadas del frontend):
    - codigo_poa: 5-50 caracteres (Pydantic)
    - anio_ejecucion: 4 dígitos (Pydantic)
    - presupuesto_asignado: > 0 (Pydantic)
    - Código único (business validator)
    - Proyecto existe (business validator)
    - Periodo existe (business validator)
    - Tipo POA existe (business validator)
    - No duplicar periodo por proyecto (business validator)
    - Presupuesto <= presupuesto_maximo del tipo POA (business validator)
    - Duración del periodo <= duracion_meses del tipo POA (business validator)
    """
    # Validar todas las reglas de negocio
    await validate_poa_business_rules(db, data)

    # Obtener estado "Ingresado"
    result = await db.execute(select(models.EstadoPOA).where(models.EstadoPOA.nombre == "Ingresado"))
    estado = result.scalars().first()
    if not estado:
        raise HTTPException(status_code=500, detail="Estado 'Ingresado' no está definido en la base de datos")

    # Crear POA
    nuevo_poa = models.Poa(
        id_poa=uuid.uuid4(),
        id_proyecto=data.id_proyecto,
        id_periodo=data.id_periodo,
        codigo_poa=data.codigo_poa,
        fecha_creacion=data.fecha_creacion,
        id_estado_poa=estado.id_estado_poa,
        id_tipo_poa=data.id_tipo_poa,
        anio_ejecucion=data.anio_ejecucion,
        presupuesto_asignado=data.presupuesto_asignado
    )
    db.add(nuevo_poa)
    await db.commit()
    await db.refresh(nuevo_poa)

    return nuevo_poa

from dateutil.relativedelta import relativedelta

@app.put("/poas/{id}", response_model=schemas.PoaOut)
async def editar_poa(
    id: uuid.UUID,
    data: schemas.PoaCreate,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    # Verificar que el POA exista
    result = await db.execute(select(models.Poa).where(models.Poa.id_poa == id))
    poa = result.scalars().first()
    if not poa:
        raise HTTPException(status_code=404, detail="POA no encontrado")

    # Verificar existencia del proyecto
    result = await db.execute(select(models.Proyecto).where(models.Proyecto.id_proyecto == data.id_proyecto))
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    # Verificar existencia del periodo
    result = await db.execute(select(models.Periodo).where(models.Periodo.id_periodo == data.id_periodo))
    periodo = result.scalars().first()
    if not periodo:
        raise HTTPException(status_code=404, detail="Periodo no encontrado")
     # Verificar si el nuevo periodo ya está ocupado por otro POA
    if poa.id_periodo != data.id_periodo:
        result = await db.execute(
            select(models.Poa)
            .where(models.Poa.id_periodo == data.id_periodo, models.Poa.id_poa != poa.id_poa)
        )
        otro_poa = result.scalars().first()
        if otro_poa:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe un POA asignado al periodo '{periodo.nombre_periodo}'"
            )
   
    # Verificar existencia del tipo POA
    result = await db.execute(select(models.TipoPOA).where(models.TipoPOA.id_tipo_poa == data.id_tipo_poa))
    tipo_poa = result.scalars().first()

    if not tipo_poa:
        raise HTTPException(status_code=404, detail="Tipo de POA no encontrado")

    # Mejorar el cálculo de la duración del periodo para considerar días también
    diferencia = relativedelta(periodo.fecha_fin, periodo.fecha_inicio)
    duracion_meses = diferencia.months + diferencia.years * 12

    # Si hay días adicionales, considerar como mes adicional si es más de la mitad del mes
    if diferencia.days > 15:
        duracion_meses += 1
    
    if duracion_meses > tipo_poa.duracion_meses:
        raise HTTPException(
            status_code=400,
            detail=f"El periodo '{periodo.nombre_periodo}' tiene una duración de {duracion_meses} meses, " +
                   f"pero el tipo de POA '{tipo_poa.nombre}' permite máximo {tipo_poa.duracion_meses} meses"
        )

    # Estado se mantiene igual que antes
    result = await db.execute(select(models.EstadoPOA).where(models.EstadoPOA.id_estado_poa == data.id_estado_poa))
    estado = result.scalars().first()
    if not estado:
        raise HTTPException(status_code=400, detail="Estado POA no encontrado")

    # Actualizar el POA
    poa.id_proyecto = data.id_proyecto
    poa.id_periodo = data.id_periodo
    poa.codigo_poa = data.codigo_poa
    poa.fecha_creacion = data.fecha_creacion
    poa.id_tipo_poa = data.id_tipo_poa
    poa.id_estado_poa = data.id_estado_poa  # o mantener el actual si no deseas sobreescribir
    poa.anio_ejecucion = data.anio_ejecucion
    poa.presupuesto_asignado = data.presupuesto_asignado

    await db.commit()
    await db.refresh(poa)
    return poa

@app.get("/poas/", response_model=List[schemas.PoaOut])
async def listar_poas(
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    result = await db.execute(select(models.Poa))
    return result.scalars().all()

@app.get("/poas/{id}", response_model=schemas.PoaOut)
async def obtener_poa(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    result = await db.execute(select(models.Poa).where(models.Poa.id_poa == id))
    poa = result.scalars().first()

    if not poa:
        raise HTTPException(status_code=404, detail="POA no encontrado")

    return poa

@app.get("/estados-poa/", response_model=List[schemas.EstadoPoaOut])
async def listar_estados_poa(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.EstadoPOA))
    return result.scalars().all()

@app.get("/tipos-poa/", response_model=List[schemas.TipoPoaOut])
async def listar_tipos_poa(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.TipoPOA))

    return result.scalars().all()

@app.get("/tipos-poa/{id}", response_model=schemas.TipoPoaOut)
async def obtener_tipo_poa(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    result = await db.execute(select(models.TipoPOA).where(models.TipoPOA.id_tipo_poa == id))
    tipo_poa = result.scalars().first()

    if not tipo_poa:
        raise HTTPException(status_code=404, detail="Tipo de POA no encontrado")

    return tipo_poa

@app.post("/periodos/", response_model=schemas.PeriodoOut)
async def crear_periodo(
    data: schemas.PeriodoCreate,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    nuevo = models.Periodo(
        id_periodo=uuid.uuid4(),
        **data.dict()
    )
    db.add(nuevo)
    await db.commit()
    await db.refresh(nuevo)
    return nuevo

@app.put("/periodos/{id}", response_model=schemas.PeriodoOut)
async def editar_periodo(
    id: uuid.UUID,
    data: schemas.PeriodoCreate,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    result = await db.execute(select(models.Periodo).where(models.Periodo.id_periodo == id))
    periodo = result.scalars().first()

    if not periodo:
        raise HTTPException(status_code=404, detail="Periodo no encontrado")

    for key, value in data.dict().items():
        setattr(periodo, key, value)

    await db.commit()
    await db.refresh(periodo)
    return periodo

#Proyecto

@app.post("/proyectos/", response_model=schemas.ProyectoOut)
async def crear_proyecto(
    data: schemas.ProyectoCreate,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    """
    Endpoint de creación de proyectos con validaciones completas.

    Validaciones aplicadas (replicadas del frontend):
    - codigo_proyecto: 5-50 caracteres (Pydantic)
    - titulo: 10-2000 caracteres (Pydantic)
    - id_director_proyecto: 2-8 palabras, solo letras (Pydantic validator)
    - presupuesto_aprobado: > 0 (Pydantic)
    - fecha_fin >= fecha_inicio (Pydantic validator)
    - Fechas de prórroga coherentes (Pydantic validator)
    - Código único (business validator)
    - Tipo proyecto existe (business validator)
    - Estado proyecto existe (business validator)
    - Presupuesto <= presupuesto_maximo del tipo (business validator)
    - Duración <= duracion_meses del tipo (business validator)
    """
    # Validar todas las reglas de negocio
    await validate_proyecto_business_rules(db, data)

    nuevo = models.Proyecto(
        id_proyecto=uuid.uuid4(),
        codigo_proyecto=data.codigo_proyecto,
        titulo=data.titulo,
        id_tipo_proyecto=data.id_tipo_proyecto,
        id_estado_proyecto=data.id_estado_proyecto,
        id_departamento=data.id_departamento,
        id_director_proyecto=data.id_director_proyecto,
        fecha_creacion=data.fecha_creacion,
        fecha_inicio=data.fecha_inicio,
        fecha_fin=data.fecha_fin,
        fecha_prorroga=data.fecha_prorroga,
        fecha_prorroga_inicio=data.fecha_prorroga_inicio,
        fecha_prorroga_fin=data.fecha_prorroga_fin,
        presupuesto_aprobado=data.presupuesto_aprobado
    )

    db.add(nuevo)
    await db.commit()
    await db.refresh(nuevo)
    return nuevo

@app.put("/proyectos/{id}", response_model=schemas.ProyectoOut)
async def editar_proyecto(
    id: uuid.UUID,
    data: schemas.ProyectoCreate,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    """
    Endpoint de edición de proyectos con validaciones completas.

    Validaciones aplicadas (mismas que en creación):
    - Todas las validaciones de Pydantic
    - Validaciones de business rules (permite mismo código si es el mismo proyecto)
    """
    try:
        result = await db.execute(select(models.Proyecto).where(models.Proyecto.id_proyecto == id))
        proyecto = result.scalars().first()

        if not proyecto:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Validar todas las reglas de negocio (pasando el ID para excluir en validación de código único)
        await validate_proyecto_business_rules(db, data, proyecto_id=str(id))

        # Validar tipo y estado (redundante pero mantenido para compatibilidad)
        tipo = await db.execute(select(models.TipoProyecto).where(models.TipoProyecto.id_tipo_proyecto == data.id_tipo_proyecto))
        if not tipo.scalars().first():
            raise HTTPException(status_code=404, detail="Tipo de proyecto no encontrado")
 
        estado = await db.execute(select(models.EstadoProyecto).where(models.EstadoProyecto.id_estado_proyecto == data.id_estado_proyecto))
        if not estado.scalars().first():
            raise HTTPException(status_code=404, detail="Estado de proyecto no encontrado")
 
        # Campos a auditar
        campos_auditar = [
            "codigo_proyecto", "titulo", "id_tipo_proyecto", "id_estado_proyecto",
            "id_departamento", "fecha_creacion", "fecha_inicio", "fecha_fin", "fecha_prorroga",
            "fecha_prorroga_inicio", "fecha_prorroga_fin", "presupuesto_aprobado",
            "id_director_proyecto"
        ]
 
        for campo in campos_auditar:
            if not hasattr(data, campo):
                continue
 
            valor_anterior = getattr(proyecto, campo)
            valor_nuevo = getattr(data, campo)
 
            if valor_anterior != valor_nuevo:
                historico = models.HistoricoProyecto(
                    id_historico=uuid.uuid4(),
                    id_proyecto=proyecto.id_proyecto,
                    id_usuario=usuario.id_usuario,
                    fecha_modificacion=datetime.utcnow(),
                    campo_modificado=campo,
                    valor_anterior=str(valor_anterior) if valor_anterior is not None else "",
                    valor_nuevo=str(valor_nuevo) if valor_nuevo is not None else "",
                    justificacion="Actualización manual de proyecto"
                )
                db.add(historico)
                setattr(proyecto, campo, valor_nuevo)
 
        await db.commit()
        await db.refresh(proyecto)
        return proyecto
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error interno al editar el proyecto")



@app.get("/proyectos/", response_model=List[schemas.ProyectoOut])
async def listar_proyectos(
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    result = await db.execute(
        select(models.Proyecto)
    )
    proyectos = result.scalars().all()
    return proyectos

@app.get("/proyectos/{id}", response_model=schemas.ProyectoOut)
async def obtener_proyecto(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    result = await db.execute(
        select(models.Proyecto).where(models.Proyecto.id_proyecto == id)
    )
    proyecto = result.scalars().first()

    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    # if proyecto.id_director_proyecto != usuario.id_usuario:
    #     raise HTTPException(status_code=403, detail="No tienes acceso a este proyecto")

    return proyecto

@app.delete("/proyectos/{id}")
async def eliminar_proyecto(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    """
    Elimina un proyecto y todos sus POAs asociados (con sus actividades y tareas).
    Solo usuarios autenticados pueden eliminar proyectos.
    """
    # Verificar que el proyecto existe
    result = await db.execute(
        select(models.Proyecto).where(models.Proyecto.id_proyecto == id)
    )
    proyecto = result.scalars().first()

    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    # Obtener todos los POAs del proyecto
    result_poas = await db.execute(
        select(models.Poa).where(models.Poa.id_proyecto == id)
    )
    poas = result_poas.scalars().all()

    # Eliminar todos los POAs y sus dependencias (actividades, tareas, etc.)
    for poa in poas:
        # Eliminar actividades y tareas del POA (sin commit interno)
        result_actividades = await db.execute(
            select(models.Actividad).where(models.Actividad.id_poa == poa.id_poa)
        )
        actividades = result_actividades.scalars().all()
        for actividad in actividades:
            # Eliminar programación mensual de las tareas
            result_tareas = await db.execute(
                select(models.Tarea).where(models.Tarea.id_actividad == actividad.id_actividad)
            )
            tareas = result_tareas.scalars().all()
            for tarea in tareas:
                await db.execute(
                    delete(models.ProgramacionMensual).where(
                        models.ProgramacionMensual.id_tarea == tarea.id_tarea
                    )
                )
                await db.delete(tarea)
            await db.delete(actividad)

        # Eliminar histórico del POA
        await db.execute(
            delete(models.HistoricoPoa).where(models.HistoricoPoa.id_poa == poa.id_poa)
        )

        # Eliminar reformas del POA
        await db.execute(
            delete(models.ReformaPoa).where(models.ReformaPoa.id_poa == poa.id_poa)
        )

        # Eliminar logs de carga Excel del POA (id_poa es String, no UUID)
        await db.execute(
            delete(models.LogCargaExcel).where(models.LogCargaExcel.id_poa == str(poa.id_poa))
        )

        # Eliminar el POA
        await db.delete(poa)

    # Eliminar histórico del proyecto
    await db.execute(
        delete(models.HistoricoProyecto).where(models.HistoricoProyecto.id_proyecto == id)
    )

    # Eliminar el proyecto
    await db.delete(proyecto)
    await db.commit()

    return {"msg": f"Proyecto '{proyecto.titulo}' y todos sus POAs han sido eliminados correctamente"}

@app.get("/roles/", response_model=List[schemas.RolOut])
async def listar_roles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Rol))
    return result.scalars().all()

@app.get("/tipos-proyecto/", response_model=List[schemas.TipoProyectoOut])
async def listar_tipos_proyecto(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.TipoProyecto))
    return result.scalars().all()

@app.get("/estados-proyecto/", response_model=List[schemas.EstadoProyectoOut])
async def listar_estados_proyecto(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.EstadoProyecto))
    return result.scalars().all()

@app.get("/departamentos/", response_model=List[schemas.DepartamentoOut])
async def listar_departamentos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Departamento))
    return result.scalars().all()

#actividades
@app.post("/poas/{id_poa}/actividades")
async def crear_actividades_para_poa(
    id_poa: uuid.UUID,
    data: schemas.ActividadesBatchCreate,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    # Verificar existencia del POA
    result = await db.execute(select(models.Poa).where(models.Poa.id_poa == id_poa))
    poa = result.scalars().first()
    if not poa:
        raise HTTPException(status_code=404, detail="POA no encontrado")

    # VALIDACIÓN: Calcular suma de actividades existentes
    result = await db.execute(
        select(models.Actividad).where(models.Actividad.id_poa == id_poa)
    )
    actividades_existentes = result.scalars().all()
    suma_existente = sum(
        float(act.total_por_actividad or 0)
        for act in actividades_existentes
    )

    # Calcular suma de las nuevas actividades
    suma_nuevas = sum(
        float(act.total_por_actividad or 0)
        for act in data.actividades
    )

    total_actividades = suma_existente + suma_nuevas
    presupuesto_poa = float(poa.presupuesto_asignado)

    if total_actividades > presupuesto_poa:
        diferencia = total_actividades - presupuesto_poa
        raise HTTPException(
            status_code=400,
            detail=(
                f"La suma de actividades (${total_actividades:,.2f}) excedería "
                f"el presupuesto asignado al POA (${presupuesto_poa:,.2f}). "
                f"Diferencia: ${diferencia:,.2f}. "
                f"Presupuesto disponible: ${presupuesto_poa - suma_existente:,.2f}"
            )
        )

    actividades = [
        models.Actividad(
            id_actividad=uuid.uuid4(),
            id_poa=id_poa,
            descripcion_actividad=act.descripcion_actividad,
            total_por_actividad=act.total_por_actividad,
            saldo_actividad=act.saldo_actividad,
        )
        for act in data.actividades
    ]

    db.add_all(actividades)
    await db.commit()

    ids_creados = [str(act.id_actividad) for act in actividades]

    return JSONResponse(
        status_code=201,
        content={
            "msg": f"{len(actividades)} actividades creadas correctamente",
            "ids_actividades": ids_creados,
        }
    )


#tareas
@app.post("/actividades/{id_actividad}/tareas", response_model=schemas.TareaOut)
async def crear_tarea(
    id_actividad: uuid.UUID,
    data: schemas.TareaCreate,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    # Verificar existencia de la actividad
    result = await db.execute(select(models.Actividad).where(models.Actividad.id_actividad == id_actividad))
    actividad = result.scalars().first()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    # Verificar existencia del detalle de tarea
    result = await db.execute(select(models.DetalleTarea).where(models.DetalleTarea.id_detalle_tarea == data.id_detalle_tarea))
    detalle = result.scalars().first()
    if not detalle:
        raise HTTPException(status_code=404, detail="Detalle de tarea no encontrado")

    # DEBUG: Imprimir valores recibidos
    print(f"DEBUG crear_tarea - data.cantidad: {data.cantidad}, type: {type(data.cantidad)}")
    print(f"DEBUG crear_tarea - data.precio_unitario: {data.precio_unitario}, type: {type(data.precio_unitario)}")

    cantidad = data.cantidad if data.cantidad is not None else Decimal("0")
    precio_unitario = data.precio_unitario if data.precio_unitario is not None else Decimal("0")
    total = precio_unitario * cantidad

    # Obtener el POA para validar contra su presupuesto
    result = await db.execute(
        select(models.Poa).where(models.Poa.id_poa == actividad.id_poa)
    )
    poa = result.scalars().first()

    # Obtener suma de TODAS las tareas del POA (de todas las actividades)
    result = await db.execute(
        select(models.Actividad).where(models.Actividad.id_poa == actividad.id_poa)
    )
    actividades_poa = result.scalars().all()

    suma_total_tareas_poa = Decimal("0")
    for act in actividades_poa:
        result_tareas = await db.execute(
            select(models.Tarea).where(models.Tarea.id_actividad == act.id_actividad)
        )
        tareas_act = result_tareas.scalars().all()
        suma_total_tareas_poa += sum(
            (tarea.total or Decimal("0"))
            for tarea in tareas_act
        )

    # Validar que la nueva tarea no exceda el presupuesto del POA
    nueva_suma_total = suma_total_tareas_poa + total
    presupuesto_poa = Decimal(str(poa.presupuesto_asignado or 0))

    if nueva_suma_total > presupuesto_poa:
        diferencia = nueva_suma_total - presupuesto_poa
        raise HTTPException(
            status_code=400,
            detail=(
                f"La suma total de tareas del POA (${float(nueva_suma_total):,.2f}) excedería "
                f"el presupuesto asignado al POA (${float(presupuesto_poa):,.2f}). "
                f"Diferencia: ${float(diferencia):,.2f}. "
                f"Presupuesto disponible: ${float(presupuesto_poa - suma_total_tareas_poa):,.2f}"
            )
        )

    nueva_tarea = models.Tarea(
        id_tarea=uuid.uuid4(),
        id_actividad=id_actividad,
        id_detalle_tarea=data.id_detalle_tarea,
        nombre=data.nombre,
        detalle_descripcion=data.detalle_descripcion,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
        total=total,
        saldo_disponible=total,
        lineaPaiViiv=data.lineaPaiViiv
    )

    db.add(nueva_tarea)

    # Actualizar total_por_actividad y saldo_actividad de la actividad
    actividad.total_por_actividad = (actividad.total_por_actividad or Decimal("0")) + total
    actividad.saldo_actividad = (actividad.saldo_actividad or Decimal("0")) + total

    await db.commit()
    await db.refresh(nueva_tarea)

    return nueva_tarea


@app.delete("/tareas/{id_tarea}")
async def eliminar_tarea(
    id_tarea: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    result = await db.execute(select(models.Tarea).where(models.Tarea.id_tarea == id_tarea))
    tarea = result.scalars().first()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    # Obtener actividad para auditoría
    result = await db.execute(
        select(models.Actividad).where(models.Actividad.id_actividad == tarea.id_actividad)
    )
    actividad = result.scalars().first()

    # Registrar en auditoría la eliminación
    if actividad:
        historico = models.HistoricoPoa(
            id_historico=uuid.uuid4(),
            id_poa=actividad.id_poa,
            id_usuario=usuario.id_usuario,
            fecha_modificacion=datetime.utcnow(),
            campo_modificado="tarea_eliminada",
            valor_anterior=f"Tarea: {tarea.nombre}, Total: ${float(tarea.total or 0):.2f}",
            valor_nuevo="",
            justificacion="Eliminación de tarea",
            id_reforma=None
        )
        db.add(historico)

        # Actualizar total_por_actividad y saldo_actividad de la actividad
        total_tarea = tarea.total or Decimal("0")
        actividad.total_por_actividad = (actividad.total_por_actividad or Decimal("0")) - total_tarea
        actividad.saldo_actividad = (actividad.saldo_actividad or Decimal("0")) - total_tarea

    await db.delete(tarea)
    await db.commit()
    return {"msg": "Tarea eliminada correctamente"}


"""Registro de modificaciones críticas en tareas 

    Objetivo:
        Mantener un historial de cambios realizados sobre los campos económicos de una tarea.
        Esta auditoría permite garantizar trazabilidad y verificar la integridad de los datos 
        ante cambios.

    Parámetros:
        usuario (models.Usuario): Usuario autenticado que realiza la modificación.
        campos_auditar (list[str]): Lista de campos sensibles que serán monitoreados.
        data (schemas.TareaUpdate): Datos nuevos provistos por el usuario.

    Operación:
        - Compara los valores antiguos con los nuevos para cada campo monitoreado.
        - Si hay diferencias, se registra un nuevo objeto en `HistoricoPoa`, incluyendo:
            • campo modificado,
            • valor anterior y nuevo,
            • justificación del cambio,
            • usuario responsable y timestamp.

    Retorna:
        - dict: Mensaje de confirmación y detalle de la tarea actualizada.
"""
@app.put("/tareas/{id_tarea}")
async def editar_tarea(
    id_tarea: uuid.UUID,
    data: schemas.TareaUpdate,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    try:
        # Obtener la tarea
        result = await db.execute(
            select(models.Tarea).where(models.Tarea.id_tarea == id_tarea)
        )
        tarea = result.scalars().first()
 
        if not tarea:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")
 
        # Obtener la actividad relacionada
        result_actividad = await db.execute(
            select(models.Actividad).where(models.Actividad.id_actividad == tarea.id_actividad)
        )
        actividad = result_actividad.scalars().first()
        if not actividad:
            raise HTTPException(status_code=404, detail="Actividad no encontrada")
 
        id_poa = actividad.id_poa

        # Campos a auditar
        campos_auditar = ["cantidad", "precio_unitario", "lineaPaiViiv"]
 
        for campo in campos_auditar:
            if not hasattr(data, campo):
                continue  # evita fallos por campos no presentes
 
            valor_anterior = getattr(tarea, campo)
            valor_nuevo = getattr(data, campo)
 
            if valor_anterior != valor_nuevo:
                historico = models.HistoricoPoa(
                    id_historico=uuid.uuid4(),
                    id_poa=id_poa,
                    id_usuario=usuario.id_usuario,
                    fecha_modificacion=datetime.utcnow(),
                    campo_modificado=campo,
                    valor_anterior=str(valor_anterior) if valor_anterior is not None else "",
                    valor_nuevo=str(valor_nuevo) if valor_nuevo is not None else "",
                    justificacion="Actualización manual de tarea",
                    id_reforma=None
                )
                db.add(historico)
                setattr(tarea, campo, valor_nuevo)
        
        # Recalcular el total de la tarea después de las actualizaciones
        cantidad = tarea.cantidad or Decimal("0")
        precio_unitario = tarea.precio_unitario or Decimal("0")
        nuevo_total = precio_unitario * cantidad
        total_anterior = tarea.total or Decimal("0")
        diferencia_total = nuevo_total - total_anterior

        # Obtener el POA para validar contra su presupuesto
        result = await db.execute(
            select(models.Poa).where(models.Poa.id_poa == actividad.id_poa)
        )
        poa = result.scalars().first()

        # Obtener suma de TODAS las tareas del POA (de todas las actividades)
        result = await db.execute(
            select(models.Actividad).where(models.Actividad.id_poa == actividad.id_poa)
        )
        actividades_poa = result.scalars().all()

        suma_total_tareas_poa = Decimal("0")
        for act in actividades_poa:
            result_tareas = await db.execute(
                select(models.Tarea).where(models.Tarea.id_actividad == act.id_actividad)
            )
            tareas_act = result_tareas.scalars().all()
            for t in tareas_act:
                # Si es la tarea que estamos editando, usar el nuevo total
                if t.id_tarea == id_tarea:
                    suma_total_tareas_poa += nuevo_total
                else:
                    suma_total_tareas_poa += (t.total or Decimal("0"))

        # Validar que la modificación no exceda el presupuesto del POA
        presupuesto_poa = Decimal(str(poa.presupuesto_asignado or 0))

        if suma_total_tareas_poa > presupuesto_poa:
            diferencia = suma_total_tareas_poa - presupuesto_poa
            raise HTTPException(
                status_code=400,
                detail=(
                    f"La modificación haría que la suma total de tareas del POA (${float(suma_total_tareas_poa):,.2f}) "
                    f"exceda el presupuesto asignado al POA (${float(presupuesto_poa):,.2f}). "
                    f"Diferencia: ${float(diferencia):,.2f}"
                )
            )

        # Actualizar el total y saldo_disponible de la tarea
        tarea.total = nuevo_total
        tarea.saldo_disponible = nuevo_total

        # Actualizar total_por_actividad y saldo_actividad de la actividad
        actividad.total_por_actividad = (actividad.total_por_actividad or Decimal("0")) + diferencia_total
        actividad.saldo_actividad = (actividad.saldo_actividad or Decimal("0")) + diferencia_total

        await db.commit()
        await db.refresh(tarea)

        return {"msg": "Tarea actualizada", "tarea": tarea}

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error interno al editar la tarea")

#detalles tarea por poa
@app.get("/poas/{id_poa}/detalles_tarea", response_model=List[schemas.DetalleTareaOut])
async def obtener_detalles_tarea_poa(
    id_poa: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    result = await db.execute(
        select(models.DetalleTarea)
        .join(models.TipoPoaDetalleTarea, models.DetalleTarea.id_detalle_tarea == models.TipoPoaDetalleTarea.id_detalle_tarea)
        .join(models.Poa, models.TipoPoaDetalleTarea.id_tipo_poa == models.Poa.id_tipo_poa)
        .where(models.Poa.id_poa == id_poa)
    )
    return result.scalars().all()


#actividades por poa
@app.get("/poas/{id_poa}/actividades", response_model=List[schemas.ActividadOut])
async def obtener_actividades_de_poa(
    id_poa: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    result = await db.execute(
        select(models.Actividad)
        .where(models.Actividad.id_poa == id_poa)
        .order_by(models.Actividad.numero_actividad.asc())  # Ordenar por número de actividad
    )
    return result.scalars().all()


@app.delete("/actividades/{id_actividad}")
async def eliminar_actividad(id_actividad: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Actividad).where(models.Actividad.id_actividad == id_actividad))
    actividad = result.scalars().first()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    await db.delete(actividad)
    await db.commit()
    return {"msg": "Actividad eliminada correctamente"}


# Endpoints de consulta de presupuesto disponible
@app.get("/proyectos/{id_proyecto}/presupuesto-disponible")
async def obtener_presupuesto_disponible_proyecto(
    id_proyecto: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    """
    Retorna información detallada del presupuesto del proyecto.
    Muestra cuánto presupuesto se ha asignado a POAs y cuánto queda disponible.
    """
    # Obtener proyecto
    result = await db.execute(
        select(models.Proyecto).where(models.Proyecto.id_proyecto == id_proyecto)
    )
    proyecto = result.scalars().first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    # Obtener suma de POAs
    result = await db.execute(
        select(models.Poa).where(models.Poa.id_proyecto == id_proyecto)
    )
    poas = result.scalars().all()
    suma_poas = sum(float(poa.presupuesto_asignado or 0) for poa in poas)

    presupuesto_aprobado = float(proyecto.presupuesto_aprobado or 0)
    disponible = presupuesto_aprobado - suma_poas

    return {
        "presupuesto_aprobado": presupuesto_aprobado,
        "suma_poas_asignados": suma_poas,
        "presupuesto_disponible": disponible,
        "porcentaje_utilizado": (suma_poas / presupuesto_aprobado * 100) if presupuesto_aprobado > 0 else 0,
        "cantidad_poas": len(poas)
    }


@app.get("/poas/{id_poa}/presupuesto-disponible")
async def obtener_presupuesto_disponible_poa(
    id_poa: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    """
    Retorna información detallada del presupuesto del POA.
    Muestra cuánto presupuesto se ha asignado a actividades y cuánto queda disponible.
    """
    # Obtener POA
    result = await db.execute(
        select(models.Poa).where(models.Poa.id_poa == id_poa)
    )
    poa = result.scalars().first()
    if not poa:
        raise HTTPException(status_code=404, detail="POA no encontrado")

    # Obtener suma de actividades
    result = await db.execute(
        select(models.Actividad).where(models.Actividad.id_poa == id_poa)
    )
    actividades = result.scalars().all()
    suma_actividades = sum(float(act.total_por_actividad or 0) for act in actividades)

    presupuesto_asignado = float(poa.presupuesto_asignado or 0)
    disponible = presupuesto_asignado - suma_actividades

    return {
        "presupuesto_asignado": presupuesto_asignado,
        "suma_actividades": suma_actividades,
        "presupuesto_disponible": disponible,
        "porcentaje_utilizado": (suma_actividades / presupuesto_asignado * 100) if presupuesto_asignado > 0 else 0,
        "cantidad_actividades": len(actividades)
    }


@app.get("/actividades/{id_actividad}/presupuesto-disponible")
async def obtener_presupuesto_disponible_actividad(
    id_actividad: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    """
    Retorna información detallada del presupuesto de la actividad.
    Muestra cuánto presupuesto se ha utilizado en tareas y cuánto queda disponible.
    """
    # Obtener actividad
    result = await db.execute(
        select(models.Actividad).where(models.Actividad.id_actividad == id_actividad)
    )
    actividad = result.scalars().first()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    # Obtener suma de tareas
    result = await db.execute(
        select(models.Tarea).where(models.Tarea.id_actividad == id_actividad)
    )
    tareas = result.scalars().all()
    suma_tareas = sum(float(tarea.total or 0) for tarea in tareas)

    presupuesto_actividad = float(actividad.total_por_actividad or 0)
    disponible = presupuesto_actividad - suma_tareas

    return {
        "total_por_actividad": presupuesto_actividad,
        "suma_tareas": suma_tareas,
        "presupuesto_disponible": disponible,
        "porcentaje_utilizado": (suma_tareas / presupuesto_actividad * 100) if presupuesto_actividad > 0 else 0,
        "cantidad_tareas": len(tareas)
    }


#tareas por actividad
@app.get("/actividades/{id_actividad}/tareas", response_model=List[schemas.TareaOut])
async def obtener_tareas_de_actividad(
    id_actividad: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    result = await db.execute(
        select(models.Tarea).where(models.Tarea.id_actividad == id_actividad)
    )
    return result.scalars().all()


#editar actividad
@app.put("/actividades/{id_actividad}", response_model=schemas.ActividadOut)
async def editar_actividad(
    id_actividad: uuid.UUID,
    data: schemas.ActividadUpdate,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    result = await db.execute(
        select(models.Actividad).where(models.Actividad.id_actividad == id_actividad)
    )
    actividad = result.scalars().first()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    actividad.descripcion_actividad = data.descripcion_actividad
    await db.commit()
    await db.refresh(actividad)

    return actividad

async def registrar_historial_poa(db, poa_id, usuario_id, campo, valor_anterior, valor_nuevo, justificacion, reforma_id=None):
    historial = models.HistoricoPoa(
        id_historico=uuid.uuid4(),
        id_poa=poa_id,
        id_usuario=usuario_id,
        fecha_modificacion=datetime.now(),
        campo_modificado=campo,
        valor_anterior=valor_anterior,
        valor_nuevo=valor_nuevo,
        justificacion=justificacion,
        id_reforma=reforma_id
    )
    db.add(historial)
    await db.commit()


#reformas
@app.post("/poas/{id_poa}/reformas", response_model=schemas.ReformaPoaOut)
async def crear_reforma_poa(
    id_poa: uuid.UUID,
    data: schemas.ReformaPoaCreate,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    # Verificar que el POA exista
    result = await db.execute(select(models.Poa).where(models.Poa.id_poa == id_poa))
    poa = result.scalars().first()
    if not poa:
        raise HTTPException(status_code=404, detail="POA no encontrado")
    
    # Inicializar variables para logging
    codigo_poa = poa.codigo_poa if poa else ""
    proyecto_nombre = ""
    if poa and poa.id_proyecto:
        result = await db.execute(select(models.Proyecto).where(models.Proyecto.id_proyecto == poa.id_proyecto))
        proyecto = result.scalars().first()
        if proyecto:
            proyecto_nombre = proyecto.titulo

    """Validación de identidad del solicitante de reforma

    Objetivo:
        Asegurar que el usuario que solicita una reforma presupuestaria esté registrado y
        autorizado en el sistema.

    Parámetros:
        usuario (models.Usuario): Usuario autenticado que realiza la solicitud.

    Operación:
        - Consulta en la base de datos si el ID del usuario autenticado existe.
        - Si no se encuentra, se lanza una excepción HTTP 403.

    Retorna:
        - HTTPException 403: En caso de que el usuario no sea válido.
    """

    # Validar que el usuario solicitante exista
    result = await db.execute(select(models.Usuario).where(models.Usuario.id_usuario == usuario.id_usuario))
    if not result.scalars().first():
        raise HTTPException(status_code=403, detail="Usuario solicitante no válido")

    # Validar que el monto solicitado sea positivo
    if data.monto_solicitado <= 0:
        raise HTTPException(status_code=400, detail="El monto solicitado debe ser mayor a 0")

    # Validar que haya diferencia de montos
    if data.monto_solicitado == poa.presupuesto_asignado:
        raise HTTPException(status_code=400, detail="El monto solicitado debe ser diferente al monto actual del POA")

    reforma = models.ReformaPoa(
        id_reforma=uuid.uuid4(),
        id_poa=id_poa,
        fecha_solicitud=datetime.utcnow(),
        estado_reforma="Solicitada",
        monto_anterior=poa.presupuesto_asignado,
        monto_solicitado=data.monto_solicitado,
        justificacion=data.justificacion,
        id_usuario_solicita=usuario.id_usuario
    )

    db.add(reforma)
    await db.commit()
    await db.refresh(reforma)
    return reforma


@app.put("/reformas/{id_reforma}/tareas/{id_tarea}")
async def editar_tarea_en_reforma(
    id_reforma: uuid.UUID,
    id_tarea: uuid.UUID,
    data: schemas.TareaEditReforma,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    tarea = await db.get(models.Tarea, id_tarea)
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    reforma = await db.get(models.ReformaPoa, id_reforma)
    if not reforma:
        raise HTTPException(status_code=404, detail="Reforma no encontrada")

    poa = await db.get(models.Poa, tarea.id_actividad)
    if not poa or poa.id_poa != reforma.id_poa:
        raise HTTPException(status_code=400, detail="Tarea no pertenece al POA de esta reforma")

    tarea.cantidad = data.cantidad
    tarea.precio_unitario = data.precio_unitario
    tarea.total = data.cantidad * data.precio_unitario
    tarea.saldo_disponible = tarea.total  # ajustar si hay lógica adicional
    if data.lineaPaiViiv is not None:
        tarea.lineaPaiViiv = data.lineaPaiViiv

    db.add(tarea)

    db.add(models.HistoricoPoa(
        id_historico=uuid.uuid4(),
        id_poa=poa.id_poa,
        id_usuario=usuario.id_usuario,
        fecha_modificacion=datetime.now(),
        campo_modificado="Tarea",
        valor_anterior=f"Cantidad: {data.anterior_cantidad}, Precio: {data.anterior_precio}",
        valor_nuevo=f"Cantidad: {data.cantidad}, Precio: {data.precio_unitario}",
        justificacion=data.justificacion,
        id_reforma=reforma.id_reforma
    ))

    await db.commit()
    return {"msg": "Tarea actualizada correctamente"}


@app.delete("/reformas/{id_reforma}/tareas/{id_tarea}")
async def eliminar_tarea_en_reforma(
    id_reforma: uuid.UUID,
    id_tarea: uuid.UUID,
    justificacion: str,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    tarea = await db.get(models.Tarea, id_tarea)
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    actividad = await db.get(models.Actividad, tarea.id_actividad)
    poa = await db.get(models.Poa, actividad.id_poa)

    if not poa or poa.id_poa != (await db.get(models.ReformaPoa, id_reforma)).id_poa:
        raise HTTPException(status_code=400, detail="Tarea no corresponde a reforma")

    await db.delete(tarea)

    db.add(models.HistoricoPoa(
        id_historico=uuid.uuid4(),
        id_poa=poa.id_poa,
        id_usuario=usuario.id_usuario,
        fecha_modificacion=datetime.now(),
        campo_modificado="Tarea eliminada",
        valor_anterior=f"Tarea: {tarea.nombre} ({tarea.total})",
        valor_nuevo="Eliminada",
        justificacion=justificacion,
        id_reforma=id_reforma
    ))

    await db.commit()
    return {"msg": "Tarea eliminada correctamente"}


@app.post("/reformas/{id_reforma}/actividades/{id_actividad}/tareas")
async def agregar_tarea_en_reforma(
    id_reforma: uuid.UUID,
    id_actividad: uuid.UUID,
    data: schemas.TareaCreateReforma,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    actividad = await db.get(models.Actividad, id_actividad)
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    reforma = await db.get(models.ReformaPoa, id_reforma)
    if not reforma:
        raise HTTPException(status_code=404, detail="Reforma no encontrada")

    poa = await db.get(models.Poa, actividad.id_poa)
    if not poa or poa.id_poa != reforma.id_poa:
        raise HTTPException(status_code=400, detail="Actividad no corresponde a reforma")

    # Crear nueva tarea
    total = data.cantidad * data.precio_unitario
    nueva_tarea = models.Tarea(
        id_tarea=uuid.uuid4(),
        id_actividad=id_actividad,
        id_detalle_tarea=data.id_detalle_tarea,
        nombre=data.nombre,
        detalle_descripcion=data.detalle_descripcion,
        cantidad=data.cantidad,
        precio_unitario=data.precio_unitario,
        total=total,
        saldo_disponible=total,
        lineaPaiViiv=data.lineaPaiViiv
    )
    db.add(nueva_tarea)

    db.add(models.HistoricoPoa(
        id_historico=uuid.uuid4(),
        id_poa=poa.id_poa,
        id_usuario=usuario.id_usuario,
        fecha_modificacion=datetime.now(),
        campo_modificado="Tarea nueva",
        valor_anterior=None,
        valor_nuevo=f"Tarea: {data.nombre} - Total: {total}",
        justificacion=data.justificacion,
        id_reforma=id_reforma
    ))

    await db.commit()
    return {"msg": "Tarea agregada correctamente"}


@app.get("/poas/{id_poa}/reformas", response_model=List[schemas.ReformaOut])
async def listar_reformas_por_poa(
    id_poa: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    result = await db.execute(
        select(models.ReformaPoa).where(models.ReformaPoa.id_poa == id_poa)
    )
    return result.scalars().all()


@app.get("/reformas/{id_reforma}", response_model=schemas.ReformaOut)
async def obtener_reforma(
    id_reforma: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    reforma = await db.get(models.ReformaPoa, id_reforma)
    if not reforma:
        raise HTTPException(status_code=404, detail="Reforma no encontrada")
    return reforma

@app.post("/reformas/{id_reforma}/aprobar")
async def aprobar_reforma(
    id_reforma: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    # # Validar rol (ejemplo: solo "Director de Investigación")
    # rol = await db.get(models.Rol, usuario.id_rol)
    # if rol.nombre_rol not in ["Director de Investigacion", "Administrador"]:
    #     raise HTTPException(status_code=403, detail="No autorizado para aprobar reformas")

    reforma = await db.get(models.ReformaPoa, id_reforma)
    if not reforma:
        raise HTTPException(status_code=404, detail="Reforma no encontrada")

    reforma.estado_reforma = "Aprobada"
    reforma.fecha_aprobacion = datetime.now()
    reforma.id_usuario_aprueba = usuario.id_usuario

    db.add(reforma)
    await db.commit()

    return {"msg": "Reforma aprobada exitosamente"}

@app.get("/poas/{id_poa}/historial", response_model=List[schemas.HistoricoPoaOut])
async def historial_poa(
    id_poa: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    result = await db.execute(
        select(models.HistoricoPoa).where(models.HistoricoPoa.id_poa == id_poa).order_by(models.HistoricoPoa.fecha_modificacion.desc())
    )
    return result.scalars().all()

@app.get("/historico-proyectos/", response_model=List[schemas.HistoricoProyectoOut])
async def obtener_historico_proyectos(
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Obtener todos los históricos de proyectos con paginación"""
    result = await db.execute(
        select(models.HistoricoProyecto)
        .order_by(models.HistoricoProyecto.fecha_modificacion.desc())
        .offset(skip)
        .limit(limit)
    )
    historicos = result.scalars().all()
    
    # Enriquecer con información del usuario y proyecto
    respuesta = []
    for historico in historicos:
        # Obtener usuario
        usuario_result = await db.execute(
            select(models.Usuario).where(models.Usuario.id_usuario == historico.id_usuario)
        )
        usuario_obj = usuario_result.scalars().first()
        
        # Obtener proyecto
        proyecto_result = await db.execute(
            select(models.Proyecto).where(models.Proyecto.id_proyecto == historico.id_proyecto)
        )
        proyecto_obj = proyecto_result.scalars().first()
        
        respuesta.append({
            "id_historico": historico.id_historico,
            "id_proyecto": historico.id_proyecto,
            "campo_modificado": historico.campo_modificado,
            "valor_anterior": historico.valor_anterior,
            "valor_nuevo": historico.valor_nuevo,
            "justificacion": historico.justificacion,
            "fecha_modificacion": historico.fecha_modificacion,
            "usuario": usuario_obj.nombre_usuario if usuario_obj else "Desconocido",
            "codigo_proyecto": proyecto_obj.codigo_proyecto if proyecto_obj else None
        })
    return respuesta

@app.get("/historico-poas/", response_model=List[schemas.HistoricoPoaOut])
async def obtener_historico_poas(
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Obtener todos los históricos de POAs con paginación"""
    result = await db.execute(
        select(models.HistoricoPoa)
        .order_by(models.HistoricoPoa.fecha_modificacion.desc())
        .offset(skip)
        .limit(limit)
    )
    historicos = result.scalars().all()
    
    # Enriquecer con información del usuario, POA y proyecto
    respuesta = []
    for historico in historicos:
        # Obtener usuario
        usuario_result = await db.execute(
            select(models.Usuario).where(models.Usuario.id_usuario == historico.id_usuario)
        )
        usuario_obj = usuario_result.scalars().first()
        
        # Obtener POA
        poa_result = await db.execute(
            select(models.Poa).where(models.Poa.id_poa == historico.id_poa)
        )
        poa_obj = poa_result.scalars().first()
        
        # Obtener proyecto si existe POA
        proyecto_obj = None
        if poa_obj:
            proyecto_result = await db.execute(
                select(models.Proyecto).where(models.Proyecto.id_proyecto == poa_obj.id_proyecto)
            )
            proyecto_obj = proyecto_result.scalars().first()
        
        respuesta.append({
            "id_historico": historico.id_historico,
            "id_poa": historico.id_poa,
            "campo_modificado": historico.campo_modificado,
            "valor_anterior": historico.valor_anterior,
            "valor_nuevo": historico.valor_nuevo,
            "justificacion": historico.justificacion,
            "fecha_modificacion": historico.fecha_modificacion,
            "usuario": usuario_obj.nombre_usuario if usuario_obj else "Desconocido",
            "codigo_poa": poa_obj.codigo_poa if poa_obj else None,
            "codigo_proyecto": proyecto_obj.codigo_proyecto if proyecto_obj else None
        })
    return respuesta


@app.get("/proyectos/{id_proyecto}/poas", response_model=List[schemas.PoaOut])
async def obtener_poas_por_proyecto(
    id_proyecto: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    # Verificar si el proyecto existe
    result = await db.execute(select(models.Proyecto).where(models.Proyecto.id_proyecto == id_proyecto))
    proyecto = result.scalars().first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    # Obtener los POAs asociados al proyecto
    result = await db.execute(select(models.Poa).where(models.Poa.id_proyecto == id_proyecto))
    poas = result.scalars().all()
    return poas

@app.post("/transformar_excel/")
async def transformar_archivo_excel(
    file: UploadFile = File(...),
    hoja: str = Form(...),
    db: AsyncSession = Depends(get_db),
    id_poa: uuid.UUID = Form(...),  # Recibir el ID del POA
    confirmacion: bool = Form(False),  # Confirmación del frontend
    usuario: models.Usuario = Depends(get_current_user)
):
    """Validación de seguridad sobre archivos de entrada

    Objetivo:
        Evitar el procesamiento de archivos no permitidos que puedan comprometer la
        integridad del sistema, mediante una validación estricta de formato.

    Parámetros:
        file (UploadFile): Archivo enviado desde el cliente.
        hoja (str): Nombre de la hoja a procesar dentro del archivo Excel.

    Operación:
        - Revisa la extensión del archivo, permitiendo únicamente `.xls` y `.xlsx`.
        - Lanza una excepción HTTP 400 si el formato no es válido.
        - Permite el procesamiento solo si el archivo cumple con las condiciones definidas.

    Retorna:
        - HTTPException 400: Si el archivo tiene formato no soportado.
        - JSON: Resultado de la transformación si es válido.
    """

    # Validar que el archivo tenga una extensión válida
    if not file.filename.endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Archivo no soportado")

    # Validar que el POA exista
    result = await db.execute(select(models.Poa).where(models.Poa.id_poa == id_poa))
    poa = result.scalars().first()
    if not poa:
        raise HTTPException(status_code=404, detail="POA no encontrado")
    
    # Inicializar variables para logging
    codigo_poa = poa.codigo_poa if poa else ""
    proyecto_nombre = ""
    if poa and poa.id_proyecto:
        result = await db.execute(select(models.Proyecto).where(models.Proyecto.id_proyecto == poa.id_proyecto))
        proyecto = result.scalars().first()
        if proyecto:
            proyecto_nombre = proyecto.titulo

    # Verificar si ya existen actividades asociadas al POA
    result = await db.execute(select(models.Actividad).where(models.Actividad.id_poa == id_poa))
    actividades_existentes = result.scalars().all()

    # Leer el contenido del archivo
    contenido = await file.read()
    # Crear zona horaria UTC-5
    zona_utc_minus_5 = timezone(timedelta(hours=-5))

    try:
        json_result = transformar_excel(contenido, hoja)

        # VALIDACIÓN: Calcular presupuesto total del Excel
        presupuesto_total_excel = sum(
            float(actividad["total_por_actividad"])
            for actividad in json_result["actividades"]
        )

        # Validar que no exceda el presupuesto asignado al POA
        if presupuesto_total_excel > float(poa.presupuesto_asignado):
            raise HTTPException(
                status_code=400,
                detail=f"El presupuesto total del archivo Excel (${presupuesto_total_excel:,.2f}) excede el presupuesto asignado al POA (${float(poa.presupuesto_asignado):,.2f}). Diferencia: ${(presupuesto_total_excel - float(poa.presupuesto_asignado)):,.2f}"
            )

        if actividades_existentes:
            if not confirmacion:
                # Si no hay confirmación, enviar mensaje al frontend
                return {
                    "message": "El POA ya tiene actividades asociadas. ¿Deseas eliminarlas?",
                    "requires_confirmation": True,
                }

            # Si hay confirmación, eliminar las tareas y actividades asociadas
            await eliminar_tareas_y_actividades(id_poa,db)

            # Para log de eliminación
            log_elim = models.LogCargaExcel(
                id_log=uuid.uuid4(),
                id_poa=str(id_poa),
                codigo_poa=codigo_poa,
                id_usuario=str(usuario.id_usuario),
                usuario_nombre=usuario.nombre_usuario,
                usuario_email=usuario.email,
                proyecto_nombre=proyecto_nombre,
                fecha_carga=datetime.now(zona_utc_minus_5).replace(tzinfo=None),
                mensaje=f"Se eliminaron las actividades, sus tareas y programaciones mensuales asociadas debido a que el usuario decidió reemplazar los datos del POA con un nuevo archivo.",
                nombre_archivo=file.filename,
                hoja=hoja
            )
            db.add(log_elim)
            await db.commit()

        # Lista para registrar errores
        errores = []
        # Crear actividades y tareas en la base de datos
        for actividad in json_result["actividades"]:
            # Crear la actividad
            nueva_actividad = models.Actividad(
                id_actividad=uuid.uuid4(),
                id_poa=id_poa,
                numero_actividad=actividad.get("numero_actividad"),  # Guardar el número de orden
                descripcion_actividad=actividad["descripcion_actividad"],
                total_por_actividad=actividad["total_por_actividad"],
                saldo_actividad=actividad["total_por_actividad"],  # Inicialmente igual al total
            )
            db.add(nueva_actividad)
            await db.commit()
            await db.refresh(nueva_actividad)

            
            # Crear las tareas asociadas a la actividad
            for tarea in actividad["tareas"]:
                # Extraer el prefijo numérico (si existe) y el resto del nombre
                match = re.match(r"^(\d+\.\d+)\s+(.*)", tarea["nombre"])
                if match:
                    nombre_sin_prefijo = match.group(2)  # El nombre sin el prefijo (e.g., "Contratación de servicios profesionales")
                else:
                    nombre_sin_prefijo = tarea["nombre"]  # Si no hay prefijo, usar el nombre completo

                # Buscar el id_item_presupuestario
                result = await db.execute(
                    select(models.ItemPresupuestario).where(
                        (models.ItemPresupuestario.codigo == tarea["item_presupuestario"])
                    )
                )
                items_presupuestarios = result.scalars().all()

                if not items_presupuestarios:
                    # Eliminar todo lo subido y lanzar excepción
                    await eliminar_tareas_y_actividades(id_poa, db)
                    raise HTTPException(
                        status_code=400,
                        detail=f"No se guardo nada en la base de datos debido a que: \nNo se encontró el item presupuestario con código '{tarea['item_presupuestario']}' y descripción '{nombre_sin_prefijo}'"
                    )
                nombre_normalizado = normalizar_texto(nombre_sin_prefijo)
                encontrado = False
                for item in items_presupuestarios:
                     # Trae todos los detalles de tarea para ese item
                    result = await db.execute(
                        select(models.DetalleTarea).where(
                            models.DetalleTarea.id_item_presupuestario == item.id_item_presupuestario
                        )
                    )
                    detalles_tarea = result.scalars().all()
                    # Normaliza y compara en Python
                    for detalle in detalles_tarea:
                        
                        nombre_bd = normalizar_texto(detalle.nombre)
                        if nombre_bd == nombre_normalizado:
                            id_detalle_tarea = detalle.id_detalle_tarea
                            encontrado = True
                            break
                        else:
                            continue  # Sigue con el siguiente item si no encontró
                    if encontrado:
                        break
                if not encontrado:  # Si no encontró ningún detalle de tarea
                    await eliminar_tareas_y_actividades(id_poa, db)
                    db.add(log_elim)
                    await db.commit()

                    raise HTTPException(
                        status_code=400,
                        detail=f"No se guardo nada en la base de datos debido a que: \nNo se encontró detalle de tarea para el item presupuestario '{tarea['item_presupuestario']}' y descripción '{nombre_sin_prefijo}'"
                    )
               # Crear la tarea
                nueva_tarea = models.Tarea(
                    id_tarea=uuid.uuid4(),
                    id_actividad=nueva_actividad.id_actividad,
                    id_detalle_tarea=id_detalle_tarea,
                    nombre=tarea["nombre"],
                    detalle_descripcion=tarea["detalle_descripcion"],
                    cantidad=tarea["cantidad"],
                    precio_unitario=tarea["precio_unitario"],
                    total=tarea["total"],
                    saldo_disponible=tarea["total"],  # Inicialmente igual al total
                )
                db.add(nueva_tarea)

                await db.commit()
                await db.refresh(nueva_tarea)  

                # Guardar programaciones mensuales si existen y no es solo "suman"
                prog_ejec = tarea.get("programacion_ejecucion", {})
                for fecha, valor in prog_ejec.items():
                    if fecha == "suman":
                        continue
                    try:
                        # Extraer el mes y año de la fecha en múltiples formatos posibles
                        fecha_str = str(fecha)
                        mes_num = None
                        anio = None

                        # Intentar formato YYYY-MM-DD o YYYY-MM-DD HH:MM:SS
                        if len(fecha_str) >= 10 and fecha_str[4] == '-':
                            mes_num = int(fecha_str[5:7])
                            anio = int(fecha_str[0:4])
                        # Intentar formato DD/MM/YYYY
                        elif len(fecha_str) >= 10 and fecha_str[2] == '/':
                            mes_num = int(fecha_str[3:5])
                            anio = int(fecha_str[6:10])
                        # Intentar parsear con datetime como último recurso
                        else:
                            from datetime import datetime as dt
                            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"]:
                                try:
                                    parsed_date = dt.strptime(fecha_str.split()[0] if ' ' in fecha_str else fecha_str, fmt.split()[0])
                                    mes_num = parsed_date.month
                                    anio = parsed_date.year
                                    break
                                except ValueError:
                                    continue

                        if mes_num is None or mes_num < 1 or mes_num > 12:
                            print(f"Error: No se pudo extraer el mes de la fecha '{fecha_str}'")
                            continue

                        # Usar año actual si no se pudo extraer
                        if anio is None:
                            anio = datetime.now().year

                        # Formato MM-YYYY para coincidir con el frontend
                        mes_formateado = f"{str(mes_num).zfill(2)}-{anio}"
                        valor_float = float(valor)
                        nueva_prog = models.ProgramacionMensual(
                            id_programacion=uuid.uuid4(),
                            id_tarea=nueva_tarea.id_tarea,
                            mes=mes_formateado,  # Guardar en formato MM-YYYY
                            valor=valor_float
                        )
                        db.add(nueva_prog)
                    except Exception as e:
                        print(f"Error al procesar programación mensual para fecha '{fecha}': {str(e)}")
                        continue
                await db.commit()
            # Confirmar las tareas después de agregarlas
            await db.commit()

        # Registrar log de carga
        log_crea = models.LogCargaExcel(
            id_log=uuid.uuid4(),
            id_poa=str(id_poa),
            codigo_poa=codigo_poa,
            id_usuario=str(usuario.id_usuario),
            usuario_nombre=usuario.nombre_usuario,
            usuario_email=usuario.email,
            proyecto_nombre=proyecto_nombre,
            fecha_carga=datetime.now(zona_utc_minus_5).replace(tzinfo=None),
            # calcula el numero de actividades creadas y se muestra en el mensaje se cargaron ... actividades y sus tareas asociadas desde el archivo {file.filename}."
            mensaje=f"Se cargaron {len(json_result['actividades'])} actividades y sus tareas asociadas desde el archivo {file.filename}.",
            nombre_archivo=file.filename,
            hoja=hoja
        )
        db.add(log_crea)
        await db.commit()
        
        # Retornar el resultado
        if errores:
            return {
                "message": "Actividades y tareas creadas con advertencias",
                "errores": errores,
            }
        else:
            return {"message": "Actividades y tareas creadas exitosamente"}
    except ValueError as e:
        # Capturar errores de formato y lanzar una excepción HTTP
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/item-presupuestario/{id_item}", response_model=schemas.ItemPresupuestarioOut)
async def get_item_presupuestario(
    id_item: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(models.ItemPresupuestario).where(models.ItemPresupuestario.id_item_presupuestario == id_item))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item presupuestario no encontrado")
    return item

@app.get("/tareas/{id_tarea}/item-presupuestario", response_model=schemas.ItemPresupuestarioOut)
async def obtener_item_presupuestario_de_tarea(
    id_tarea: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    # Buscar la tarea y su detalle
    result = await db.execute(
        select(models.Tarea)
        .where(models.Tarea.id_tarea == id_tarea)
        .options(selectinload(models.Tarea.detalle_tarea).selectinload(models.DetalleTarea.item_presupuestario))
    )
    tarea = result.scalars().first()

    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    if not tarea.detalle_tarea or not tarea.detalle_tarea.item_presupuestario:
        raise HTTPException(status_code=404, detail="Item presupuestario no asociado a esta tarea")

    return tarea.detalle_tarea.item_presupuestario

@app.post("/reporte-poa/")
async def reporte_poa(
    anio: str = Form(...),
    tipo_proyecto: str = Form(...),
    id_departamento: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    # Determinar códigos de tipo de proyecto
    codigo_tipo: list[str] = []
    if tipo_proyecto == "Investigacion":
        codigo_tipo = ["PIIF", "PIS", "PIGR", "PIM"]
    elif tipo_proyecto == "Vinculacion":
        codigo_tipo = ["PVIF"]
    elif tipo_proyecto == "Transferencia":
        codigo_tipo = ["PTT"]
    else:
        raise HTTPException(status_code=400, detail="Tipo de proyecto no válido")

    # Buscar tipos de proyecto
    result = await db.execute(
        select(models.TipoProyecto)
        .where(models.TipoProyecto.codigo_tipo.in_(codigo_tipo))
    )
    tipos_proyecto = result.scalars().all()
    ids_tipo_proyecto = [tp.id_tipo_proyecto for tp in tipos_proyecto]

    # Buscar proyectos de esos tipos, con filtro por departamento si se proporciona
    query = select(models.Proyecto).where(models.Proyecto.id_tipo_proyecto.in_(ids_tipo_proyecto))
    if id_departamento:
        query = query.where(models.Proyecto.id_departamento == id_departamento)
    
    result = await db.execute(query)
    proyectos = result.scalars().all()
    ids_proyecto = [p.id_proyecto for p in proyectos]

    # Buscar POAs de esos proyectos y año
    result = await db.execute(
        select(models.Poa)
        .where(
            models.Poa.id_proyecto.in_(ids_proyecto),
            models.Poa.anio_ejecucion == anio
        )
    )
    poas = result.scalars().all()
    ids_poa = [poa.id_poa for poa in poas]

    # Buscar actividades de esos POAs (total_por_actividad > 0)
    result = await db.execute(
        select(models.Actividad)
        .where(
            models.Actividad.id_poa.in_(ids_poa),
            models.Actividad.total_por_actividad > 0
        )
    )
    actividades = result.scalars().all()
    ids_actividad = [act.id_actividad for act in actividades]

    # Buscar tareas de esas actividades (total > 0)
    result = await db.execute(
        select(models.Tarea)
        .where(
            models.Tarea.id_actividad.in_(ids_actividad),
            models.Tarea.total > 0
        )
    )
    tareas = result.scalars().all()

    # Preparar la lista plana de tareas
    tareas_lista = []
    for tarea in tareas:
        actividad = next((a for a in actividades if a.id_actividad == tarea.id_actividad), None)
        poa = next((p for p in poas if actividad and p.id_poa == actividad.id_poa), None)
        proyecto = next((pr for pr in proyectos if poa and pr.id_proyecto == poa.id_proyecto), None)
        tipo_proyecto_codigo = next((tp.codigo_tipo for tp in tipos_proyecto if proyecto and tp.id_tipo_proyecto == proyecto.id_tipo_proyecto), "") if proyecto else ""
        presupuesto_aprobado = proyecto.presupuesto_aprobado if proyecto else 0

        # Item presupuestario
        result = await db.execute(
            select(models.DetalleTarea).where(models.DetalleTarea.id_detalle_tarea == tarea.id_detalle_tarea)
        )
        detalle = result.scalars().first()
        item_presupuestario = None
        if detalle:
            result = await db.execute(
                select(models.ItemPresupuestario).where(models.ItemPresupuestario.id_item_presupuestario == detalle.id_item_presupuestario)
            )
            item = result.scalars().first()
            if item:
                item_presupuestario = item.codigo

        # Programación mensual
        result_prog = await db.execute(
            select(models.ProgramacionMensual).where(models.ProgramacionMensual.id_tarea == tarea.id_tarea)
        )
        programaciones = result_prog.scalars().all()
        prog_mensual_dict = {prog.mes: round(float(prog.valor), 2) for prog in programaciones}

        tareas_lista.append({
            "anio_poa": poa.anio_ejecucion if poa else "",
            "codigo_proyecto": proyecto.codigo_proyecto if proyecto else "",
            "tipo_proyecto": tipo_proyecto_codigo,
            "presupuesto_aprobado": float(presupuesto_aprobado) if presupuesto_aprobado else 0,
            "nombre": tarea.nombre,
            "detalle_descripcion": tarea.detalle_descripcion,  # NUEVO CAMPO
            "item_presupuestario": item_presupuestario,
            "cantidad": tarea.cantidad,
            "precio_unitario": float(tarea.precio_unitario),
            "total": float(tarea.total),
            "programacion_mensual": prog_mensual_dict
        })

    return tareas_lista


@app.post("/reporte-poa/excel/")
async def descargar_excel(
    reporte: list = Body(...)
):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Reporte POA")

    # Formatos
    header = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
    centro = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
    moneda = workbook.add_format({'num_format': '"$"#,##0.00', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
    texto = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True})

    # Detectar todos los meses presentes en todas las tareas
    meses_presentes = set()
    for tarea in reporte:
        meses_presentes.update(tarea.get("programacion_mensual", {}).keys())
    meses_orden = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    meses_final = meses_orden

    # Cabecera
    cabecera = [
        "AÑO POA", "CODIGO PROYECTO", "Tipo de Proyecto", "Presupuesto Aprobado", "Tarea",
        "Detalle Descripción",  # NUEVA COLUMNA
        "Item Presupuestario", "Cantidad", "Precio Unitario", "Total Tarea"
    ] + [m.capitalize() for m in meses_final]
    worksheet.write_row(0, 0, cabecera, header)

    # Ajustar anchos de columna
    worksheet.set_column(0, 0, 10)   # Año POA
    worksheet.set_column(1, 1, 15)   # Código Proyecto
    worksheet.set_column(2, 2, 15)   # Tipo de Proyecto
    worksheet.set_column(3, 3, 18)   # Presupuesto Aprobado
    worksheet.set_column(4, 4, 45)   # Tarea
    worksheet.set_column(5, 5, 45)   # Detalle Descripción  # NUEVA COLUMNA
    worksheet.set_column(6, 6, 16)   # Item Presupuestario
    worksheet.set_column(7, 7, 8)    # Cantidad
    worksheet.set_column(8, 8, 12)   # Precio Unitario
    worksheet.set_column(9, 9, 12)   # Total Tarea
    worksheet.set_column(10, 10 + len(meses_final) - 1, 11)  # Meses

    # Filas de tareas
    for row, tarea in enumerate(reporte, start=1):
        worksheet.write(row, 0, tarea["anio_poa"], centro)
        worksheet.write(row, 1, tarea["codigo_proyecto"], centro)
        worksheet.write(row, 2, tarea["tipo_proyecto"], centro)
        worksheet.write_number(row, 3, tarea["presupuesto_aprobado"], moneda)
        worksheet.write(row, 4, tarea["nombre"], texto)
        worksheet.write(row, 5, tarea["detalle_descripcion"], texto)  # NUEVA COLUMNA
        worksheet.write(row, 6, tarea["item_presupuestario"], centro)
        worksheet.write_number(row, 7, tarea["cantidad"], centro)
        worksheet.write_number(row, 8, tarea["precio_unitario"], moneda)
        worksheet.write_number(row, 9, tarea["total"], moneda)
        for col, mes in enumerate(meses_final, start=10):
            valor_mes = tarea.get("programacion_mensual", {}).get(mes, 0)
            worksheet.write_number(row, col, valor_mes, moneda)

    # Agregar fecha de descarga al final
    zona_utc_minus_5 = timezone(timedelta(hours=-5))
    fecha_descarga = datetime.now(zona_utc_minus_5).strftime("%d/%m/%Y %H:%M")
    fila_fecha = len(reporte) + 2
    worksheet.write(fila_fecha, 0, "Fecha de descarga:", centro)
    worksheet.write(fila_fecha, 1, fecha_descarga, centro)
    workbook.close()
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reporte-poa.xlsx"}
    )             

@app.post("/reporte-poa/pdf/")
async def descargar_pdf(
    reporte: list = Body(...)
):
    output = io.BytesIO()
    custom_size = (1700, 900)  # ancho x alto en puntos

    doc = SimpleDocTemplate(output, pagesize=custom_size)
    elements = []
    style_cell = ParagraphStyle('cell', fontSize=9, leading=11, alignment=1)  # Centrado
    style_left = ParagraphStyle('leftcell', fontSize=9, leading=11, alignment=0)  # Izquierda

    # Detectar todos los meses presentes en todas las tareas
    meses_presentes = set()
    for tarea in reporte:
        meses_presentes.update(tarea.get("programacion_mensual", {}).keys())
    meses_orden = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    meses_final = meses_orden

    # Cabecera
    cabecera = [
        Paragraph("<b>AÑO POA</b>", style_cell),
        Paragraph("<b>CODIGO PROYECTO</b>", style_cell),
        Paragraph("<b>Tipo de Proyecto</b>", style_cell),
        Paragraph("<b>Presupuesto Aprobado</b>", style_cell),
        Paragraph("<b>Tarea</b>", style_left),
        Paragraph("<b>Detalle Descripción</b>", style_left),  # NUEVA COLUMNA
        Paragraph("<b>Item Presupuestario</b>", style_cell),
        Paragraph("<b>Cantidad</b>", style_cell),
        Paragraph("<b>Precio Unitario</b>", style_cell),
        Paragraph("<b>Total Tarea</b>", style_cell)
    ] + [Paragraph(f"<b>{m.capitalize()}</b>", style_cell) for m in meses_final]
    data = [cabecera]

    # Filas de tareas
    for tarea in reporte:
        fila = [
            Paragraph(str(tarea["anio_poa"]), style_cell),
            Paragraph(str(tarea["codigo_proyecto"]), style_cell),
            Paragraph(str(tarea["tipo_proyecto"]), style_cell),
            Paragraph(f"${tarea['presupuesto_aprobado']:.2f}", style_cell),
            Paragraph(str(tarea["nombre"]), style_left),
            Paragraph(str(tarea["detalle_descripcion"]), style_left),  # NUEVA COLUMNA
            Paragraph(str(tarea["item_presupuestario"]), style_cell),
            Paragraph(str(tarea["cantidad"]), style_cell),
            Paragraph(f"${tarea['precio_unitario']:.2f}", style_cell),
            Paragraph(f"${tarea['total']:.2f}", style_cell)
        ]
        for mes in meses_final:
            valor_mes = tarea.get("programacion_mensual", {}).get(mes, 0)
            fila.append(Paragraph(f"${valor_mes:.2f}", style_cell))
        data.append(fila)

    # Definir anchos de columna (igual que Excel)
    col_widths = [60, 90, 90, 90, 250, 250, 80, 60, 80, 80] + [60]*len(meses_final)  # Ajustar ancho para nueva columna
    table = Table(data, hAlign='LEFT', colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#D9D9D9")),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (4,1), (4,-1), 'LEFT'),  # Columna "Tarea" alineada a la izquierda
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(table)

    # Fecha de descarga al final
    zona_utc_minus_5 = timezone(timedelta(hours=-5))
    fecha_descarga = datetime.datetime.now(zona_utc_minus_5).strftime("%d/%m/%Y %H:%M")
    elements.append(Spacer(1, 18))
    elements.append(Paragraph(f"<b>Fecha de descarga:</b> {fecha_descarga}", style_left))

    doc.build(elements)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte-poa.pdf"}
    )

@app.get("/logs-carga-excel/")
async def obtener_logs_carga_excel(
    db: AsyncSession = Depends(get_db),
    fecha_inicio: str = Query(None),
    fecha_fin: str = Query(None),
    usuario: models.Usuario = Depends(get_current_user)
):
    try:
        query = select(models.LogCargaExcel)
        # Filtros de fecha
        if fecha_inicio:
            try:
                fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
                query = query.where(models.LogCargaExcel.fecha_carga >= fecha_inicio_dt)
            except ValueError:
                return JSONResponse(content=[], status_code=200)
        if fecha_fin:
            try:
                from datetime import timedelta
                fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
                query = query.where(models.LogCargaExcel.fecha_carga <= fecha_fin_dt)
            except ValueError:
                return JSONResponse(content=[], status_code=200)
        query = query.order_by(models.LogCargaExcel.fecha_carga.desc())

        result = await db.execute(query)
        logs = result.scalars().all()

        respuesta = []
        for log in logs:
            respuesta.append({
                "fecha_carga": log.fecha_carga.strftime("%Y-%m-%d %H:%M:%S"),
                "usuario": log.usuario_nombre or "",
                "correo_usuario": log.usuario_email or "",
                "proyecto": log.proyecto_nombre or "",
                "codigo_poa": log.codigo_poa or "",
                "nombre_archivo": log.nombre_archivo or "",
                "hoja": log.hoja or "",
                "mensaje": log.mensaje or ""
            })
        return respuesta
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
# programacion mensual
@app.post("/programacion-mensual", response_model=schemas.ProgramacionMensualOut)
async def crear_programacion_mensual(
    data: schemas.ProgramacionMensualCreate,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    nueva = models.ProgramacionMensual(**data.dict())
    db.add(nueva)
    try:
        await db.commit()
        await db.refresh(nueva)
        return nueva
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Ya existe programación para ese mes y tarea.")

@app.put("/programacion-mensual/{id_programacion}", response_model=schemas.ProgramacionMensualOut)
async def actualizar_programacion_mensual(
    id_programacion: uuid.UUID,
    data: schemas.ProgramacionMensualUpdate,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    result = await db.execute(
        select(models.ProgramacionMensual).where(models.ProgramacionMensual.id_programacion == id_programacion)
    )
    programacion = result.scalars().first()
    if not programacion:
        raise HTTPException(status_code=404, detail="Programación no encontrada")

    programacion.valor = data.valor
    await db.commit()
    await db.refresh(programacion)
    return programacion

@app.get("/tareas/{id_tarea}/programacion-mensual", response_model=List[schemas.ProgramacionMensualOut])
async def obtener_programacion_por_tarea(
    id_tarea: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    # Verificar que la tarea exista
    result = await db.execute(select(models.Tarea).where(models.Tarea.id_tarea == id_tarea))
    tarea = result.scalars().first()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    result = await db.execute(
        select(models.ProgramacionMensual).where(models.ProgramacionMensual.id_tarea == id_tarea)
    )
    return result.scalars().all()

@app.delete("/tareas/{id_tarea}/programacion-mensual")
async def eliminar_programacion_mensual_tarea(
    id_tarea: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user)
):
    """Eliminar toda la programación mensual de una tarea específica
    
    Objetivo:
        Eliminar todos los registros de programación mensual asociados a una tarea,
        manteniendo la trazabilidad y verificando permisos del usuario.
    
    Parámetros:
        id_tarea (uuid.UUID): Identificador único de la tarea.
        db (AsyncSession): Conexión a la base de datos.
        usuario (models.Usuario): Usuario autenticado que realiza la operación.
    
    Operación:
        - Verifica que la tarea exista en la base de datos.
        - Busca todas las programaciones mensuales asociadas a la tarea.
        - Elimina todos los registros encontrados.
        - Registra la operación en el historial para auditoría.
    
    Retorna:
        - dict: Mensaje de confirmación con el número de registros eliminados.
    """
    try:
        # Verificar que la tarea exista
        result = await db.execute(
            select(models.Tarea).where(models.Tarea.id_tarea == id_tarea)
        )
        tarea = result.scalars().first()
        if not tarea:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")

        # Obtener la actividad y POA para el historial
        result_actividad = await db.execute(
            select(models.Actividad).where(models.Actividad.id_actividad == tarea.id_actividad)
        )
        actividad = result_actividad.scalars().first()
        if not actividad:
            raise HTTPException(status_code=404, detail="Actividad no encontrada")

        # Buscar todas las programaciones mensuales de la tarea
        result = await db.execute(
            select(models.ProgramacionMensual).where(
                models.ProgramacionMensual.id_tarea == id_tarea
            )
        )
        programaciones = result.scalars().all()
        
        if not programaciones:
            return {
                "message": "No se encontraron programaciones mensuales para esta tarea",
                "registros_eliminados": 0
            }

        # Contar registros antes de eliminar
        total_registros = len(programaciones)
        
        # Crear resumen de programaciones para el historial
        resumen_eliminado = ", ".join([
            f"{prog.mes}: ${prog.valor}" for prog in programaciones
        ])

        # Eliminar todas las programaciones mensuales
        for programacion in programaciones:
            await db.delete(programacion)

        # Registrar en el historial del POA
        historico = models.HistoricoPoa(
            id_historico=uuid.uuid4(),
            id_poa=actividad.id_poa,
            id_usuario=usuario.id_usuario,
            fecha_modificacion=datetime.utcnow(),
            campo_modificado="programacion_mensual_eliminada",
            valor_anterior=resumen_eliminado,
            valor_nuevo="",
            justificacion=f"Eliminación completa de programación mensual de la tarea: {tarea.nombre}",
            id_reforma=None
        )
        db.add(historico)

        # Confirmar cambios
        await db.commit()

        return {
            "message": f"Programación mensual eliminada exitosamente",
            "tarea": tarea.nombre,
            "registros_eliminados": total_registros,
            "detalle": f"Se eliminaron {total_registros} registros de programación mensual"
        }

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Error interno al eliminar programación mensual: {str(e)}"
        )