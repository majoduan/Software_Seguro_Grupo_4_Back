import pytest
import uuid
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from pydantic import ValidationError

from app import models, schemas
from app.main import (
    crear_reforma_poa,
    editar_tarea_en_reforma,
    actualizar_precio_detalle_tarea,
    eliminar_tarea_en_reforma,
    agregar_tarea_en_reforma,
    listar_reformas_por_poa,
    obtener_reforma,
    aprobar_reforma
)

@pytest.mark.asyncio
class TestReformasPOA:
    """Tests para la lógica de Reformas del POA en main.py

    Objetivo: Validar ≥90% de cobertura en validadores y lógica de negocio del módulo de reformas.

    Alcance:
    - Creación de reformas con validaciones de negocio
    - Edición de tareas en contexto de reforma
    - Eliminación de tareas en reforma
    - Agregación de tareas en reforma
    - Listado y obtención de reformas
    - Aprobación de reformas
    - Actualización de precios predefinidos (gestión de precios)
    """

    async def test_crear_reforma_poa_success(self):
        """Debe crear una reforma exitosamente"""
        id_poa = uuid.uuid4()
        db = AsyncMock()
        usuario = models.Usuario(id_usuario=uuid.uuid4())
        data = schemas.ReformaPoaCreate(
            id_poa=id_poa,
            monto_solicitado=Decimal("60000.00"),
            justificacion="Reforma necesaria para el proyecto debido a ajustes presupuestarios anuales"
        )

        poa = models.Poa(id_poa=id_poa, codigo_poa="POA-001", presupuesto_asignado=Decimal("50000.00"))

        # Mocking db calls
        mock_res_poa = MagicMock()
        mock_res_poa.scalars().first.return_value = poa
        mock_res_user = MagicMock()
        mock_res_user.scalars().first.return_value = usuario

        db.execute.side_effect = [mock_res_poa, mock_res_user]

        reforma = await crear_reforma_poa(id_poa, data, db, usuario)

        assert reforma.id_poa == id_poa
        assert reforma.monto_solicitado == Decimal("60000.00")
        assert reforma.monto_anterior == Decimal("50000.00")
        assert reforma.estado_reforma == "Solicitada"
        assert db.add.called
        assert db.commit.called

    async def test_crear_reforma_monto_invalido_pydantic(self):
        """Pydantic debe rechazar reforma con monto <= 0 antes de llamar a la función"""
        id_poa = uuid.uuid4()

        # Pydantic debe lanzar ValidationError antes de que llegue a la función
        with pytest.raises(ValidationError) as exc:
            data = schemas.ReformaPoaCreate(
                id_poa=id_poa,
                monto_solicitado=Decimal("-10.00"),
                justificacion="Reforma con monto invalido para validacion de seguridad"
            )

        # Verificar que el error es por el validador gt=0
        assert "greater_than" in str(exc.value)

    async def test_crear_reforma_justificacion_corta(self):
        """Pydantic debe rechazar reforma con justificación < 10 caracteres"""
        id_poa = uuid.uuid4()

        with pytest.raises(ValidationError) as exc:
            data = schemas.ReformaPoaCreate(
                id_poa=id_poa,
                monto_solicitado=Decimal("50000.00"),
                justificacion="Corta"  # Solo 5 caracteres
            )

        assert "at least 10 characters" in str(exc.value)

    async def test_crear_reforma_poa_no_encontrado(self):
        """Debe retornar 404 si el POA no existe"""
        id_poa = uuid.uuid4()
        db = AsyncMock()
        usuario = models.Usuario(id_usuario=uuid.uuid4())
        data = schemas.ReformaPoaCreate(
            id_poa=id_poa,
            monto_solicitado=Decimal("60000.00"),
            justificacion="Reforma para POA inexistente en la base de datos del sistema"
        )

        # Simular que el POA no existe
        mock_res = MagicMock()
        mock_res.scalars().first.return_value = None
        db.execute.return_value = mock_res

        with pytest.raises(HTTPException) as exc:
            await crear_reforma_poa(id_poa, data, db, usuario)

        assert exc.value.status_code == 404
        assert "POA no encontrado" in str(exc.value.detail)

    async def test_crear_reforma_usuario_no_valido(self):
        """Debe rechazar si el usuario solicitante no existe"""
        id_poa = uuid.uuid4()
        db = AsyncMock()
        usuario = models.Usuario(id_usuario=uuid.uuid4())
        data = schemas.ReformaPoaCreate(
            id_poa=id_poa,
            monto_solicitado=Decimal("60000.00"),
            justificacion="Reforma solicitada por usuario no autorizado en el sistema actual"
        )

        poa = models.Poa(id_poa=id_poa, presupuesto_asignado=Decimal("50000.00"))
        mock_res_poa = MagicMock()
        mock_res_poa.scalars().first.return_value = poa

        # Usuario no encontrado
        mock_res_user = MagicMock()
        mock_res_user.scalars().first.return_value = None

        db.execute.side_effect = [mock_res_poa, mock_res_user]

        with pytest.raises(HTTPException) as exc:
            await crear_reforma_poa(id_poa, data, db, usuario)

        assert exc.value.status_code == 403
        assert "Usuario solicitante no válido" in str(exc.value.detail)

    async def test_editar_tarea_en_reforma_calculations(self):
        """Debe actualizar tarea y calcular el total automáticamente (cantidad * precio)"""
        id_reforma = uuid.uuid4()
        id_tarea = uuid.uuid4()
        db = AsyncMock()
        usuario = models.Usuario(id_usuario=uuid.uuid4())
        data = schemas.TareaEditReforma(
            cantidad=Decimal("5.00"),
            precio_unitario=Decimal("100.00"),
            justificacion="Cambio de precio por inflacion y reajuste de mercado actual"
        )

        id_actividad = uuid.uuid4()
        tarea = models.Tarea(id_tarea=id_tarea, id_actividad=id_actividad, cantidad=Decimal("2.00"), precio_unitario=Decimal("50.00"))
        reforma = models.ReformaPoa(id_reforma=id_reforma, id_poa=uuid.uuid4())
        actividad = models.Actividad(id_actividad=id_actividad, id_poa=reforma.id_poa)
        poa = models.Poa(id_poa=reforma.id_poa)

        # db.get calls in order: tarea, reforma, actividad, poa
        db.get.side_effect = [tarea, reforma, actividad, poa]

        await editar_tarea_en_reforma(id_reforma, id_tarea, data, db, usuario)

        assert tarea.total == Decimal("500.00")
        assert tarea.saldo_disponible == Decimal("500.00")
        assert db.commit.called

    async def test_editar_tarea_en_reforma_tarea_no_encontrada(self):
        """Debe retornar 404 si la tarea no existe"""
        id_reforma = uuid.uuid4()
        id_tarea = uuid.uuid4()
        db = AsyncMock()
        usuario = models.Usuario(id_usuario=uuid.uuid4())
        data = schemas.TareaEditReforma(
            cantidad=Decimal("5.00"),
            precio_unitario=Decimal("100.00"),
            justificacion="Intento de editar tarea inexistente en la base de datos actual"
        )

        # Simular que la tarea no existe
        db.get.return_value = None

        with pytest.raises(HTTPException) as exc:
            await editar_tarea_en_reforma(id_reforma, id_tarea, data, db, usuario)

        assert exc.value.status_code == 404
        assert "Tarea no encontrada" in str(exc.value.detail)

    async def test_editar_tarea_en_reforma_reforma_no_encontrada(self):
        """Debe retornar 404 si la reforma no existe"""
        id_reforma = uuid.uuid4()
        id_tarea = uuid.uuid4()
        id_actividad = uuid.uuid4()
        db = AsyncMock()
        usuario = models.Usuario(id_usuario=uuid.uuid4())
        data = schemas.TareaEditReforma(
            cantidad=Decimal("5.00"),
            precio_unitario=Decimal("100.00"),
            justificacion="Edicion de tarea en reforma inexistente en el sistema actual"
        )

        tarea = models.Tarea(id_tarea=id_tarea, id_actividad=id_actividad)

        # Primera llamada retorna tarea, segunda reforma no existe
        db.get.side_effect = [tarea, None]

        with pytest.raises(HTTPException) as exc:
            await editar_tarea_en_reforma(id_reforma, id_tarea, data, db, usuario)

        assert exc.value.status_code == 404
        assert "Reforma no encontrada" in str(exc.value.detail)

    async def test_editar_tarea_tarea_no_pertenece_a_poa_reforma(self):
        """Debe rechazar si la tarea no pertenece al POA de la reforma"""
        id_reforma = uuid.uuid4()
        id_tarea = uuid.uuid4()
        id_actividad = uuid.uuid4()
        db = AsyncMock()
        usuario = models.Usuario(id_usuario=uuid.uuid4())
        data = schemas.TareaEditReforma(
            cantidad=Decimal("5.00"),
            precio_unitario=Decimal("100.00"),
            justificacion="Intento de editar tarea que no corresponde a este POA especifico"
        )

        tarea = models.Tarea(id_tarea=id_tarea, id_actividad=id_actividad)
        reforma = models.ReformaPoa(id_reforma=id_reforma, id_poa=uuid.uuid4())
        actividad = models.Actividad(id_actividad=id_actividad, id_poa=uuid.uuid4())  # POA diferente
        poa = models.Poa(id_poa=actividad.id_poa)

        db.get.side_effect = [tarea, reforma, actividad, poa]

        with pytest.raises(HTTPException) as exc:
            await editar_tarea_en_reforma(id_reforma, id_tarea, data, db, usuario)

        assert exc.value.status_code == 400
        assert "no pertenece al POA" in str(exc.value.detail)

    async def test_eliminar_tarea_en_reforma_success(self):
        """Debe eliminar una tarea correctamente en el contexto de reforma"""
        id_reforma = uuid.uuid4()
        id_tarea = uuid.uuid4()
        id_actividad = uuid.uuid4()
        id_poa = uuid.uuid4()
        db = AsyncMock()
        usuario = models.Usuario(id_usuario=uuid.uuid4())
        justificacion = "Eliminacion de tarea obsoleta segun nueva planificacion estrategica"

        tarea = models.Tarea(id_tarea=id_tarea, id_actividad=id_actividad, nombre="Tarea Test", total=Decimal("1000"))
        actividad = models.Actividad(id_actividad=id_actividad, id_poa=id_poa)
        poa = models.Poa(id_poa=id_poa)
        reforma = models.ReformaPoa(id_reforma=id_reforma, id_poa=id_poa)

        db.get.side_effect = [tarea, actividad, poa, reforma]

        result = await eliminar_tarea_en_reforma(id_reforma, id_tarea, justificacion, db, usuario)

        assert "eliminada correctamente" in result["msg"]
        assert db.delete.called
        assert db.commit.called

    async def test_agregar_tarea_en_reforma_success(self):
        """Debe agregar una nueva tarea en el contexto de reforma"""
        id_reforma = uuid.uuid4()
        id_actividad = uuid.uuid4()
        id_poa = uuid.uuid4()
        db = AsyncMock()
        usuario = models.Usuario(id_usuario=uuid.uuid4())

        data = schemas.TareaCreateReforma(
            id_actividad=id_actividad,
            id_detalle_tarea=uuid.uuid4(),
            nombre="Nueva tarea en reforma presupuestaria institucional",
            detalle_descripcion="Descripcion detallada de la nueva tarea",
            cantidad=Decimal("3.00"),
            precio_unitario=Decimal("200.00"),
            lineaPaiViiv=3,  # Debe ser int, no string
            justificacion="Nueva tarea necesaria por cambios en alcance del proyecto actual"
        )

        reforma = models.ReformaPoa(id_reforma=id_reforma, id_poa=id_poa)
        actividad = models.Actividad(id_actividad=id_actividad, id_poa=id_poa)
        poa = models.Poa(id_poa=id_poa)

        # El endpoint usa: actividad, reforma, poa (no detalle)
        db.get.side_effect = [actividad, reforma, poa]

        result = await agregar_tarea_en_reforma(id_reforma, id_actividad, data, db, usuario)

        assert result["msg"] == "Tarea agregada correctamente"
        assert db.add.called
        assert db.commit.called

    async def test_listar_reformas_por_poa(self):
        """Debe listar todas las reformas de un POA específico"""
        id_poa = uuid.uuid4()
        db = AsyncMock()

        reforma1 = models.ReformaPoa(id_reforma=uuid.uuid4(), id_poa=id_poa, estado_reforma="Solicitada")
        reforma2 = models.ReformaPoa(id_reforma=uuid.uuid4(), id_poa=id_poa, estado_reforma="Aprobada")

        mock_res = MagicMock()
        mock_res.scalars().all.return_value = [reforma1, reforma2]
        db.execute.return_value = mock_res

        result = await listar_reformas_por_poa(id_poa, db)

        assert len(result) == 2
        assert result[0].estado_reforma == "Solicitada"
        assert result[1].estado_reforma == "Aprobada"

    async def test_obtener_reforma_success(self):
        """Debe obtener una reforma específica por su ID"""
        id_reforma = uuid.uuid4()
        db = AsyncMock()

        reforma = models.ReformaPoa(id_reforma=id_reforma, estado_reforma="Solicitada")

        # obtener_reforma usa db.get, no db.execute
        db.get.return_value = reforma

        result = await obtener_reforma(id_reforma, db)

        assert result.id_reforma == id_reforma
        assert result.estado_reforma == "Solicitada"

    async def test_obtener_reforma_no_encontrada(self):
        """Debe retornar 404 si la reforma no existe"""
        id_reforma = uuid.uuid4()
        db = AsyncMock()

        # obtener_reforma usa db.get, no db.execute
        db.get.return_value = None

        with pytest.raises(HTTPException) as exc:
            await obtener_reforma(id_reforma, db)

        assert exc.value.status_code == 404
        assert "Reforma no encontrada" in str(exc.value.detail)

    async def test_aprobar_reforma_success(self):
        """Debe aprobar una reforma y actualizar el presupuesto del POA"""
        id_reforma = uuid.uuid4()
        id_poa = uuid.uuid4()
        db = AsyncMock()
        usuario = models.Usuario(id_usuario=uuid.uuid4())

        reforma = models.ReformaPoa(
            id_reforma=id_reforma,
            id_poa=id_poa,
            estado_reforma="Solicitada",
            monto_solicitado=Decimal("80000.00")
        )

        # aprobar_reforma solo usa db.get para obtener la reforma
        db.get.return_value = reforma

        result = await aprobar_reforma(id_reforma, db, usuario)

        assert reforma.estado_reforma == "Aprobada"
        assert reforma.id_usuario_aprueba == usuario.id_usuario
        assert db.add.called
        assert db.commit.called
        assert "aprobada exitosamente" in result["msg"]

    async def test_actualizar_precio_detalle_tarea_admin_only(self):
        """Debe permitir actualizar precio solo si es Administrador"""
        id_detalle = uuid.uuid4()
        db = AsyncMock()
        # Usuario NO administrador
        usuario = models.Usuario(id_usuario=uuid.uuid4(), id_rol=uuid.uuid4())
        data = schemas.DetalleTareaUpdatePrecio(precio_unitario=Decimal("1500.00"))

        mock_res_rol = MagicMock()
        mock_res_rol.scalars().first.return_value = models.Rol(nombre_rol="Director")
        db.execute.return_value = mock_res_rol

        with pytest.raises(HTTPException) as exc:
            await actualizar_precio_detalle_tarea(id_detalle, data, db, usuario)
        assert exc.value.status_code == 403
        assert "Solo los administradores" in str(exc.value.detail)

    async def test_actualizar_precio_success(self):
        """Debe actualizar el precio del detalle de tarea para admin"""
        id_detalle = uuid.uuid4()
        db = AsyncMock()
        usuario = models.Usuario(id_usuario=uuid.uuid4(), id_rol=uuid.uuid4())
        data = schemas.DetalleTareaUpdatePrecio(precio_unitario=Decimal("2000.00"))

        mock_res_rol = MagicMock()
        mock_res_rol.scalars().first.return_value = models.Rol(nombre_rol="Administrador")

        detalle = models.DetalleTarea(id_detalle_tarea=id_detalle, precio_unitario=Decimal("1000.00"))
        mock_res_detalle = MagicMock()
        mock_res_detalle.scalars().first.return_value = detalle

        db.execute.side_effect = [mock_res_rol, mock_res_detalle]

        result = await actualizar_precio_detalle_tarea(id_detalle, data, db, usuario)
        assert result.precio_unitario == Decimal("2000.00")
        assert db.commit.called

    async def test_crear_reforma_monto_igual_a_actual(self):
        """Debe rechazar si el monto solicitado es igual al actual"""
        id_poa = uuid.uuid4()
        db = AsyncMock()
        usuario = models.Usuario(id_usuario=uuid.uuid4())
        data = schemas.ReformaPoaCreate(
            id_poa=id_poa,
            monto_solicitado=Decimal("1000.00"),
            justificacion="Sin cambios reales para probar validacion de diferencia de montos"
        )

        poa = models.Poa(id_poa=id_poa, presupuesto_asignado=Decimal("1000.00"))
        mock_res = MagicMock()
        mock_res.scalars().first.side_effect = [poa, usuario]
        db.execute.return_value = mock_res

        with pytest.raises(HTTPException) as exc:
            await crear_reforma_poa(id_poa, data, db, usuario)
        assert exc.value.status_code == 400
        assert "diferente al monto actual" in str(exc.value.detail)
