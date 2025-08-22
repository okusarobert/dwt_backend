import os
from sqlalchemy import create_engine, event, Engine
from sqlalchemy.orm import scoped_session, sessionmaker
from decouple import config
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))


db_url = "postgresql://{user}:{password}@{host}:{port}/{db_name}".format(
    host=config("DB_HOST"),
    port=config("DB_PORT"),
    db_name=config("POSTGRES_DB"),
    user=config("DB_USER"),
    password=config("DB_PASS"),
)

print("db_url: ",db_url)

engine = create_engine(
    db_url, 
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600
)

session = scoped_session(
    sessionmaker(
        autoflush=False,
        autocommit=False,
        bind=engine
    )
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    # cursor.execute("PRAGMA foreign_keys=ON")
    print("db connected")
    cursor.close()


def get_session():
    """Create a new database session"""
    return sessionmaker(
        autoflush=False,
        autocommit=False,
        bind=engine
    )()
