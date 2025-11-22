"""agregar_departamento

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-11-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    """Agregar tabla DEPARTAMENTO y columna id_departamento a PROYECTO.

    **Objetivo:** Permitir clasificar proyectos por departamento institucional
    para facilitar filtrados y reportes.

    **Cambios:**
    - Crear tabla `DEPARTAMENTO` con id_departamento, nombre, descripcion
    - Agregar columna `id_departamento` a la tabla PROYECTO como FK nullable
    """
    # Crear tabla DEPARTAMENTO
    op.create_table(
        'DEPARTAMENTO',
        sa.Column('id_departamento', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nombre', sa.String(100), nullable=False),
        sa.Column('descripcion', sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint('id_departamento')
    )

    # Agregar columna id_departamento a PROYECTO
    op.add_column(
        'PROYECTO',
        sa.Column('id_departamento', postgresql.UUID(as_uuid=True), nullable=True)
    )

    # Crear foreign key constraint
    op.create_foreign_key(
        'fk_proyecto_departamento',
        'PROYECTO',
        'DEPARTAMENTO',
        ['id_departamento'],
        ['id_departamento']
    )


def downgrade():
    """Revertir la adición del departamento.

    **Operación:**
    - Eliminar FK constraint
    - Eliminar columna `id_departamento` de PROYECTO
    - Eliminar tabla `DEPARTAMENTO`
    """
    # Eliminar foreign key
    op.drop_constraint('fk_proyecto_departamento', 'PROYECTO', type_='foreignkey')

    # Eliminar columna
    op.drop_column('PROYECTO', 'id_departamento')

    # Eliminar tabla
    op.drop_table('DEPARTAMENTO')
