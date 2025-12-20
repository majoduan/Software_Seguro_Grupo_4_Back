"""
Validadores de reglas de negocio para endpoints

Este módulo contiene validadores que se ejecutan en los endpoints
para garantizar la integridad de las reglas de negocio (validaciones
que requieren consultas a la base de datos).
"""

from decimal import Decimal
from datetime import date
from typing import Optional
from uuid import UUID
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from fastapi import HTTPException

from app import models
from app.validators import validate_project_duration, validate_presupuesto_range


async def validate_proyecto_business_rules(
    db: AsyncSession,
    data,
    proyecto_id: Optional[str] = None
) -> None:
    """
    Valida las reglas de negocio para proyectos.

    Reglas (replicadas del frontend):
    - Título de proyecto único (el código puede repetirse)
    - Título máximo 100 caracteres
    - Presupuesto <= presupuesto_maximo del tipo de proyecto
    - Duración <= duracion_meses del tipo de proyecto
    - Tipo de proyecto existe
    - Estado de proyecto existe

    Args:
        db: Sesión de base de datos
        data: Datos del proyecto (ProyectoCreate)
        proyecto_id: ID del proyecto (si es edición)

    Raises:
        HTTPException: Si alguna validación falla
    """
    # Validar que el tipo de proyecto existe
    result = await db.execute(
        select(models.TipoProyecto).where(
            models.TipoProyecto.id_tipo_proyecto == data.id_tipo_proyecto
        )
    )
    tipo_proyecto = result.scalars().first()
    if not tipo_proyecto:
        raise HTTPException(
            status_code=404,
            detail="Tipo de proyecto no encontrado"
        )

    # Validar que el estado de proyecto existe
    result = await db.execute(
        select(models.EstadoProyecto).where(
            models.EstadoProyecto.id_estado_proyecto == data.id_estado_proyecto
        )
    )
    estado_proyecto = result.scalars().first()
    if not estado_proyecto:
        raise HTTPException(
            status_code=404,
            detail="Estado de proyecto no encontrado"
        )

    # Validar que el departamento existe (si se proporciona)
    if hasattr(data, 'id_departamento') and data.id_departamento is not None:
        result = await db.execute(
            select(models.Departamento).where(
                models.Departamento.id_departamento == data.id_departamento
            )
        )
        departamento = result.scalars().first()
        if not departamento:
            raise HTTPException(
                status_code=404,
                detail="Departamento no encontrado"
            )

    # Validar título único (el código se puede repetir, pero el nombre del proyecto debe ser único)
    query = select(models.Proyecto).where(
        models.Proyecto.titulo == data.titulo
    )
    if proyecto_id:
        query = query.where(models.Proyecto.id_proyecto != proyecto_id)

    result = await db.execute(query)
    if result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un proyecto con el nombre '{data.titulo}'"
        )

    # Validar presupuesto <= presupuesto_maximo del tipo
    if data.presupuesto_aprobado is not None:
        try:
            validate_presupuesto_range(
                float(data.presupuesto_aprobado),
                float(tipo_proyecto.presupuesto_maximo) if tipo_proyecto.presupuesto_maximo else None
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Validar duración del proyecto
    if data.fecha_inicio and data.fecha_fin:
        try:
            validate_project_duration(
                data.fecha_inicio,
                data.fecha_fin,
                tipo_proyecto.duracion_meses
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


async def validate_poa_business_rules(
    db: AsyncSession,
    data,
    poa_id: Optional[str] = None
) -> None:
    """
    Valida las reglas de negocio para POAs.

    Reglas (replicadas del frontend):
    - Código POA único
    - Proyecto existe
    - Periodo existe
    - Tipo POA existe
    - No duplicar periodo (un proyecto no puede tener 2 POAs en el mismo periodo)
    - Presupuesto <= presupuesto_maximo del tipo POA
    - Duración del periodo <= duracion_meses del tipo POA

    Args:
        db: Sesión de base de datos
        data: Datos del POA (PoaCreate)
        poa_id: ID del POA (si es edición)

    Raises:
        HTTPException: Si alguna validación falla
    """
    # Validar que el proyecto existe
    result = await db.execute(
        select(models.Proyecto).where(
            models.Proyecto.id_proyecto == data.id_proyecto
        )
    )
    proyecto = result.scalars().first()
    if not proyecto:
        raise HTTPException(
            status_code=404,
            detail="Proyecto no encontrado"
        )

    # Validar que el periodo existe
    result = await db.execute(
        select(models.Periodo).where(
            models.Periodo.id_periodo == data.id_periodo
        )
    )
    periodo = result.scalars().first()
    if not periodo:
        raise HTTPException(
            status_code=404,
            detail="Periodo no encontrado"
        )

    # Validar que el tipo POA existe
    result = await db.execute(
        select(models.TipoPOA).where(
            models.TipoPOA.id_tipo_poa == data.id_tipo_poa
        )
    )
    tipo_poa = result.scalars().first()
    if not tipo_poa:
        raise HTTPException(
            status_code=404,
            detail="Tipo de POA no encontrado"
        )

    # Validar código único
    query = select(models.Poa).where(
        models.Poa.codigo_poa == data.codigo_poa
    )
    if poa_id:
        query = query.where(models.Poa.id_poa != poa_id)

    result = await db.execute(query)
    if result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un POA con el código '{data.codigo_poa}'"
        )

    # Validar que no haya otro POA con el mismo periodo (solo en creación o si cambió el periodo)
    query = select(models.Poa).where(
        models.Poa.id_proyecto == data.id_proyecto,
        models.Poa.id_periodo == data.id_periodo
    )
    if poa_id:
        query = query.where(models.Poa.id_poa != poa_id)

    result = await db.execute(query)
    if result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Ya existe un POA para este proyecto en el periodo seleccionado"
        )

    # Validar presupuesto <= presupuesto_maximo del tipo POA
    try:
        validate_presupuesto_range(
            float(data.presupuesto_asignado),
            float(tipo_poa.presupuesto_maximo) if tipo_poa.presupuesto_maximo else None
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Validar duración del periodo <= duracion_meses del tipo POA
    duracion_periodo = relativedelta(periodo.fecha_fin, periodo.fecha_inicio)
    meses_periodo = duracion_periodo.years * 12 + duracion_periodo.months

    # Si tiene más de 15 días, cuenta como mes adicional
    if duracion_periodo.days > 15:
        meses_periodo += 1

    if meses_periodo > tipo_poa.duracion_meses:
        raise HTTPException(
            status_code=400,
            detail=f"La duración del periodo ({meses_periodo} meses) excede "
                   f"la duración máxima ({tipo_poa.duracion_meses} meses) "
                   f"permitida para este tipo de POA"
        )

    # Validar que la suma de presupuestos de POAs no exceda el presupuesto del proyecto
    await validate_poa_presupuesto_proyecto(
        db=db,
        id_proyecto=data.id_proyecto,
        nuevo_presupuesto_poa=data.presupuesto_asignado,
        poa_id_excluir=poa_id
    )


async def validate_poa_presupuesto_proyecto(
    db: AsyncSession,
    id_proyecto,
    nuevo_presupuesto_poa: Decimal,
    poa_id_excluir: Optional[str] = None
) -> None:
    """
    Valida que la suma de presupuestos de POAs no exceda el presupuesto del proyecto.

    Args:
        db: Sesión de base de datos
        id_proyecto: ID del proyecto
        nuevo_presupuesto_poa: Presupuesto del POA que se está creando/editando
        poa_id_excluir: ID del POA a excluir del cálculo (en caso de edición)

    Raises:
        HTTPException: Si la suma excede el presupuesto del proyecto
    """
    # Obtener el proyecto
    result = await db.execute(
        select(models.Proyecto).where(
            models.Proyecto.id_proyecto == id_proyecto
        )
    )
    proyecto = result.scalars().first()
    if not proyecto or not proyecto.presupuesto_aprobado:
        return  # Si no hay presupuesto aprobado, no validar

    # Calcular suma de presupuestos de POAs existentes
    query = select(models.Poa).where(models.Poa.id_proyecto == id_proyecto)
    if poa_id_excluir:
        query = query.where(models.Poa.id_poa != poa_id_excluir)

    result = await db.execute(query)
    poas_existentes = result.scalars().all()

    suma_poas_existentes = sum(
        float(poa.presupuesto_asignado or 0)
        for poa in poas_existentes
    )

    # Calcular nuevo total
    total_con_nuevo_poa = suma_poas_existentes + float(nuevo_presupuesto_poa)
    presupuesto_proyecto = float(proyecto.presupuesto_aprobado)

    if total_con_nuevo_poa > presupuesto_proyecto:
        diferencia = total_con_nuevo_poa - presupuesto_proyecto
        raise HTTPException(
            status_code=400,
            detail=(
                f"La suma de presupuestos de POAs (${total_con_nuevo_poa:,.2f}) "
                f"excedería el presupuesto aprobado del proyecto (${presupuesto_proyecto:,.2f}). "
                f"Diferencia: ${diferencia:,.2f}. "
                f"Presupuesto disponible: ${presupuesto_proyecto - suma_poas_existentes:,.2f}"
            )
        )


async def validate_periodo_business_rules(
    db: AsyncSession,
    data,
    periodo_id: Optional[str] = None
) -> None:
    """
    Valida las reglas de negocio para periodos.

    Reglas (replicadas del frontend):
    - Código único

    Args:
        db: Sesión de base de datos
        data: Datos del periodo (PeriodoCreate)
        periodo_id: ID del periodo (si es edición)

    Raises:
        HTTPException: Si alguna validación falla
    """
    # Validar código único
    query = select(models.Periodo).where(
        models.Periodo.codigo_periodo == data.codigo_periodo
    )
    if periodo_id:
        query = query.where(models.Periodo.id_periodo != periodo_id)

    result = await db.execute(query)
    if result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un periodo con el código '{data.codigo_periodo}'"
        )


