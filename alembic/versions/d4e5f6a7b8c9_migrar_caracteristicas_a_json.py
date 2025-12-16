"""migrar_caracteristicas_a_json

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2025-12-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import json

# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    """Migrar campo características de formato posicional a JSON.

    **Objetivo:**
    Cambiar el formato del campo `caracteristicas` de DetalleTarea
    de formato posicional "X.X; Y.Y; Z.Z" a JSON auto-documentado.

    **Formato Anterior:**
    "9.1; 0; 9.1" donde posiciones representan:
    - Índice 0: PIM
    - Índice 1: PTT
    - Índice 2: PVIF/PVIS/PIGR/PIS/PIIF (todos los demás)

    **Formato Nuevo:**
    {"PIM": "9.1", "PTT": null, "OTROS": "9.1"}

    **Cambios:**
    - Convertir todos los registros existentes al nuevo formato
    - "0" se convierte en null (JSON)
    - Mantiene mismo tipo de columna (String)
    """

    bind = op.get_bind()

    # Obtener todos los registros con características
    result = bind.execute(text(
        "SELECT id_detalle_tarea, caracteristicas FROM \"DETALLE_TAREA\" WHERE caracteristicas IS NOT NULL"
    ))

    registros = result.fetchall()

    # Convertir cada registro
    for registro in registros:
        id_detalle = str(registro[0])
        carac_antigua = registro[1]

        if not carac_antigua:
            continue

        # Parsear formato antiguo "X.X; Y.Y; Z.Z"
        partes = carac_antigua.split('; ')

        if len(partes) != 3:
            # Si no tiene el formato esperado, mantener original
            continue

        # Convertir a nuevo formato JSON
        pim_val = None if partes[0] == '0' else partes[0]
        ptt_val = None if partes[1] == '0' else partes[1]
        otros_val = None if partes[2] == '0' else partes[2]

        # IMPORTANTE: sort_keys=True y separators consistentes
        # Esto garantiza formato idéntico al usado en init_data.py
        carac_nueva = json.dumps({
            "PIM": pim_val,
            "PTT": ptt_val,
            "OTROS": otros_val
        }, sort_keys=True, separators=(',', ':'))

        # Actualizar registro
        bind.execute(
            text(
                'UPDATE "DETALLE_TAREA" SET caracteristicas = :carac '
                'WHERE id_detalle_tarea = :id'
            ),
            {"carac": carac_nueva, "id": id_detalle}
        )

    print(f"✅ Migrados {len(registros)} registros de características a formato JSON")


def downgrade():
    """Revertir características de JSON a formato posicional.

    **Operación:**
    Convertir de JSON {"PIM": "9.1", "PTT": null, "OTROS": "9.1"}
    de vuelta a formato posicional "9.1; 0; 9.1"
    """

    bind = op.get_bind()

    # Obtener todos los registros con características
    result = bind.execute(text(
        "SELECT id_detalle_tarea, caracteristicas FROM \"DETALLE_TAREA\" WHERE caracteristicas IS NOT NULL"
    ))

    registros = result.fetchall()

    # Convertir cada registro
    for registro in registros:
        id_detalle = str(registro[0])
        carac_json = registro[1]

        if not carac_json:
            continue

        try:
            # Parsear JSON
            carac_dict = json.loads(carac_json)

            # Convertir de vuelta a formato posicional
            pim = carac_dict.get("PIM") or "0"
            ptt = carac_dict.get("PTT") or "0"
            otros = carac_dict.get("OTROS") or "0"

            carac_antigua = f"{pim}; {ptt}; {otros}"

            # Actualizar registro
            bind.execute(
                text(
                    'UPDATE "DETALLE_TAREA" SET caracteristicas = :carac '
                    'WHERE id_detalle_tarea = :id'
                ),
                {"carac": carac_antigua, "id": id_detalle}
            )
        except json.JSONDecodeError:
            # Si no es JSON válido, asumir que ya está en formato antiguo
            continue

    print(f"✅ Revertidos {len(registros)} registros de JSON a formato posicional")
