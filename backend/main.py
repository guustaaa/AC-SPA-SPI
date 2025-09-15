#-- Arquivo principal do Backend utilizando FASTAPI

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from . import database, models
from .auth import gerar_hash, verificar_hash
import os

app = FastAPI()

# Monta caminho do frontend
caminho_front = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=caminho_front), name="static")


# Serve a página no caminho root da aplicação (/)
@app.get("/")
def tela_inicial():
    return FileResponse(os.path.join(caminho_front, "index.html"))

# Gerencia o Evento de Inicialização da aplicação e cria usuário administrador no BD

@app.on_event("startup")
def iniciar():
    models.Base.metadata.create_all(bind=database.engine)
    db = database.SessionLocal()
    if not db.query(models.Usuario).filter_by(usuario="admin").first():
        admin = models.Usuario(usuario="admin", senha=gerar_hash("admin123"), eh_admin=True)
        db.add(admin)
        db.commit()
    db.close()

# Linka DB e finaliza graciosamente 
def get_db():
    db_sessao = database.SessionLocal()
    try:
        yield db_sessao
    finally:
        db_sessao.close()

# Rotas de cadastro e listagem de clientes e cliente
@app.post("/clientes/")
def cadastrar_cliente(dados: models.ClienteEntrada, db: Session = Depends(get_db)):
    cliente = models.Cliente(nome=dados.nome, email=dados.email)
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return {"id": cliente.id, "nome": cliente.nome, "email": cliente.email}

@app.get("/clientes/")
def listar_clientes(db: Session = Depends(get_db)):
    return db.query(models.Cliente).all()

@app.get("/clientes/{id_cliente}")
def detalhe_cliente(id_cliente: int, db: Session = Depends(get_db)):
    cliente = db.query(models.Cliente).filter(models.Cliente.id == id_cliente).first()
    if not cliente:
        return {"erro": "Cliente não encontrado"}
    return {"id": cliente.id, "nome": cliente.nome, "email": cliente.email}

# Rotas de cadastro de Usuario """
@app.post("/usuarios/registrar")
def registrar_usuario(dados: models.UsuarioEntrada, db: Session = Depends(get_db)):
    if db.query(models.Usuario).filter_by(usuario=dados.usuario).first():
        raise HTTPException(status_code=400, detail="Usuário já existe")
    novo = models.Usuario(
        usuario=dados.usuario,
        senha=gerar_hash(dados.senha),
        eh_admin=False
    )
    db.add(novo)
    db.commit()
    return {"mensagem": "Usuário cadastrado com sucesso"}

@app.post("/usuarios/login")
def login(dados: models.UsuarioEntrada, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter_by(usuario=dados.usuario).first()
    if not usuario or not verificar_hash(dados.senha, usuario.senha):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return {"mensagem": "Login ok", "eh_admin": usuario.eh_admin}

@app.get("/usuarios/")
def listar_usuarios(db: Session = Depends(get_db)):
    usuarios = db.query(models.Usuario).all()
    return [{"id": u.id, "usuario": u.usuario, "eh_admin": u.eh_admin} for u in usuarios]
