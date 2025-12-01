# Geração de registros dummys para testar os graficos sem ter que inserir manualmente
from sqlalchemy.orm import Session
from . import models
from datetime import date, timedelta
import random

def popular_banco(db: Session):


    # --- 1. Clientes ---
    # Gera ids de clientes com um for mudando apenas o ultimo digito do cnpj
    nomes_clientes = ["Mercado-Hortifruti", "Padaria", "Tech Solutions", "Consultoria Alpha", "Loja Beta"]
    clientes_objs = []
    for i, nome in enumerate(nomes_clientes):
        c = models.Cliente(
            cnpj=f"1111111100010{i}",
            razao_social=f"{nome} LTDA",
            nome_fantasia=nome,
            email=f"contato{i}@teste.com",
            rua="Rua Exemplo",
            numero=str(i+100),
            bairro="Centro",
            cidade="São Paulo",
            estado="SP",
            cep="01000000"
        )
        db.add(c)
        clientes_objs.append(c)
    
    # Commita parcialmente para gerar ids
    db.commit()
    for c in clientes_objs: db.refresh(c)

    # --- Fornecedores ---
    nomes_forn = ["Distribuidora de Bebidas", "Atacadao", "Serviços de TI", "Produtos de limpeza", "Energia--Enel"]
    forn_objs = []
    for i, nome in enumerate(nomes_forn):
        f = models.Fornecedor(
            cnpj=f"2222222200010{i}",
            razao_social=f"{nome} LTDA",
            nome_fantasia=nome,
            email=f"vendas{i}@teste.com",
            rua="Av Industrial",
            numero=str(i+500),
            bairro="Distrito Ind",
            cidade="Campinas",
            estado="SP",
            cep="13000000"
        )
        db.add(f)
        forn_objs.append(f)
    
    db.commit()
    for f in forn_objs: db.refresh(f)

    #Gera recebimentos e pagamentos de maneira aleatória, utiliza valores aleatórios e iterações com peso/probalidade

    # --- Contas a Receber

    hoje = date.today()
    
    for _ in range(25):
        cliente = random.choice(clientes_objs)
        dias = random.randint(-45, 15)
        vencimento = hoje + timedelta(days=dias)
        valor = round(random.uniform(100.0, 5000.0), 2)
        
        status = "pendente"
        valor_pago = 0.0
        
        # Se data passada, X% chance de pago, X% vencido
        if dias < 0:
            if random.random() > 0.15:
                status = "pago"
                valor_pago = valor
            else:
                status = "vencido"
        
        cr = models.ContaReceber(
            cliente_id=cliente.id,
            descricao=f"Venda {random.randint(1000,9999)}",
            valor=valor,
            valor_pago=valor_pago,
            data_vencimento=vencimento,
            status=status
        )
        db.add(cr)

    # --- Contas a Pagar ---
    #mesmo conceito do a receber
    for _ in range(30):

        forn = random.choice(forn_objs)
        dias = random.randint(-60, 30)
        vencimento = hoje + timedelta(days=dias)
        valor = round(random.uniform(200.0, 8000.0), 2)
        
        status = "pendente"
        valor_pago = 0.0
        
        if dias < 0:
            if random.random() > 0.25:
                status = "pago"
                valor_pago = valor
            else:
                status = "vencido"
        
        cp = models.ContaPagar(
            fornecedor_id=forn.id,
            descricao=f"Compra Insumo {random.randint(100,999)}",
            valor=valor,
            valor_pago=valor_pago,
            data_vencimento=vencimento,
            status=status
        )
        db.add(cp)

    db.commit()