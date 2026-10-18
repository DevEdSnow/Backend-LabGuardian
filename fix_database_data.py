
"""
Corrección segura de datos de LabGuardian AI.

1. Busca áreas de laboratorio con valor de prueba "string".
2. Muestra los registros antes de modificarlos.
3. Solicita confirmación.
4. Cambia únicamente laboratory_area a "Sin clasificar".
5. No elimina muestras, eventos, alertas ni tablas.
"""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal


def inspect_test_data(db):
    """Busca registros que podrían contener datos de prueba."""

    query = text("""
        SELECT
            id,
            code,
            laboratory_area,
            sample_type
        FROM samples
        WHERE LOWER(TRIM(COALESCE(laboratory_area, ''))) = 'string'
           OR UPPER(TRIM(COALESCE(code, ''))) = 'STRING'
        ORDER BY id;
    """)

    rows = db.execute(query).mappings().all()

    print("\n=== Registros sospechosos ===")

    if not rows:
        print("No se encontraron registros con esos valores.")
        return []

    for row in rows:
        print(
            f"ID: {row['id']} | "
            f"Código: {row['code']} | "
            f"Área: {row['laboratory_area']} | "
            f"Tipo: {row['sample_type']}"
        )

    return rows


def fix_laboratory_areas(db):
    """Corrige exclusivamente las áreas cuyo valor sea 'string'."""

    query = text("""
        UPDATE samples
        SET laboratory_area = 'Sin clasificar'
        WHERE LOWER(TRIM(COALESCE(laboratory_area, ''))) = 'string'
        RETURNING id, code, laboratory_area;
    """)

    updated_rows = db.execute(query).mappings().all()

    print("\n=== Resultado de la corrección ===")

    for row in updated_rows:
        print(
            f"ID: {row['id']} | "
            f"Código: {row['code']} | "
            f"Nueva área: {row['laboratory_area']}"
        )

    print(f"\nÁreas modificadas: {len(updated_rows)}")

    return len(updated_rows)


def main():
    db = SessionLocal()

    try:
        rows = inspect_test_data(db)

        # No continuar si no hay áreas que corregir.
        areas_to_fix = [
            row for row in rows
            if (row["laboratory_area"] or "").strip().lower() == "string"
        ]

        if not areas_to_fix:
            print(
                "\nNo hay áreas 'string' para corregir. "
                "No se realizaron cambios."
            )
            db.rollback()
            return

        print(
            f"\nSe modificarán {len(areas_to_fix)} área(s). "
            "Los códigos de muestra no cambiarán."
        )

        confirmation = input(
            "¿Deseas continuar? Escribe SI para confirmar: "
        ).strip()

        if confirmation != "SI":
            db.rollback()
            print("Operación cancelada. No se guardaron cambios.")
            return

        total = fix_laboratory_areas(db)
        db.commit()

        print(f"\nCambios guardados correctamente: {total}")

    except SQLAlchemyError as exc:
        db.rollback()
        print(f"\nError de base de datos: {exc}")
        print("Se revirtieron los cambios pendientes.")

    except Exception as exc:
        db.rollback()
        print(f"\nError inesperado: {exc}")
        print("Se revirtieron los cambios pendientes.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
