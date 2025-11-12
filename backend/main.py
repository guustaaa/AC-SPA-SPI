#-- Arquivo principal do Backend utilizando FASTAPI

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from . import database, models
from .auth import gerar_hash, verificar_hash
import os
from datetime import date as dt_date
from typing import Optional
import requests # Importado

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

# --- Rotas de Clientes ---

@app.post("/clientes/")
def cadastrar_cliente(dados: models.ClienteEntrada, db: Session = Depends(get_db)):
    #Validação de campos obrigatórios
    if not dados.cnpj or not dados.razao_social:
        raise HTTPException(status_code=400, detail="CNPJ e Razão Social são obrigatórios")
    #Validação de CNPJ único
    if db.query(models.Cliente).filter_by(cnpj=dados.cnpj).first():
        raise HTTPException(status_code=400, detail="CNPJ já cadastrado")

    #Cria cliente com todos os dados
    cliente = models.Cliente(**dados.dict())
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente

#Rota de Edição de Cliente
@app.put("/clientes/{id_cliente}")
def editar_cliente(id_cliente: int, dados: models.ClienteEntrada, db: Session = Depends(get_db)):
    cliente = db.query(models.Cliente).filter(models.Cliente.id == id_cliente).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    #Validação de vínculos
    vinculos = db.query(models.ContaReceber).filter(models.ContaReceber.cliente_id == id_cliente).first()
    if vinculos:
        raise HTTPException(status_code=400, detail="Cliente não pode ser editado pois possui lançamentos financeiros vinculados.")
        
    #Validação de CNPJ duplicado na edição
    if dados.cnpj != cliente.cnpj:
        if db.query(models.Cliente).filter_by(cnpj=dados.cnpj).first():
            raise HTTPException(status_code=400, detail="Este CNPJ já pertence a outro cliente")

    update_data = dados.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(cliente, key, value)
    
    db.commit()
    db.refresh(cliente)
    return cliente

@app.get("/clientes/")
def listar_clientes(db: Session = Depends(get_db)):
    return db.query(models.Cliente).all()

@app.get("/clientes/{id_cliente}")
def detalhe_cliente(id_cliente: int, db: Session = Depends(get_db)):
    cliente = db.query(models.Cliente).filter(models.Cliente.id == id_cliente).first()
    if not cliente:
        return {"erro": "Cliente não encontrado"}
    return cliente #Retorna o objeto completo

#Rota de consulta CNPJ
@app.get("/consulta-cnpj/{cnpj}")
def consulta_cnpj_real(cnpj: str):
    # Limpa CNPJ
    cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
    if len(cnpj_limpo) != 14:
        raise HTTPException(status_code=400, detail="CNPJ inválido")
    
    try:
        # URL da API CNPJa
        url = f"https://open.cnpja.com/office/{cnpj_limpo}"
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        #guarda json
        dados = res.json()
        
        #extrai empresa e adress
        company = dados.get('company', {})
        address = dados.get('address', {})
        
        # Pega o primeiro email
        emails = dados.get('emails', [])
        email = emails[0].get('address') if emails else None
        
        # Pega a primeira IE
        registrations = dados.get('registrations', [])
        ie = registrations[0].get('number') if registrations else None

        # Mapeia a resposta
        return JSONResponse({
            "razao_social": company.get('name'),
            "nome_fantasia": dados.get('alias'),
            "rua": address.get('street'),
            "numero": address.get('number'),
            "bairro": address.get('district'),
            "cidade": address.get('city'),
            "estado": address.get('state'),
            "cep": address.get('zip'),
            "ie": ie,
            "email": email
        })

    except requests.exceptions.HTTPError as e:
        #trata erros por http status code
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="CNPJ não encontrado na API CNPJa")
        raise HTTPException(status_code=e.response.status_code, detail=f"Erro da API: {e.response.text}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Erro ao conectar à API CNPJa: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao processar CNPJ: {str(e)}")

# --- Rotas de Usuários ---

