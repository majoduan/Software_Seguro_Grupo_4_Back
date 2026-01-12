from decimal import Decimal
from pydantic import BaseModel, condecimal, constr, Field, EmailStr, field_validator
from uuid import UUID
from datetime import date, datetime
from typing import Optional, List, Annotated
from app.validators import (
    validate_director_name,
    validate_password_strength,
    validate_username,
    validate_email_format,
    validate_anio_format,
    validate_date_range,
    validate_periodo_dates,
    validate_codigo_unique_format
)

class Token(BaseModel):
    """
    Token de autenticación

    Objetivo:
        Representar la estructura del token de acceso utilizado en los mecanismos de autenticación 
        basados en JWT u otros esquemas, permitiendo la validación y autorización de usuarios en 
        las operaciones protegidas del sistema.

    Parámetros:
        - access_token (str): Cadena codificada que representa el token de acceso.
        - token_type (str): Tipo del token, comúnmente 'bearer'.

    Operación:
        - Almacena temporalmente el token que se retorna al usuario autenticado.
        - Utilizado en encabezados HTTP para la autenticación de solicitudes.

    Retorna:
        - Instancia del modelo `Token`, que contiene la información de autenticación del usuario.
    """

    access_token: str
    token_type: str

class UserCreate(BaseModel):
    """
    Modelo para la creación de usuarios

    Objetivo:
        Capturar la información necesaria para el registro de nuevos usuarios, incluyendo
        credenciales y asignación de roles, garantizando la integridad de los datos mediante
        validaciones.

    Parámetros:
        - nombre_usuario (str): Nombre identificador del usuario (3-100 caracteres, alfanuméricos).
        - email (str): Correo electrónico único para el usuario (formato válido).
        - password (str): Contraseña (mínimo 8 caracteres, 1 mayúscula, 1 número).
        - id_rol (UUID): Identificador del rol asociado al nuevo usuario.

    Operación:
        - Este modelo es utilizado en los endpoints de registro de usuarios.
        - La contraseña debe ser procesada (hasheada) antes de su almacenamiento en base de datos.
        - Validaciones replicadas del frontend para consistencia.

    Retorna:
        - Instancia de `UserCreate` con los datos ingresados para su posterior procesamiento.
    """

    nombre_usuario: constr(min_length=3, max_length=100, strip_whitespace=True)
    email: EmailStr
    password: constr(min_length=8, max_length=100)
    id_rol: UUID

    @field_validator('nombre_usuario')
    @classmethod
    def validate_username_format(cls, v):
        """Valida que el nombre de usuario solo contenga alfanuméricos y espacios"""
        return validate_username(v)

    @field_validator('password')
    @classmethod
    def validate_password_complexity(cls, v):
        """Valida la complejidad de la contraseña (mayúscula + número)"""
        return validate_password_strength(v)

class UserOut(BaseModel):
    """
    Modelo de salida para información de usuario

    Objetivo:
        Estructurar los datos del usuario que pueden ser retornados al cliente, 
        excluyendo la contraseña u otros campos sensibles, para preservar la privacidad
        y seguridad de la información.

    Parámetros:
        - id_usuario (UUID): Identificador único del usuario.
        - nombre_usuario (str): Nombre identificador del usuario.
        - email (str): Correo electrónico del usuario.
        - id_rol (UUID): Identificador del rol asignado.
        - activo (bool): Estado del usuario (activo o inactivo).

    Operación:
        - Utilizado como respuesta en endpoints de consulta de usuarios.
        - Previene la exposición de contraseñas u otros datos críticos.

    Retorna:
        - Instancia de `UserOut` con los campos no sensibles del usuario.
    """

    id_usuario: UUID
    nombre_usuario: str
    email: str
    id_rol: UUID
    activo: bool

    class Config:
        from_attributes = True


