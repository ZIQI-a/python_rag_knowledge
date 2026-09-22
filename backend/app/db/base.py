""" SQL Alchemy 2.0声明时期内，所有ORM模型都继承自Base """

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