@app.post("/usuarios/registrar")
def registrar_usuario(dados: models.UsuarioEntrada, db: Session = Depends(get_db)):
    #Validação simples
    if not dados.usuario or not dados.senha:
        raise HTTPException(status_code=400, detail="Usuário e Senha são obrigatórios")
    if db.query(models.Usuario).filter_by(usuario=dados.usuario).first():
        raise HTTPException(status_code=400, detail="Usuário já existe")
    novo = models.Usuario(usuario=dados.usuario, senha=gerar_hash(dados.senha), eh_admin=False)
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

#Rota de configs do usuário
@app.get("/usuarios/{id_usuario}")
def detalhe_usuario(id_usuario: int, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == id_usuario).first()
    if not usuario:
        return {"erro": "Usuário não encontrado"}
    return {"id": usuario.id, "usuario": usuario.usuario, "eh_admin": usuario.eh_admin}

#Rotas de Fornecedores


@app.post("/fornecedores/")
def cadastrar_fornecedor(dados: models.FornecedorEntrada, db: Session = Depends(get_db)):
    if not dados.cnpj or not dados.razao_social:
        raise HTTPException(status_code=400, detail="CNPJ e Razão Social são obrigatórios")
    if db.query(models.Fornecedor).filter_by(cnpj=dados.cnpj).first():
        raise HTTPException(status_code=400, detail="CNPJ já cadastrado")
    fornecedor = models.Fornecedor(**dados.dict())
    db.add(fornecedor)
    db.commit()
    db.refresh(fornecedor)
    return fornecedor

# (Novo) Rota de Edição de Fornecedor
@app.put("/fornecedores/{id_fornecedor}")
def editar_fornecedor(id_fornecedor: int, dados: models.FornecedorEntrada, db: Session = Depends(get_db)):
    #Verifica se fornecedor existe
    fornecedor = db.query(models.Fornecedor).filter(models.Fornecedor.id == id_fornecedor).first()
    if not fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")

    #Verifica vínculos financeiros (Contas a Pagar)
    vinculos = db.query(models.ContaPagar).filter(models.ContaPagar.fornecedor_id == id_fornecedor).first()
    if vinculos:
        raise HTTPException(status_code=400, detail="Fornecedor não pode ser editado pois possui lançamentos financeiros vinculados.")
        
    #Verifica se o CNPJ está sendo alterado para um que já existe
    if dados.cnpj != fornecedor.cnpj:
        if db.query(models.Fornecedor).filter_by(cnpj=dados.cnpj).first():
            raise HTTPException(status_code=400, detail="Este CNPJ já pertence a outro fornecedor")

    # Atualiza os campos
    update_data = dados.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(fornecedor, key, value)
    
    db.commit()
    db.refresh(fornecedor)
    return fornecedor

@app.get("/fornecedores/")
def listar_fornecedores(db: Session = Depends(get_db)):
    return db.query(models.Fornecedor).all()

@app.get("/fornecedores/{id_fornecedor}")
def detalhe_fornecedor(id_fornecedor: int, db: Session = Depends(get_db)):
    fornecedor = db.query(models.Fornecedor).filter(models.Fornecedor.id == id_fornecedor).first()
    if not fornecedor:
        return {"erro": "Fornecedor não encontrado"}
    return fornecedor
    
#Rotas Contareceber/Contapagar
@app.post("/contas-receber/")
def cadastrar_conta_receber(dados: models.ContaReceberEntrada, db: Session = Depends(get_db)):
    if not dados.cliente_id or not dados.descricao or not dados.valor or not dados.data_vencimento:
        raise HTTPException(status_code=400, detail="Campos obrigatórios não preenchidos")
    conta = models.ContaReceber(**dados.dict())
    db.add(conta)
    db.commit()
    db.refresh(conta)
    return conta

