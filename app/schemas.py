from decimal import Decimal
from pydantic import BaseModel, condecimal,constr,Field
from uuid import UUID
from datetime import date, datetime
from typing import Optional,List,Annotated

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
        - nombre_usuario (str): Nombre identificador del usuario.
        - email (str): Correo electrónico único para el usuario.
        - password (str): Contraseña en texto plano que será procesada y almacenada de forma segura.
        - id_rol (UUID): Identificador del rol asociado al nuevo usuario.

    Operación:
        - Este modelo es utilizado en los endpoints de registro de usuarios.
        - La contraseña debe ser procesada (hasheada) antes de su almacenamiento en base de datos.

    Retorna:
        - Instancia de `UserCreate` con los datos ingresados para su posterior procesamiento.
    """

    nombre_usuario: str
    email: str
    password: str
    id_rol: UUID

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
    codigo_periodo: str
    nombre_periodo: str
    fecha_inicio: date
    fecha_fin: date
    anio: Optional[str] = None
    mes: Optional[str] = None

class PeriodoOut(PeriodoCreate):
    id_periodo: UUID

    class Config:
        from_attributes = True

class PoaCreate(BaseModel):
    id_proyecto: UUID
    id_periodo: UUID
    codigo_poa: str
    fecha_creacion: datetime
    id_tipo_poa: UUID
    id_estado_poa: Optional[UUID]
    anio_ejecucion: str
    presupuesto_asignado: Decimal


class PoaOut(PoaCreate):
    id_poa: UUID
    fecha_creacion: datetime
    id_estado_poa: UUID

    class Config:
        from_attributes = True


class ProyectoCreate(BaseModel):
    codigo_proyecto: str
    titulo: str
    id_tipo_proyecto: UUID
    id_estado_proyecto: UUID
    id_director_proyecto: Optional[str] = None
    fecha_creacion: datetime
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    fecha_prorroga: Optional[date] = None
    fecha_prorroga_inicio: Optional[date] = None
    fecha_prorroga_fin: Optional[date] = None
    presupuesto_aprobado: Optional[Decimal] = None

class ProyectoOut(ProyectoCreate):
    id_proyecto: UUID

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


class PeriodoCreate(BaseModel):
    codigo_periodo: str
    nombre_periodo: str
    fecha_inicio: date
    fecha_fin: date
    anio: Optional[str] = None
    mes: Optional[str] = None

class PeriodoOut(PeriodoCreate):
    id_periodo: UUID

    class Config:
        from_attributes = True

class ActividadCreate(BaseModel):
    descripcion_actividad: str
    total_por_actividad: Optional[condecimal(ge=0)] = 0.00
    saldo_actividad: Optional[condecimal(ge=0)] = 0.00
class ActividadesBatchCreate(BaseModel):
    actividades: List[ActividadCreate]

class TareaCreate(BaseModel):
    id_detalle_tarea: Optional[UUID] = None
    nombre: Optional[str] = None
    detalle_descripcion: Optional[str] = None
    cantidad: Optional[condecimal(ge=0)] = 0
    precio_unitario: Optional[condecimal(ge=0)] = 0
    lineaPaiViiv: Optional[int] = None

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

    class Config:
        from_attributes = True

class ActividadOut(BaseModel):
    id_actividad: UUID
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
    cantidad: condecimal(gt=0)
    precio_unitario: condecimal(gt=0)
    lineaPaiViiv: Optional[int] = None  # ← nuevo campo


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
    id_actividad: UUID
    id_detalle_tarea: UUID
    nombre: Optional[str]
    detalle_descripcion: Optional[str]
    cantidad: condecimal(gt=0)
    precio_unitario: condecimal(gt=0)
    justificacion: str
    lineaPaiViiv: Optional[int] = None

class TareaEditReforma(BaseModel):
    cantidad: Optional[condecimal(gt=0)]
    precio_unitario: Optional[condecimal(gt=0)]
    justificacion: str
    lineaPaiViiv: Optional[int] = None

class HistoricoPoaOut(BaseModel):
    campo_modificado: str
    valor_anterior: Optional[str]
    valor_nuevo: Optional[str]
    justificacion: str
    fecha_modificacion: datetime
    usuario: str

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
    mes: Annotated[str, Field(pattern=r"^\d{2}-\d{4}$")]  # Formato MM-AAAA
    valor: Decimal

class ProgramacionMensualCreate(ProgramacionMensualBase):
    id_tarea: UUID

class ProgramacionMensualUpdate(BaseModel):
    valor: Decimal

class ProgramacionMensualOut(ProgramacionMensualBase):
    id_programacion: UUID
    id_tarea: UUID

    class Config:
        orm_mode = True