from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.database import Usuario

pwd_context = PasswordHash([Argon2Hasher()])


def hash_senha(senha: str) -> str:
    """Gera o hash Argon2 da senha."""
    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    """Compara a senha em texto-plano com o hash armazenado."""
    return pwd_context.verify(senha, hash_armazenado)


def buscar_usuario_por_email(email: str) -> Usuario | None:
    """Retorna o usuário pelo e-mail normalizado, ou None se não encontrado."""
    return Usuario.get_or_none(Usuario.email == email)


def criar_usuario(nome: str, email: str, senha: str) -> Usuario:
    """
    Normaliza o e-mail, valida unicidade e persiste o novo usuário.
    Levanta ValueError se o e-mail já estiver cadastrado.
    """
    email = email.strip().lower()

    if buscar_usuario_por_email(email):
        raise ValueError('E-mail já cadastrado.')

    return Usuario.create(
        nome=nome.strip(),
        email=email,
        senha_hash=hash_senha(senha),
    )


def autenticar(email: str, senha: str) -> Usuario | None:
    """
    Retorna o usuário se as credenciais forem válidas, ou None caso contrário.
    A normalização do e-mail é feita aqui também, para consistência.
    """
    email = email.strip().lower()
    usuario = buscar_usuario_por_email(email)

    if usuario is None:
        return None

    if not verificar_senha(senha, usuario.senha_hash):
        return None

    return usuario
