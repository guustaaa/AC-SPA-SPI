# Arquivo Docker (Configuração do Ambiente)

# Utiliza imagem base de versão estável do python
FROM python:3.10

# varivel para debian aceitar mariadb
ENV DEBIAN_FRONTEND=noninteractive

# Instala MariaDB para genrenciar bancos
RUN apt-get update && apt-get install -y --no-install-recommends \
    mariadb-server \
    && rm -rf /var/lib/apt/lists/*

# Cria diretorio padrão da aplicação e copia arquivos
WORKDIR /app
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY requirements.txt .
RUN pip install -r requirements.txt

# Inicia MariaDB pulando verificação de tabelas e seta senha do root, por ultimo da o shutdown 
RUN mariadbd-safe --skip-networking & \
    sleep 5 && \
    mysqladmin -u root password 'password' || true && \
    mysql -uroot -ppassword -e "CREATE DATABASE IF NOT EXISTS cliente_main;" && \
    mysqladmin -uroot -ppassword shutdown

# Expõe a porta 8000 para o host (Aqui encaixaria um proxy lindo para redirecionar do dns porém sem necessidade para projeto de faculdade)
EXPOSE 8000

# Inicia MariaDB esperando 10 segundos para inicialização limpa, e inicia o Uvicorn gerenciando as Threads do FASTAPI e conectando backend com porta exposta
CMD ["sh", "-c", "mariadbd-safe & sleep 10 && exec uvicorn backend.main:app --host 0.0.0.0 --port 8000"]