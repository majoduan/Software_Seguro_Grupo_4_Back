"""agregar_numero_actividad_a_actividad

Revision ID: a1b2c3d4e5f6
Revises: 429563bb5914
Create Date: 2025-11-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '429563bb5914'
branch_labels = None
depends_on = None


def upgrade():
    """Agregar columna numero_actividad a la tabla ACTIVIDAD.

    **Objetivo:** Permitir el ordenamiento de actividades según su número secuencial
    extraído del archivo Excel (1, 2, 3, ...).

    **Cambios:**
    - Agregar columna `numero_actividad` de tipo INTEGER, nullable=True
    - Esto permite mantener el orden original de las actividades del Excel
    - Mejora la visualización de actividades en el frontend
    """
    op.add_column('ACTIVIDAD', sa.Column('numero_actividad', sa.Integer(), nullable=True))


def downgrade():
    """Revertir la adición de la columna numero_actividad.

    **Operación:**
    - Eliminar la columna `numero_actividad` de la tabla ACTIVIDAD
    """
    op.drop_column('ACTIVIDAD', 'numero_actividad')
