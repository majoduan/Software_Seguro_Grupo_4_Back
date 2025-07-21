import uuid
from app import models
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

"""
Eliminar tareas y actividades asociadas a un POA

Objetivo:
    Eliminar de forma asincrónica todas las tareas y actividades vinculadas a un POA específico,
    garantizando la integridad referencial al eliminar primero las dependencias (tareas) antes de
    su entidad superior (actividad).

Parámetros:
    - id_poa (UUID): Identificador único del POA cuyas actividades y tareas serán eliminadas.
    - db (AsyncSession): Sesión de base de datos asincrónica utilizada para realizar las operaciones.

Operación:
    - Consulta todas las actividades relacionadas con el POA proporcionado.
    - Para cada actividad, consulta y elimina sus tareas asociadas.
    - Posteriormente, elimina la actividad.
    - Confirma los cambios utilizando `db.commit()` para hacer persistente la eliminación.

Retorna:
    - None. La función no retorna valores, pero modifica el estado de la base de datos de 
    forma permanente.
"""

async def eliminar_tareas_y_actividades(id_poa: uuid.UUID, db: AsyncSession):
    """
    Elimina todas las tareas y actividades asociadas a un POA.
    """
    # Obtener las actividades asociadas al POA
    result = await db.execute(select(models.Actividad).where(models.Actividad.id_poa == id_poa))
    actividades = result.scalars().all()
    for actividad in actividades:
        # Eliminar tareas asociadas a la actividad
        result = await db.execute(select(models.Tarea).where(models.Tarea.id_actividad == actividad.id_actividad))
        tareas = result.scalars().all()
        for tarea in tareas:
            await db.delete(tarea)

        # Eliminar la actividad
        await db.delete(actividad)

    # Confirmar los cambios en la base de datos
    await db.commit()