async def validate_tarea_business_rules(
    db: AsyncSession,
    data,
    id_actividad: str
) -> None:
    """
    Valida las reglas de negocio para tareas.

    Reglas (replicadas del frontend):
    - Actividad existe
    - Detalle de tarea existe (si se proporciona)

    Args:
        db: Sesión de base de datos
        data: Datos de la tarea (TareaCreate)
        id_actividad: ID de la actividad

    Raises:
        HTTPException: Si alguna validación falla
    """
    # Validar que la actividad existe
    result = await db.execute(
        select(models.Actividad).where(
            models.Actividad.id_actividad == id_actividad
        )
    )
    actividad = result.scalars().first()
    if not actividad:
        raise HTTPException(
            status_code=404,
            detail="Actividad no encontrada"
        )

    # Validar que el detalle de tarea existe (si se proporciona)
    if data.id_detalle_tarea:
        result = await db.execute(
            select(models.DetalleTarea).where(
                models.DetalleTarea.id_detalle_tarea == data.id_detalle_tarea
            )
        )
        detalle = result.scalars().first()
        if not detalle:
            raise HTTPException(
                status_code=404,
                detail="Detalle de tarea no encontrado"
            )


async def validate_usuario_business_rules(
    db: AsyncSession,
    data
) -> None:
    """
    Valida las reglas de negocio para usuarios.

    Reglas (replicadas del frontend):
    - Email único
    - Rol existe

    Args:
        db: Sesión de base de datos
        data: Datos del usuario (UserCreate)

    Raises:
        HTTPException: Si alguna validación falla
    """
    # Validar email único
    result = await db.execute(
        select(models.Usuario).where(
            models.Usuario.email == data.email.lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Ya existe un usuario con este correo electrónico"
        )

    # Validar que el rol existe
    result = await db.execute(
        select(models.Rol).where(
            models.Rol.id_rol == data.id_rol
        )
    )
    if not result.scalars().first():
        raise HTTPException(
            status_code=404,
            detail="Rol no encontrado"
        )


async def validate_programacion_mensual_business_rules(
    db: AsyncSession,
    data
) -> None:
    """
    Valida las reglas de negocio para programación mensual.

    Reglas:
    - Tarea existe

    Args:
        db: Sesión de base de datos
        data: Datos de la programación mensual

    Raises:
        HTTPException: Si alguna validación falla
    """
    # Validar que la tarea existe
    result = await db.execute(
        select(models.Tarea).where(
            models.Tarea.id_tarea == data.id_tarea
        )
    )
    if not result.scalars().first():
        raise HTTPException(
            status_code=404,
            detail="Tarea no encontrada"
        )


async def validate_departamento_unique(
    db: AsyncSession,
    nombre: str,
    departamento_id: Optional[UUID] = None
) -> None:
    """
    Valida que el nombre del departamento sea único.

    Args:
        db: Sesión de base de datos
        nombre: Nombre del departamento a validar
        departamento_id: ID del departamento (None para creación, UUID para edición)

    Raises:
        HTTPException: 400 si ya existe un departamento con ese nombre
    """
    # Normalizar para comparación (quitar espacios extras y convertir a mayúsculas)
    nombre_normalizado = ' '.join(nombre.split()).upper()

    query = select(models.Departamento).where(
        func.upper(func.regexp_replace(models.Departamento.nombre, r'\s+', ' ', 'g')) == nombre_normalizado
    )

    # Si estamos editando, excluir el departamento actual
    if departamento_id:
        query = query.where(models.Departamento.id_departamento != departamento_id)

    result = await db.execute(query)
    departamento_existente = result.scalars().first()

    if departamento_existente:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un departamento con el nombre '{nombre}'"
        )


async def validate_departamento_can_delete(
    db: AsyncSession,
    departamento_id: UUID
) -> None:
    """
    Valida que un departamento pueda ser eliminado.

    Un departamento NO puede eliminarse si tiene proyectos asociados.

    Args:
        db: Sesión de base de datos
        departamento_id: ID del departamento a eliminar

    Raises:
        HTTPException: 400 si el departamento tiene proyectos asociados
    """
    # Verificar si existen proyectos asociados
    query = select(func.count(models.Proyecto.id_proyecto)).where(
        models.Proyecto.id_departamento == departamento_id
    )

    result = await db.execute(query)
    count = result.scalar()

    if count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar el departamento porque tiene {count} proyecto(s) asociado(s). "
                   f"Reasigne o elimine los proyectos primero."
        )