@app.get("/contas-receber/")
def listar_contas_receber(
    db: Session = Depends(get_db),
    cliente_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    data_inicio: Optional[dt_date] = Query(None),
    data_fim: Optional[dt_date] = Query(None)
):
    query = db.query(models.ContaReceber).join(models.Cliente)
    if cliente_id:
        query = query.filter(models.ContaReceber.cliente_id == cliente_id)
    if status:
        query = query.filter(models.ContaReceber.status == status)
    if data_inicio:
        query = query.filter(models.ContaReceber.data_vencimento >= data_inicio)
    if data_fim:
        query = query.filter(models.ContaReceber.data_vencimento <= data_fim)
    
    contas = query.all()
    # Retorna lista com nome do cliente
    return [
        {
            "id": c.id, 
            "descricao": c.descricao, 
            "valor": c.valor, 
            "valor_pago": c.valor_pago,
            "data_vencimento": c.data_vencimento, 
            "status": c.status,
            "cliente_nome": c.cliente.nome_fantasia or c.cliente.razao_social
        } 
        for c in contas
    ]

@app.get("/contas-receber/{id_conta}") 
def detalhe_conta_receber(id_conta: int, db: Session = Depends(get_db)):
    conta = db.query(models.ContaReceber).filter(models.ContaReceber.id == id_conta).first()
    if not conta:
        return {"erro": "Conta não encontrada"}
    return conta

@app.put("/contas-receber/{id_conta}/pagar") 
def pagar_conta_receber(id_conta: int, dados: models.PagamentoUpdate, db: Session = Depends(get_db)):
    conta = db.query(models.ContaReceber).filter(models.ContaReceber.id == id_conta).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
    conta.valor_pago = dados.valor_pago
    
    # Atualiza status baseado no valor pago
    if conta.valor_pago >= conta.valor:
        conta.status = "pago"
    else:
        conta.status = "pendente" 
    
    db.commit()
    db.refresh(conta)
    return conta

@app.post("/contas-pagar/")
def cadastrar_conta_pagar(dados: models.ContaPagarEntrada, db: Session = Depends(get_db)):
    if not dados.fornecedor_id or not dados.descricao or not dados.valor or not dados.data_vencimento:
        raise HTTPException(status_code=400, detail="Campos obrigatórios não preenchidos")
    conta = models.ContaPagar(**dados.dict())
    db.add(conta)
    db.commit()
    db.refresh(conta)
    return conta

@app.get("/contas-pagar/")
def listar_contas_pagar(
    db: Session = Depends(get_db),
    fornecedor_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    data_inicio: Optional[dt_date] = Query(None),
    data_fim: Optional[dt_date] = Query(None)
):
    query = db.query(models.ContaPagar).join(models.Fornecedor)
    if fornecedor_id:
        query = query.filter(models.ContaPagar.fornecedor_id == fornecedor_id)
    if status:
        query = query.filter(models.ContaPagar.status == status)
    if data_inicio:
        query = query.filter(models.ContaPagar.data_vencimento >= data_inicio)
    if data_fim:
        query = query.filter(models.ContaPagar.data_vencimento <= data_fim)

    contas = query.all()
    # Retorna lista com nome do fornecedor
    return [
        {
            "id": c.id, 
            "descricao": c.descricao, 
            "valor": c.valor,
            "valor_pago": c.valor_pago,
            "data_vencimento": c.data_vencimento, 
            "status": c.status,
            "fornecedor_nome": c.fornecedor.nome_fantasia or c.fornecedor.razao_social
        } 
        for c in contas
    ]

@app.get("/contas-pagar/{id_conta}") 
def detalhe_conta_pagar(id_conta: int, db: Session = Depends(get_db)):
    conta = db.query(models.ContaPagar).filter(models.ContaPagar.id == id_conta).first()
    if not conta:
        return {"erro": "Conta não encontrada"}
    return conta

@app.put("/contas-pagar/{id_conta}/pagar") 
def pagar_conta_pagar(id_conta: int, dados: models.PagamentoUpdate, db: Session = Depends(get_db)):
    conta = db.query(models.ContaPagar).filter(models.ContaPagar.id == id_conta).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
        
    conta.valor_pago = dados.valor_pago
    
    # Atualiza status
    if conta.valor_pago >= conta.valor:
        conta.status = "pago"
    else:
        conta.status = "pendente"
        
    db.commit()
    db.refresh(conta)
    return conta