class PeriodoCreate(BaseModel):
    """
    Modelo para la creación de periodos fiscales/académicos

    Validaciones replicadas del frontend:
    - codigo_periodo: 3-150 caracteres
    - nombre_periodo: 5-180 caracteres
    - fecha_fin > fecha_inicio
    - anio: 4 dígitos si está presente
    """
    codigo_periodo: constr(min_length=3, max_length=150, strip_whitespace=True)
    nombre_periodo: constr(min_length=5, max_length=180, strip_whitespace=True)
    fecha_inicio: date
    fecha_fin: date
    anio: Optional[constr(pattern=r'^\d{4}$')] = None
    mes: Optional[constr(max_length=35)] = None

    @field_validator('fecha_fin')
    @classmethod
    def validate_dates(cls, v, info):
        """Valida que fecha_fin sea posterior a fecha_inicio"""
        if 'fecha_inicio' in info.data and v is not None:
            validate_periodo_dates(info.data['fecha_inicio'], v)
        return v

class PeriodoOut(BaseModel):
    """
    Modelo de salida para periodos

    IMPORTANTE: NO hereda de PeriodoCreate para evitar que los validadores
    estrictos de input se ejecuten durante la serialización de datos existentes.
    Esto previene errores 500 cuando datos antiguos no cumplen validaciones nuevas.
    """
    id_periodo: UUID
    codigo_periodo: str
    nombre_periodo: str
    fecha_inicio: date
    fecha_fin: date
    anio: Optional[str] = None
    mes: Optional[str] = None

    class Config:
        from_attributes = True

class PoaCreate(BaseModel):
    """
    Modelo para la creación de POAs (Plan Operativo Anual)

    Validaciones replicadas del frontend:
    - codigo_poa: 5-50 caracteres
    - anio_ejecucion: 4 dígitos
    - presupuesto_asignado: > 0
    """
    id_proyecto: UUID
    id_periodo: UUID
    codigo_poa: constr(min_length=5, max_length=50, strip_whitespace=True)
    fecha_creacion: datetime
    id_tipo_poa: UUID
    id_estado_poa: Optional[UUID]
    anio_ejecucion: constr(pattern=r'^\d{4}$')
    presupuesto_asignado: condecimal(gt=0, max_digits=18, decimal_places=2)

    @field_validator('anio_ejecucion')
    @classmethod
    def validate_anio(cls, v):
        """Valida el formato del año de ejecución"""
        return validate_anio_format(v)


class PoaOut(BaseModel):
    """
    Modelo de salida para POAs

    IMPORTANTE: NO hereda de PoaCreate para evitar que los validadores
    estrictos de input se ejecuten durante la serialización de datos existentes.
    Esto previene errores 500 cuando datos antiguos no cumplen validaciones nuevas.
    """
    id_poa: UUID
    id_proyecto: UUID
    id_periodo: UUID
    codigo_poa: str
    fecha_creacion: datetime
    id_tipo_poa: UUID
    id_estado_poa: UUID
    anio_ejecucion: str
    presupuesto_asignado: Decimal

    class Config:
        from_attributes = True


