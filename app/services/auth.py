# pyrefly: ignore [missing-import]
from pwdlib import PasswordHash
import re
# pyrefly: ignore [missing-import]
from pwdlib.hashers.argon2 import Argon2Hasher
from peewee import IntegrityError

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


def criar_usuario(nome: str, email: str, senha: str, confirmar_senha: str) -> Usuario:
    """
    Normaliza e valida nome, e-mail, unicidade, senha e persiste o novo usuário.
    Levanta ValueError se houver problema nos dados.
    """
    nome = nome.strip()
    if not nome:
        raise ValueError('Nome não pode estar vazio.')

    email = email.strip().lower()
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise ValueError('E-mail inválido.')

    if len(senha) < 8:
        raise ValueError('A senha deve ter no mínimo 8 caracteres.')

    if senha != confirmar_senha:
        raise ValueError('As senhas não coincidem.')

    try:
        return Usuario.create(
            nome=nome,
            email=email,
            senha_hash=hash_senha(senha),
        )
    except IntegrityError:
        raise ValueError('E-mail já cadastrado.')


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
