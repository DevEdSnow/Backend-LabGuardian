
"""Initialize the LabGuardian AI database and demo data."""

from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import Base, SessionLocal, engine

# Register all models before creating tables.
import app.models  # noqa: F401

from app.seed.initial_data import seed_initial_data


def main() -> None:
    print("=" * 55)
    print(" LABGUARDIAN AI - DATABASE SEED")
    print("=" * 55)

    db = None

    try:
        # Create tables that do not exist yet.
        Base.metadata.create_all(bind=engine)

        tables = sorted(inspect(engine).get_table_names())
        print(f"\nTables detected: {len(tables)}")

        db = SessionLocal()

        print("Loading demonstration data...")
        result = seed_initial_data(db)

        # Persist all seed operations in one transaction.
        db.commit()

        print("\nSeed completed successfully.")
        if result is not None:
            print(f"Result: {result}")

        print("\nDemo data has been committed to the database.")

    except SQLAlchemyError as exc:
        if db is not None:
            db.rollback()

        print("\nDatabase operation failed.")
        print(f"Error: {exc}")
        raise SystemExit(1) from exc

    except Exception as exc:
        if db is not None:
            db.rollback()

        print("\nSeed initialization failed.")
        print(f"Error: {exc}")
        raise

    finally:
        if db is not None:
            db.close()

        engine.dispose()


if __name__ == "__main__":
    main()
