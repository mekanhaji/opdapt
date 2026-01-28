from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

engine = create_engine(
    "sqlite:///opdapt.db",
    connect_args={"check_same_thread": False}  # needed for SQLite + FastAPI
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
