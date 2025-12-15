"""
Middleware de autenticação JWT para validação de tokens do WSO2.

Nota: Migrado de python-jose para pyjwt para corrigir vulnerabilidades
de segurança no pacote ecdsa (SNYK-PYTHON-ECDSA-6184115, SNYK-PYTHON-ECDSA-6219992).
"""
import os
import logging
from typing import Optional
from functools import lru_cache
import httpx
import jwt
from jwt import PyJWKClient, PyJWKClientError
from jwt.exceptions import InvalidTokenError, DecodeError
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Configurações do WSO2
WSO2_JWKS_URL = os.getenv("WSO2_JWKS_URL", "https://identidade.senai.br/oauth2/jwks")
WSO2_ISSUER = os.getenv("WSO2_ISSUER", "https://identidade.senai.br/oauth2/token")
WSO2_AUDIENCE = os.getenv("WSO2_AUDIENCE")  # Client ID do WSO2

# Esquema de segurança HTTP Bearer
security = HTTPBearer(auto_error=False)

# Cliente JWKS com cache automático
_jwk_client: Optional[PyJWKClient] = None


def get_jwk_client() -> PyJWKClient:
    """
    Retorna o cliente JWKS com cache automático.
    O PyJWKClient gerencia o cache de chaves internamente.
    """
    global _jwk_client
    
    if _jwk_client is None:
        logger.info(f"Inicializando cliente JWKS para {WSO2_JWKS_URL}")
        _jwk_client = PyJWKClient(WSO2_JWKS_URL, cache_keys=True, lifespan=3600)
    
    return _jwk_client


def get_signing_key(token: str) -> jwt.PyJWK:
    """
    Encontra a chave correta no JWKS baseado no 'kid' do token.
    """
    try:
        jwk_client = get_jwk_client()
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        return signing_key
    except PyJWKClientError as e:
        logger.error(f"Erro ao obter chave de assinatura: {e}")
        raise HTTPException(status_code=401, detail="Token inválido: chave não encontrada")
    except DecodeError as e:
        logger.error(f"Erro ao decodificar header do token: {e}")
        raise HTTPException(status_code=401, detail="Token inválido")


def clear_jwks_cache():
    """Limpa o cache de JWKS (útil para forçar refresh)."""
    global _jwks_cache
    _jwks_cache = None
    logger.info("Cache de JWKS limpo")


class AuthenticatedUser:
    """Representa um usuário autenticado extraído do JWT."""
    
    def __init__(self, sub: str, email: Optional[str] = None, name: Optional[str] = None, raw_claims: dict = None):
        self.sub = sub
        self.email = email
        self.name = name
        self.raw_claims = raw_claims or {}
    
    @property
    def user_id(self) -> str:
        """Retorna o identificador do usuário (sub)."""
        return self.sub


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> AuthenticatedUser:
    """
    Dependency do FastAPI que valida o token JWT e retorna o usuário autenticado.
    
    Uso:
        @app.get("/protected")
        async def protected_route(user: AuthenticatedUser = Depends(get_current_user)):
            return {"user_id": user.sub}
    """
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Token de autenticação não fornecido",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    
    try:
        # Encontrar a chave de assinatura usando PyJWKClient
        signing_key = get_signing_key(token)
        
        # Decodificar e validar o token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=WSO2_ISSUER,
            options={
                "verify_signature": True,
                "verify_aud": False,  # Desabilitado por enquanto
                "verify_iss": True,
                "verify_exp": True,
                "verify_iat": True,
                "require": ["exp", "iat", "sub"],
            }
        )
        
        # Extrair claims
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Token inválido: sub não encontrado")
        
        user = AuthenticatedUser(
            sub=sub,
            email=payload.get("email"),
            name=f"{payload.get('given_name', '')} {payload.get('family_name', '')}".strip(),
            raw_claims=payload
        )
        
        logger.debug(f"Usuário autenticado: {user.sub}")
        return user
        
    except InvalidTokenError as e:
        logger.warning(f"Erro de validação JWT: {e}")
        raise HTTPException(
            status_code=401,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except PyJWKClientError as e:
        logger.error(f"Erro ao processar chave JWK: {e}")
        raise HTTPException(status_code=401, detail="Erro ao validar token")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro inesperado na autenticação: {e}")
        raise HTTPException(status_code=500, detail="Erro interno de autenticação")


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Optional[AuthenticatedUser]:
    """
    Versão opcional do get_current_user.
    Retorna None se não houver token, ao invés de lançar exceção.
    Útil para rotas que funcionam para usuários autenticados e anônimos.
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