class ProyectoCreate(BaseModel):
    """
    Modelo para la creación de proyectos

    Validaciones replicadas del frontend:
    - codigo_proyecto: 5-50 caracteres
    - titulo: 10-100 caracteres (nombre del proyecto único)
    - id_director_proyecto: 2-8 palabras, solo letras + acentos
    - presupuesto_aprobado: > 0
    - fecha_fin >= fecha_inicio
    - fechas de prórroga coherentes
    """
    codigo_proyecto: constr(min_length=5, max_length=50, strip_whitespace=True)
    titulo: constr(min_length=10, max_length=300, strip_whitespace=True)
    id_tipo_proyecto: UUID
    id_estado_proyecto: UUID
    id_departamento: Optional[UUID] = None
    id_director_proyecto: Optional[constr(min_length=5, max_length=200)] = None
    fecha_creacion: datetime
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    fecha_prorroga: Optional[date] = None
    fecha_prorroga_inicio: Optional[date] = None
    fecha_prorroga_fin: Optional[date] = None
    presupuesto_aprobado: Optional[condecimal(gt=0, max_digits=18, decimal_places=2)] = None

    @field_validator('fecha_creacion', mode='before')
    @classmethod
    def convert_date_to_datetime(cls, v):
        """Convierte date a datetime si es necesario"""
        if isinstance(v, str):
            # Si es solo fecha (YYYY-MM-DD), agregar hora
            if len(v) == 10 and v.count('-') == 2:
                return datetime.fromisoformat(f"{v}T00:00:00")
        if isinstance(v, date) and not isinstance(v, datetime):
            return datetime.combine(v, datetime.min.time())
        return v

    @field_validator('id_director_proyecto')
    @classmethod
    def validate_director(cls, v):
        """Valida el formato del nombre del director (2-8 palabras, solo letras)"""
        if v is not None:
            return validate_director_name(v)
        return v

    @field_validator('fecha_fin')
    @classmethod
    def validate_end_date(cls, v, info):
        """Valida que fecha_fin sea >= fecha_inicio"""
        if v is not None and 'fecha_inicio' in info.data and info.data['fecha_inicio'] is not None:
            if v < info.data['fecha_inicio']:
                raise ValueError("La fecha de fin no puede ser anterior a la fecha de inicio")
        return v

    @field_validator('fecha_prorroga_fin')
    @classmethod
    def validate_all_dates(cls, v, info):
        """Valida la coherencia de todas las fechas del proyecto"""
        if v is not None:
            validate_date_range(
                fecha_inicio=info.data.get('fecha_inicio'),
                fecha_fin=info.data.get('fecha_fin'),
                fecha_prorroga_inicio=info.data.get('fecha_prorroga_inicio'),
                fecha_prorroga_fin=v
            )
        return v

class ProyectoOut(BaseModel):
    """
    Modelo para la salida de proyectos (sin validaciones estrictas)

    No hereda de ProyectoCreate para evitar que los validadores
    se ejecuten al serializar datos existentes de la BD.
    """
    id_proyecto: UUID
    codigo_proyecto: str
    titulo: str
    id_tipo_proyecto: UUID
    id_estado_proyecto: UUID
    id_departamento: Optional[UUID] = None
    id_director_proyecto: Optional[str] = None
    fecha_creacion: datetime
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    fecha_prorroga: Optional[date] = None
    fecha_prorroga_inicio: Optional[date] = None
    fecha_prorroga_fin: Optional[date] = None
    presupuesto_aprobado: Optional[Decimal] = None

    class Config:
        from_attributes = True


class RolOut(BaseModel):
    id_rol: UUID
    nombre_rol: str
    descripcion: str

    class Config:
        from_attributes = True

class TipoProyectoOut(BaseModel):
    id_tipo_proyecto: UUID
    codigo_tipo: str
    nombre: str
    descripcion: str
    duracion_meses: int
    cantidad_periodos: int
    presupuesto_maximo: Decimal

    class Config:
        from_attributes = True

class EstadoProyectoOut(BaseModel):
    id_estado_proyecto: UUID
    nombre: str
    descripcion: str

    class Config:
        from_attributes = True

class DepartamentoCreate(BaseModel):
    """
    Schema para crear un nuevo departamento

    Validaciones:
    - nombre: 3-100 caracteres, no vacío
    - descripcion: opcional, máximo 500 caracteres
    """
    nombre: constr(min_length=3, max_length=100, strip_whitespace=True)
    descripcion: Optional[constr(max_length=500, strip_whitespace=True)] = None

    @field_validator('nombre')
    @classmethod
    def validate_nombre(cls, v):
        if not v or not v.strip():
            raise ValueError("El nombre del departamento no puede estar vacío")
        # Normalizar espacios múltiples
        v = ' '.join(v.split())
        return v

    @field_validator('descripcion', mode='before')
    @classmethod
    def validate_descripcion(cls, v):
        if v and not v.strip():
            return None
        return v


