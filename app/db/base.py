from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy import Column, Integer, String


@as_declarative()
class Base:
    id = Column(Integer, primary_key=True)
    __name__ = String
    @declared_attr
    def __tablename__(cls):
        """Generate a table name by converting 
        the class name to lowercase."""
        
        return cls.__name__.lower()