#-- Arquivo de gerenciamento de tipos com Modelos pydanticos --#

from sqlalchemy import Column, Integer, String, Boolean
from .database import Base
from pydantic import BaseModel

class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100))
    email = Column(String(100))

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String(50), unique=True, index=True, nullable=False)
    senha = Column(String(255), nullable=False)
    eh_admin = Column(Boolean, default=False)

class UsuarioEntrada(BaseModel):
    usuario: str
    senha: str

class ClienteEntrada(BaseModel):
    nome: str
    email: str
