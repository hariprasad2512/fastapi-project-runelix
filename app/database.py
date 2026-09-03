import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


load_dotenv(override=True)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set to a PostgreSQL connection string")
if not DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg2://")):
    raise RuntimeError("DATABASE_URL must use PostgreSQL")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def initialize_database() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    legacy_tables = []
    required_columns = {
        "products": {"id", "name", "category", "price", "quantity", "supplier_id"},
        "suppliers": {"id", "name", "email"},
    }
    for table_name, columns in required_columns.items():
        if table_name in existing_tables:
            current_columns = {column["name"] for column in inspector.get_columns(table_name)}
            if not columns.issubset(current_columns):
                legacy_tables.append(table_name)

    if legacy_tables:
        with engine.begin() as connection:
            for table_name in legacy_tables:
                row_count = connection.exec_driver_sql(
                    f'SELECT COUNT(*) FROM "{table_name}"'
                ).scalar_one()
                if row_count:
                    raise RuntimeError(
                        f"The existing {table_name} table has data but does not match the API schema. "
                        "Migrate it before starting the application."
                    )
                connection.exec_driver_sql(f'DROP TABLE "{table_name}" CASCADE')

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
