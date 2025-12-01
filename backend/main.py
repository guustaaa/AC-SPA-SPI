#-- Arquivo principal do Backend utilizando FASTAPI

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from . import database, models, seed
from .auth import gerar_hash, verificar_hash
import os
from datetime import date as dt_date
from typing import Optional
import requests

import pandas as pd
import matplotlib
matplotlib.use('Agg') # Importante para rodar sem interface gráfica (Docker/Server)
import matplotlib.pyplot as plt
import io
import base64


RODAR_SEED = True


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
    # popula o banco baseado em env hardcoded 
    if RODAR_SEED:
        seed.popular_banco(db)
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

#remoção de cliente
@app.delete("/clientes/{id_cliente}")
def remover_cliente(id_cliente: int, db: Session = Depends(get_db)):
    cliente = db.query(models.Cliente).filter(models.Cliente.id == id_cliente).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Validação de vínculos
    vinculos = db.query(models.ContaReceber).filter(models.ContaReceber.cliente_id == id_cliente).first()
    if vinculos:
        raise HTTPException(status_code=400, detail="Cliente não pode ser removido pois possui lançamentos financeiros vinculados.")
    
    db.delete(cliente)
    db.commit()
    return {"mensagem": "Cliente removido com sucesso"}

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

#Rota de Edição de Fornecedor
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


# --- Rota de geração do dashboard ---
# Utiliza de filtros e queries para gerar os graficos com pandas e matplotlib

