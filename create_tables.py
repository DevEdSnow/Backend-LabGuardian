
"""Create database tables for LabGuardian AI."""

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import Base, engine, init_db

# Register all SQLAlchemy models before creating tables.
import app.models  # noqa: F401


def main() -> None:
    print("=" * 55)
    print(" LABGUARDIAN AI - DATABASE INITIALIZATION")
    print("=" * 55)

    try:
        with engine.connect() as connection:
            database_name = connection.execute(
                text("SELECT current_database()")
            ).scalar_one()

        print(f"\nConnected database: {database_name}")
        print(f"Registered model tables: {len(Base.metadata.tables)}")

        print("\nCreating missing tables...")
        init_db()

        inspector = inspect(engine)
        tables = sorted(inspector.get_table_names())

        print("\nAvailable tables:")
        for table in tables:
            print(f"  [OK] {table}")

        print(f"\nTotal tables: {len(tables)}")
        print("Database initialization completed successfully.")

    except SQLAlchemyError as exc:
        print("\nDatabase initialization failed.")
        print(f"Error: {exc}")
        raise SystemExit(1) from exc

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
