#-- Arquivo de Autentificação utilizando Hash's com passlib --#

from passlib.context import CryptContext

contexto = CryptContext(schemes=["bcrypt"], deprecated="auto")

def gerar_hash(senha: str) -> str:
    return contexto.hash(senha)

def verificar_hash(senha: str, senha_hash: str) -> bool:
    return contexto.verify(senha, senha_hash)