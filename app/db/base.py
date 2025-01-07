from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy import String


@as_declarative()
class Base:
    __name__ = String

    @declared_attr
    def __tablename__(cls):
        """Generate a table name by converting
        the class name to lowercase."""

        return cls.__name__.lower()