class DepartamentoUpdate(BaseModel):
    """
    Schema para actualizar un departamento existente

    Nota: Los campos son opcionales para permitir actualizaciones parciales
    """
    nombre: Optional[constr(min_length=3, max_length=100, strip_whitespace=True)] = None
    descripcion: Optional[constr(max_length=500, strip_whitespace=True)] = None

    @field_validator('nombre')
    @classmethod
    def validate_nombre(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError("El nombre del departamento no puede estar vacío")
            v = ' '.join(v.split())
        return v

    @field_validator('descripcion', mode='before')
    @classmethod
    def validate_descripcion(cls, v):
        if v and not v.strip():
            return None
        return v


class DepartamentoOut(BaseModel):
    id_departamento: UUID
    nombre: str
    descripcion: Optional[str] = None

    class Config:
        from_attributes = True


class EstadoPoaOut(BaseModel):
    id_estado_poa: UUID
    nombre: str
    descripcion: str

    class Config:
        from_attributes = True

class TipoPoaOut(BaseModel):
    id_tipo_poa: UUID
    codigo_tipo: str
    nombre: str
    descripcion: Optional[str]
    duracion_meses: int
    cantidad_periodos: int
    presupuesto_maximo: Decimal

    class Config:
        from_attributes = True

class ActividadCreate(BaseModel):
    """
    Modelo para la creación de actividades

    Validaciones replicadas del frontend:
    - descripcion_actividad: 10-500 caracteres
    - total_por_actividad: >= 0
    - saldo_actividad: >= 0
    """
    descripcion_actividad: constr(min_length=10, max_length=500, strip_whitespace=True)
    total_por_actividad: Optional[condecimal(ge=0, max_digits=18, decimal_places=2)] = 0.00
    saldo_actividad: Optional[condecimal(ge=0, max_digits=18, decimal_places=2)] = 0.00

class ActividadesBatchCreate(BaseModel):
    actividades: List[ActividadCreate]

class TareaCreate(BaseModel):
    """
    Modelo para la creación de tareas

    Validaciones replicadas del frontend:
    - nombre: máximo 200 caracteres
    - detalle_descripcion: máximo 5000 caracteres
    - cantidad: >= 0
    - precio_unitario: >= 0
    - lineaPaiViiv: >= 0 si está presente
    """
    id_detalle_tarea: Optional[UUID] = None
    nombre: Optional[constr(max_length=200)] = None
    detalle_descripcion: Optional[constr(max_length=5000)] = None
    cantidad: Optional[condecimal(ge=0, max_digits=10, decimal_places=2)] = 0
    precio_unitario: Optional[condecimal(ge=0, max_digits=18, decimal_places=2)] = 0
    lineaPaiViiv: Optional[int] = Field(None, ge=0)

class TareaOut(BaseModel):
    id_tarea: UUID
    nombre: Optional[str] = None
    detalle_descripcion: Optional[str] = None
    cantidad: Optional[condecimal(ge=0)] = 0
    precio_unitario: Optional[condecimal(ge=0)] = 0
    total: Optional[condecimal(ge=0)] = 0
    saldo_disponible: Optional[condecimal(ge=0)] = 0
    lineaPaiViiv: Optional[int] = None

    class Config:
        from_attributes = True


class DetalleTareaOut(BaseModel):
    id_detalle_tarea: UUID
    nombre: str
    descripcion: Optional[str]
    caracteristicas: Optional[str]  # Nuevo campo para información específica de la tarea
    id_item_presupuestario: Optional[UUID]  # Nuevo campo agregado
    precio_unitario: Optional[condecimal(max_digits=10, decimal_places=2)] = None  # Precio predefinido (solo para servicios profesionales)

    class Config:
        from_attributes = True

class DetalleTareaUpdatePrecio(BaseModel):
    """
    Schema para actualizar el precio de un detalle de tarea

    Objetivo:
        Validar y procesar la actualización del precio unitario de servicios profesionales
        predefinidos (Asistente de investigación, Servicios profesionales 1/2/3).

    Parámetros:
        - precio_unitario (Decimal): Nuevo precio a asignar. Debe ser mayor a 100 y menor a 5000.

    Validaciones:
        - Tipo: Decimal con máximo 10 dígitos y 2 decimales
        - Rango: 100 <= precio <= 5000

    Retorna:
        - Instancia validada del modelo con el precio sanitizado
    """
    precio_unitario: condecimal(gt=Decimal("100"), lt=Decimal("5000"), max_digits=10, decimal_places=2)

    @field_validator('precio_unitario')
    @classmethod
    def validate_precio_range(cls, v):
        if v <= Decimal("100"):
            raise ValueError("El precio debe ser mayor a $100")
        if v >= Decimal("5000"):
            raise ValueError("El precio debe ser menor a $5,000")
        return v

class DetalleTareaPrecioOut(BaseModel):
    """
    Schema para mostrar detalles de tarea con información de precios editables

    Objetivo:
        Proporcionar información completa de un detalle de tarea incluyendo su
        item presupuestario asociado, para la gestión de precios predefinidos.

    Parámetros:
        - id_detalle_tarea (UUID): Identificador único del detalle
        - nombre (str): Nombre del detalle de tarea
        - descripcion (str): Descripción del servicio profesional
        - precio_unitario (Decimal): Precio predefinido actual (nullable)
        - item_presupuestario (ItemPresupuestarioOut): Información del item presupuestario asociado

    Retorna:
        - Instancia del modelo con todos los datos necesarios para la UI de gestión de precios
    """
    id_detalle_tarea: UUID
    nombre: str
    descripcion: Optional[str]
    precio_unitario: Optional[condecimal(max_digits=10, decimal_places=2)]
    item_presupuestario: Optional['ItemPresupuestarioOut'] = None

    class Config:
        from_attributes = True

class ActividadOut(BaseModel):
    id_actividad: UUID
    numero_actividad: Optional[int] = None  # Número de orden de la actividad
    descripcion_actividad: str
    total_por_actividad: condecimal(max_digits=18, decimal_places=2)
    saldo_actividad: condecimal(max_digits=18, decimal_places=2)
    lineaPaiViiv: Optional[int] = None  # ← nuevo campo

    class Config:
        from_attributes = True

class ActividadUpdate(BaseModel):
    descripcion_actividad: str

class TareaOut(BaseModel):
    id_tarea: UUID
    nombre: Optional[str] = None
    detalle_descripcion: Optional[str] = None
    cantidad: Optional[condecimal(ge=0)] = 0
    precio_unitario: Optional[condecimal(ge=0)] = 0
    total: Optional[condecimal(ge=0)] = 0
    saldo_disponible: Optional[condecimal(ge=0)] = 0
    lineaPaiViiv: Optional[int] = None

    class Config:
        from_attributes = True

class TareaUpdate(BaseModel):
    """
    Modelo para actualización de tareas existentes

    IMPORTANTE: Permite cantidad = 0 para "limpiar" tareas sin eliminarlas.
    Cuando cantidad = 0, el frontend envía precio_unitario = 0 automáticamente.
    """
    cantidad: condecimal(ge=0)  # Permite 0 para tareas "vacías"
    precio_unitario: condecimal(ge=0)  # Permite 0 cuando cantidad = 0
    lineaPaiViiv: Optional[int] = None


#reformas
class ReformaPoaBase(BaseModel):
    """
    Modelo base para reformas de POA

    Objetivo:
        Estructurar la solicitud de una reforma financiera sobre un POA, incluyendo
        validación de montos y justificaciones, de modo que se preserve la trazabilidad 
        y el control del flujo presupuestario.

    Parámetros:
        - id_poa (UUID): Identificador del POA a reformar.
        - monto_solicitado (Decimal): Valor de la reforma solicitado, validado como mayor que cero.
        - justificacion (str): Justificación detallada que respalda la solicitud de reforma.

    Operación:
        - Garantiza integridad mediante validaciones.
        - Se utiliza en flujos donde se requiere autorización administrativa.

    Retorna:
        - Instancia de `ReformaPoaBase` lista para ser validada o almacenada.
    """

    id_poa: UUID
    monto_solicitado: condecimal(gt=0)
    justificacion: constr(min_length=10, max_length=500)

class ReformaPoaCreate(ReformaPoaBase):
    pass

class ReformaPoaOut(ReformaPoaBase):
    id_reforma: UUID
    fecha_solicitud: datetime
    fecha_aprobacion: Optional[datetime]
    estado_reforma: str
    monto_anterior: condecimal(gt=0)
    id_usuario_solicita: UUID
    id_usuario_aprueba: Optional[UUID]

    class Config:
        orm_mode = True

class TareaCreateReforma(BaseModel):
    """
    Modelo para crear tareas mediante reformas

    IMPORTANTE: Permite cantidad = 0 y precio_unitario = 0 para consistencia
    con el comportamiento de creación/edición normal de tareas.
    """
    id_actividad: UUID
    id_detalle_tarea: UUID
    nombre: Optional[str]
    detalle_descripcion: Optional[str]
    cantidad: condecimal(ge=0)  # Permite 0 para tareas "vacías"
    precio_unitario: condecimal(ge=0)  # Permite 0 cuando cantidad = 0
    justificacion: str
    lineaPaiViiv: Optional[int] = None

class TareaEditReforma(BaseModel):
    """
    Modelo para editar tareas mediante reformas

    IMPORTANTE: Permite cantidad = 0 y precio_unitario = 0 para consistencia
    con el comportamiento de creación/edición normal de tareas.
    """
    cantidad: Optional[condecimal(ge=0)]  # Permite 0 para tareas "vacías"
    precio_unitario: Optional[condecimal(ge=0)]  # Permite 0 cuando cantidad = 0
    justificacion: str
    lineaPaiViiv: Optional[int] = None

class HistoricoPoaOut(BaseModel):
    id_historico: UUID
    id_poa: UUID
    campo_modificado: str
    valor_anterior: Optional[str]
    valor_nuevo: Optional[str]
    justificacion: str
    fecha_modificacion: datetime
    usuario: Optional[str] = None  # Opcional para compatibilidad con endpoint original
    codigo_poa: Optional[str] = None
    codigo_proyecto: Optional[str] = None

    class Config:
        orm_mode = True

class HistoricoProyectoOut(BaseModel):
    id_historico: UUID
    id_proyecto: UUID
    campo_modificado: str
    valor_anterior: Optional[str]
    valor_nuevo: Optional[str]
    justificacion: str
    fecha_modificacion: datetime
    usuario: str
    codigo_proyecto: Optional[str] = None

    class Config:
        orm_mode = True


class ReformaOut(BaseModel):
    id_reforma: UUID
    id_poa: UUID
    fecha_solicitud: datetime
    estado_reforma: str
    monto_anterior: condecimal(gt=0)
    monto_solicitado: condecimal(gt=0)
    justificacion: str

    class Config:
        orm_mode = True

class ItemPresupuestarioOut(BaseModel):
    id_item_presupuestario: UUID
    codigo: str
    nombre: str
    descripcion: Optional[str]

    class Config:
        orm_mode = True

class ProgramacionMensualBase(BaseModel):
    """
    Modelo base para programación mensual

    Validaciones replicadas del frontend:
    - mes: formato MM-YYYY
    - valor: >= 0
    """
    mes: Annotated[str, Field(pattern=r"^\d{2}-\d{4}$")]  # Formato MM-AAAA
    valor: condecimal(ge=0, max_digits=18, decimal_places=2)

class ProgramacionMensualCreate(ProgramacionMensualBase):
    id_tarea: UUID

class ProgramacionMensualUpdate(BaseModel):
    valor: condecimal(ge=0, max_digits=18, decimal_places=2)

class ProgramacionMensualOut(BaseModel):
    """
    Modelo de salida para programación mensual

    IMPORTANTE: NO hereda de ProgramacionMensualBase para evitar que los validadores
    estrictos de input (como el patrón regex del mes) se ejecuten durante la serialización.
    Esto previene errores 500 cuando datos antiguos tienen formato diferente (ej: "abril" vs "04-2024").
    """
    id_programacion: UUID
    id_tarea: UUID
    mes: str  # Sin validador de patrón para permitir cualquier formato existente
    valor: Decimal

    class Config:
        orm_mode = True

# ==================== Resumen de POAs ====================

class ActividadResumen(BaseModel):
    """
    Schema para mostrar resumen de una actividad (sin tareas ni programación mensual)

    Objetivo:
        Proporcionar información resumida de una actividad mostrando solo su número,
        descripción y total gastado. Usado en el resumen consolidado de POAs.

    Parámetros:
        - numero_actividad (int, optional): Número de orden de la actividad
        - descripcion_actividad (str): Descripción de la actividad
        - total_actividad (Decimal): Total gastado en la actividad

    Retorna:
        - Instancia del modelo con datos resumidos de la actividad
    """
    numero_actividad: Optional[int] = None
    descripcion_actividad: str
    total_actividad: condecimal(max_digits=12, decimal_places=2)

class PoaResumen(BaseModel):
    """
    Schema para mostrar resumen de un POA con sus actividades

    Objetivo:
        Proporcionar información consolidada de un POA mostrando presupuesto,
        total gastado, saldo disponible y listado de actividades con sus totales.

    Parámetros:
        - id_poa (UUID): Identificador único del POA
        - codigo_poa (str): Código del POA
        - anio_poa (int): Año del POA
        - presupuesto_asignado (Decimal): Presupuesto total asignado
        - total_gastado (Decimal): Total gastado en todas las actividades
        - saldo_disponible (Decimal): Presupuesto restante (asignado - gastado)
        - actividades (List[ActividadResumen]): Listado de actividades con sus totales

    Retorna:
        - Instancia del modelo con resumen completo del POA
    """
    id_poa: UUID
    codigo_poa: str
    anio_poa: int
    presupuesto_asignado: condecimal(max_digits=12, decimal_places=2)
    total_gastado: condecimal(max_digits=12, decimal_places=2)
    saldo_disponible: condecimal(max_digits=12, decimal_places=2)
    actividades: List[ActividadResumen]

class ResumenPoasOut(BaseModel):
    """
    Schema para mostrar resumen consolidado de todos los POAs de un proyecto

    Objetivo:
        Proporcionar una vista consolidada de todos los POAs de un proyecto,
        mostrando información del proyecto y el desglose de gastos por POA y actividad.

    Parámetros:
        - id_proyecto (UUID): Identificador único del proyecto
        - codigo_proyecto (str): Código del proyecto
        - titulo (str): Título del proyecto
        - poas (List[PoaResumen]): Listado de POAs con sus actividades y totales
        - total_proyecto (Decimal): Suma total de gastos en todos los POAs

    Retorna:
        - Instancia del modelo con resumen completo del proyecto y sus POAs
    """
    id_proyecto: UUID
    codigo_proyecto: str
    titulo: str
    poas: List[PoaResumen]
    total_proyecto: condecimal(max_digits=12, decimal_places=2)

    class Config:
        from_attributes = True