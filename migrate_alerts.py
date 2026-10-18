
"""
LabGuardian AI - Migración de la tabla alerts.

Agrega las columnas y restricciones necesarias sin eliminar
las alertas, muestras ni eventos existentes.
"""

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import engine


def migrate_alerts() -> None:
    """Update the alerts table safely and transactionally."""

    print("Iniciando migración de la tabla alerts...")

    try:
        with engine.begin() as connection:
            inspector = inspect(connection)

            if not inspector.has_table("alerts"):
                raise RuntimeError(
                    "La tabla 'alerts' no existe. "
                    "Verifica que el modelo Alert esté registrado "
                    "y que la base de datos esté inicializada."
                )

            if not inspector.has_table("sample_events"):
                raise RuntimeError(
                    "La tabla 'sample_events' no existe."
                )

            columns = {
                column["name"]
                for column in inspector.get_columns("alerts")
            }

            # 1. Agregar columnas faltantes.
            migrations = {
                "event_id": """
                    ALTER TABLE alerts
                    ADD COLUMN IF NOT EXISTS event_id INTEGER
                """,
                "acknowledged_at": """
                    ALTER TABLE alerts
                    ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMPTZ
                """,
                "acknowledged_by": """
                    ALTER TABLE alerts
                    ADD COLUMN IF NOT EXISTS acknowledged_by VARCHAR(100)
                """,
            }

            for column_name, statement in migrations.items():
                if column_name not in columns:
                    connection.execute(text(statement))
                    print(f"Columna agregada: {column_name}")
                else:
                    print(f"Columna existente: {column_name}")

            # 2. Crear índice único para evitar alertas duplicadas
            # para un mismo evento.
            connection.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_alerts_event_id
                ON alerts (event_id)
            """))
            print("Índice único verificado.")

            # 3. Agregar la clave foránea si aún no existe.
            connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname =
                            'fk_alerts_event_id_sample_events'
                    ) THEN
                        ALTER TABLE alerts
                        ADD CONSTRAINT
                            fk_alerts_event_id_sample_events
                        FOREIGN KEY (event_id)
                        REFERENCES sample_events(id)
                        ON DELETE SET NULL;
                    END IF;
                END
                $$;
            """))
            print("Relación con sample_events verificada.")

        print("\nMigración completada correctamente.")
        print("No se eliminaron datos existentes.")

    except (SQLAlchemyError, RuntimeError) as error:
        print("\nERROR durante la migración:")
        print(error)
        raise


if __name__ == "__main__":
    migrate_alerts()
