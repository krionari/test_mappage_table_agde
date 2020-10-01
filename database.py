import uuid
from sqlalchemy import (LargeBinary, TypeDecorator, create_engine, types, event)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

engine = create_engine(
    os.getenv('DATABASE_URL'), echo=True
)

if 'sqlite' in os.getenv('DATABASE_URL'):
    def _fk_pragma_on_connect(dbapi_con, con_record):
        dbapi_con.execute('pragma foreign_keys=ON')

    event.listen(engine, 'connect', _fk_pragma_on_connect)

    engine.execute('pragma foreign_keys=on')

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

BaseFdb = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# noinspection PyAbstractClass
class UUID(TypeDecorator):
    impl = LargeBinary

    def __init__(self):
        self.impl.length = 16
        types.TypeDecorator.__init__(self, length=self.impl.length)

    def process_bind_param(self, value, dialect=None):
        if value and isinstance(value, uuid.UUID):
            return value.bytes
        elif value and not isinstance(value, uuid.UUID):
            raise ValueError('value %s is not a valid uuid.UUID' % value)
        else:
            return None

    def process_result_value(self, value, dialect=None):
        if value:
            return uuid.UUID(bytes=value)
        else:
            return None

    @staticmethod
    def is_mutable():
        return False