@app.post("/dashboard/gerar")
def gerar_dashboard(filtros: models.DashboardFiltro, db: Session = Depends(get_db)):
    # Gera as queries com base nos modelos pydanticos

    query_rec = db.query(models.ContaReceber)
    query_pag = db.query(models.ContaPagar)

    #aplica os filtros enviados por front
    if filtros.data_inicio:
        query_rec = query_rec.filter(models.ContaReceber.data_vencimento >= filtros.data_inicio)
        query_pag = query_pag.filter(models.ContaPagar.data_vencimento >= filtros.data_inicio)
    
    if filtros.data_fim:
        query_rec = query_rec.filter(models.ContaReceber.data_vencimento <= filtros.data_fim)
        query_pag = query_pag.filter(models.ContaPagar.data_vencimento <= filtros.data_fim)

    if filtros.status:
        query_rec = query_rec.filter(models.ContaReceber.status == filtros.status)
        query_pag = query_pag.filter(models.ContaPagar.status == filtros.status)

    if filtros.fornecedor_id:
        query_pag = query_pag.filter(models.ContaPagar.fornecedor_id == filtros.fornecedor_id)
    
    contas_rec = query_rec.all()
    contas_pag = query_pag.all()

    # Cria imagens de graficos base64 com pandas e plt de matplot

    # Pagamentos
    dados_pag = []
    for c in contas_pag:
        nome_fornecedor = c.fornecedor.nome_fantasia if c.fornecedor else "Desconhecido"
        #fluxo de caixa o valor deve ser negativo
        dados_pag.append({
            "data": c.data_vencimento,
            "valor": -abs(c.valor), 
            "valor_abs": c.valor,
            "status": c.status, 
            "fornecedor": nome_fornecedor,
            "tipo": "despesa"
        })
    
    # Recebimentos
    dados_rec = []
    for c in contas_rec:
        dados_rec.append({
            "data": c.data_vencimento,
            "valor": abs(c.valor),
            "valor_abs": c.valor,
            "status": c.status,
            "tipo": "receita"
        })
    
    df_pag = pd.DataFrame(dados_pag)
    df_rec = pd.DataFrame(dados_rec)

    # Cria os data frames vazios para preenchimento posterior
    if df_pag.empty: df_pag = pd.DataFrame(columns=['data', 'valor', 'valor_abs', 'status', 'fornecedor', 'tipo'])
    if df_rec.empty: df_rec = pd.DataFrame(columns=['data', 'valor', 'valor_abs', 'status', 'tipo'])

    # Valores totais para os cards
    total_receitas = df_rec['valor_abs'].sum() if not df_rec.empty else 0
    total_despesas = df_pag['valor_abs'].sum() if not df_pag.empty else 0
    total_pagar_pendente = df_pag[df_pag['status'] != 'pago']['valor_abs'].sum() if not df_pag.empty else 0
    total_pagar_pago = df_pag[df_pag['status'] == 'pago']['valor_abs'].sum() if not df_pag.empty else 0

    # Geração dos gráficos 

    # 1 - Pizza pendente por fornecedor
    img_pizza_forn = None
    df_pendentes = df_pag[df_pag['status'] != 'pago']
    if not df_pendentes.empty:
        df_pizza = df_pendentes.groupby('fornecedor')['valor_abs'].sum()
        fig1, ax1 = plt.subplots(figsize=(6, 4))
        ax1.pie(df_pizza, labels=df_pizza.index, autopct='%1.1f%%', startangle=140)
        ax1.set_title('Dívida Aberta por Fornecedor')
        buf1 = io.BytesIO()
        fig1.savefig(buf1, format='png', bbox_inches='tight')
        buf1.seek(0)
        img_pizza_forn = base64.b64encode(buf1.read()).decode('utf-8')
        plt.close(fig1)


    # 2 - Barras pago x pendente
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    cats = ['Pago', 'Pendente/Vencido']
    vals = [total_pagar_pago, total_pagar_pendente]
    barras = ax2.bar(cats, vals, color=['#4CAF50', '#E74C3C'])
    ax2.set_title('Situação Geral (Contas a Pagar)')
    for barra in barras:
        height = barra.get_height()
        ax2.text(barra.get_x() + barra.get_width()/2., height, f'R$ {height:.2f}', ha='center', va='bottom')
    buf2 = io.BytesIO()
    fig2.savefig(buf2, format='png', bbox_inches='tight')
    buf2.seek(0)
    img_barras_pag = base64.b64encode(buf2.read()).decode('utf-8')
    plt.close(fig2)

    # 3 - Barras emplilhadas, fornecedor x pendentes
    img_forn_detalhado = None
    if not df_pag.empty:

        # Cria df dinâmico: Linhas=Fornecedor, Colunas=Status, Valores=Soma
        # - status 'Pago' e 'Pendente'
        df_pag['status_simples'] = df_pag['status'].apply(lambda x: 'Pago' if x == 'pago' else 'Pendente')
        
        pivot_forn = df_pag.pivot_table(index='fornecedor', columns='status_simples', values='valor_abs', aggfunc='sum', fill_value=0)
        
        fig3, ax3 = plt.subplots(figsize=(8, 5)) # Um pouco mais largo
        # Plota barras empilhadas
        pivot_forn.plot(kind='bar', stacked=True, color={'Pago': '#4CAF50', 'Pendente': '#E74C3C'}, ax=ax3)
        ax3.set_title('Pagamentos por Fornecedor (Pago vs Pendente)')
        ax3.set_ylabel('Valor (R$)')
        ax3.set_xlabel('Fornecedor')
        plt.xticks(rotation=45, ha='right') # Rotação para ler os nomes
        
        buf3 = io.BytesIO()
        fig3.savefig(buf3, format='png', bbox_inches='tight')
        buf3.seek(0)
        img_forn_detalhado = base64.b64encode(buf3.read()).decode('utf-8')
        plt.close(fig3)

    # 4 - Gráfico de linha x tempo
    img_linha_tempo = None
    # Junta os dois dfs
    df_total = pd.concat([df_rec, df_pag], sort=False)
    
    if not df_total.empty:
        # Agrupa por data e soma os valores + receita - despesa
        df_tempo = df_total.groupby('data')['valor'].sum().sort_index().cumsum()
        
        fig4, ax4 = plt.subplots(figsize=(10, 4))
        ax4.plot(df_tempo.index, df_tempo.values, marker='o', linestyle='-', color='#2980b9', linewidth=2)
        ax4.set_title('Evolução do Saldo Acumulado (Período Selecionado)')
        ax4.set_ylabel('Saldo Acumulado (R$)')
        ax4.grid(True, linestyle='--', alpha=0.6)
        
        # Formata data no eixo X
        fig4.autofmt_xdate()
        
        buf4 = io.BytesIO()
        fig4.savefig(buf4, format='png', bbox_inches='tight')
        buf4.seek(0)
        img_linha_tempo = base64.b64encode(buf4.read()).decode('utf-8')
        plt.close(fig4)
    # Retorna totais e as images em base64
    return {
        "resumo": {
            "total_rec": total_receitas,
            "total_pag": total_despesas,
            "total_aberto": total_pagar_pendente,
            "saldo": total_receitas - total_despesas
        },
        "graficos": {
            "pizza_fornecedor": f"data:image/png;base64,{img_pizza_forn}" if img_pizza_forn else None,
            "barras_geral": f"data:image/png;base64,{img_barras_pag}",
            "barras_fornecedor": f"data:image/png;base64,{img_forn_detalhado}" if img_forn_detalhado else None,
            "linha_tempo": f"data:image/png;base64,{img_linha_tempo}" if img_linha_tempo else None
        }
    }