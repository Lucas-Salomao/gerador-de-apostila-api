"""
Configuração de conexão com o banco de dados PostgreSQL.
Compatível com Supabase (pooler) e AlloyDB.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Variáveis de ambiente para conexão
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_SSLMODE = os.getenv("DB_SSLMODE", "")  # "require" para Supabase, vazio para local

# Construir a URL de conexão
# Formato: postgresql://user:password@host:port/database?sslmode=require
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Adicionar SSL se configurado (necessário para Supabase pooler)
if DB_SSLMODE:
    DATABASE_URL += f"?sslmode={DB_SSLMODE}"

logger.info(f"Conectando ao banco de dados em {DB_HOST}:{DB_PORT}/{DB_NAME}")

# Criar engine com pool de conexões
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    echo=False  # Set to True for SQL debugging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()


def get_db():
    """
    Dependency para obter uma sessão do banco de dados.
    Uso: db = next(get_db()) ou como injeção de dependência do FastAPI.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Inicializa o banco de dados criando todas as tabelas.
    Deve ser chamado na inicialização da aplicação.
    """
    from api.db_models import Apostila  # Import dos modelos
    logger.info("Inicializando banco de dados...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tabelas criadas com sucesso.")
