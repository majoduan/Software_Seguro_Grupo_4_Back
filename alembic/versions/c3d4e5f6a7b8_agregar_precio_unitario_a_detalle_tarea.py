"""agregar_precio_unitario_a_detalle_tarea

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2025-12-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    """Agregar columna precio_unitario a DETALLE_TAREA.

    **Objetivo:** Centralizar precios predefinidos de servicios profesionales
    en la base de datos en lugar de mantenerlos hardcodeados en el frontend.

    **Cambios:**
    - Agregar columna `precio_unitario` a la tabla DETALLE_TAREA (nullable)
    - Solo los 4 detalles de "Contratación de servicios profesionales" tendrán valores
    """
    op.add_column(
        'DETALLE_TAREA',
        sa.Column('precio_unitario', sa.Numeric(10, 2), nullable=True)
    )


def downgrade():
    """Revertir la adición del precio_unitario.

    **Operación:**
    - Eliminar columna `precio_unitario` de DETALLE_TAREA
    """
    op.drop_column('DETALLE_TAREA', 'precio_unitario')
