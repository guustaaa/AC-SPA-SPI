#-- Arquivo de gerenciamento de tipos com Modelos pydanticos --#

from sqlalchemy import Column, Integer, String, Boolean, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from pydantic import BaseModel
from typing import Optional
from datetime import date as dt_date

# --- Modelos do Banco (SQLAlchemy) ---

class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    
    #Campos CNPJ
    cnpj = Column(String(20), unique=True, index=True)
    ie = Column(String(20))
    razao_social = Column(String(255))
    nome_fantasia = Column(String(255))
    
    #campos antigos
    nome = Column(String(100)) 
    email = Column(String(100))
     
    #Endereço
    rua = Column(String(255))
    numero = Column(String(20))
    bairro = Column(String(100))
    cidade = Column(String(100))
    estado = Column(String(2))
    cep = Column(String(10))
    
    #Relacionamento
    contas_receber = relationship("ContaReceber", back_populates="cliente")

#Fornecedor
class Fornecedor(Base):
    __tablename__ = "fornecedores"
    id = Column(Integer, primary_key=True, index=True)
    
    cnpj = Column(String(20), unique=True, index=True)
    ie = Column(String(20))
    razao_social = Column(String(255))
    nome_fantasia = Column(String(255))
    email = Column(String(100))
    
    rua = Column(String(255))
    numero = Column(String(20))
    bairro = Column(String(100))
    cidade = Column(String(100))
    estado = Column(String(2))
    cep = Column(String(10))
    
    # Relacionamento
    contas_pagar = relationship("ContaPagar", back_populates="fornecedor")

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String(50), unique=True, index=True, nullable=False)
    senha = Column(String(255), nullable=False)
    eh_admin = Column(Boolean, default=False)

#Contas a Receber
class ContaReceber(Base):
    __tablename__ = "contas_receber"
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    descricao = Column(String(255), nullable=False)
    valor = Column(Float, nullable=False)
    valor_pago = Column(Float, nullable=False, default=0.0) # Valor efetivamente pago
    data_vencimento = Column(Date, nullable=False)
    status = Column(String(20), default="pendente") # pendente, pago, vencido
    
    cliente = relationship("Cliente", back_populates="contas_receber")

#Contas a Pagar
class ContaPagar(Base):
    __tablename__ = "contas_pagar"
    id = Column(Integer, primary_key=True, index=True)
    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id"))
    descricao = Column(String(255), nullable=False)
    valor = Column(Float, nullable=False)
    valor_pago = Column(Float, nullable=False, default=0.0) # Valor efetivamente pago
    data_vencimento = Column(Date, nullable=False)
    status = Column(String(20), default="pendente") # pendente, pago, vencido
    
    fornecedor = relationship("Fornecedor", back_populates="contas_pagar")


# --- Modelos de Entrada/Saída ---

class UsuarioEntrada(BaseModel):
    usuario: str
    senha: str

#entrada do Cliente
class ClienteEntrada(BaseModel):
    nome: Optional[str] = None
    email: Optional[str] = None
    cnpj: str
    ie: Optional[str] = None
    razao_social: str
    nome_fantasia: Optional[str] = None
    rua: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None
    
    class Config:
        orm_mode = True

#entrada do Fornecedor
class FornecedorEntrada(BaseModel):
    email: Optional[str] = None
    cnpj: str
    ie: Optional[str] = None
    razao_social: str
    nome_fantasia: Optional[str] = None
    rua: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None

    class Config:
        orm_mode = True

#entrada Conta a Receber
class ContaReceberEntrada(BaseModel):
    cliente_id: int
    descricao: str
    valor: float
    data_vencimento: dt_date
    status: Optional[str] = "pendente"

#entrada Conta a Pagar
class ContaPagarEntrada(BaseModel):
    fornecedor_id: int
    descricao: str
    valor: float
    data_vencimento: dt_date
    status: Optional[str] = "pendente"

#atualização de pagamento
class PagamentoUpdate(BaseModel):
    valor_pago: float