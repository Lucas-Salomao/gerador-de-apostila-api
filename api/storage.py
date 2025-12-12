"""
Módulo para upload e gerenciamento de arquivos no Google Cloud Storage.
"""
import os
import logging
from datetime import timedelta
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Variável de ambiente para o bucket
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")


def get_storage_client():
    """
    Retorna o cliente do Google Cloud Storage.
    Usa Application Default Credentials ou GOOGLE_APPLICATION_CREDENTIALS.
    """
    return storage.Client()


def upload_to_gcs(file_path: str, blob_name: str = None) -> tuple[str, str, int]:
    """
    Faz upload de um arquivo para o Google Cloud Storage.
    
    Args:
        file_path: Caminho local do arquivo
        blob_name: Nome do blob no GCS (opcional, usa o nome do arquivo se não fornecido)
    
    Returns:
        Tuple com (public_url, blob_name, file_size_bytes)
    """
    if not GCS_BUCKET_NAME:
        raise ValueError("GCS_BUCKET_NAME não configurado nas variáveis de ambiente")
    
    if not blob_name:
        blob_name = os.path.basename(file_path)
    
    # Adicionar prefixo de pasta com timestamp para organização
    from datetime import datetime
    date_prefix = datetime.utcnow().strftime("%Y/%m/%d")
    blob_name = f"apostilas/{date_prefix}/{blob_name}"
    
    logger.info(f"Fazendo upload de {file_path} para gs://{GCS_BUCKET_NAME}/{blob_name}")
    
    client = get_storage_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(blob_name)
    
    # Fazer upload
    blob.upload_from_filename(file_path)
    
    # Obter tamanho do arquivo
    file_size = os.path.getsize(file_path)
    
    # Gerar URL pública (ou usar signed URL para acesso controlado)
    public_url = f"gs://{GCS_BUCKET_NAME}/{blob_name}"
    
    logger.info(f"Upload concluído: {public_url} ({file_size} bytes)")
    
    return public_url, blob_name, file_size


def generate_signed_url(blob_name: str, expiration_minutes: int = 60) -> str:
    """
    Gera uma URL assinada para download temporário de um arquivo.
    
    Args:
        blob_name: Nome do blob no GCS
        expiration_minutes: Tempo de expiração da URL em minutos
    
    Returns:
        URL assinada para download
    """
    if not GCS_BUCKET_NAME:
        raise ValueError("GCS_BUCKET_NAME não configurado nas variáveis de ambiente")
    
    logger.info(f"Gerando URL assinada para {blob_name}")
    
    client = get_storage_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(blob_name)
    
    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=expiration_minutes),
        method="GET"
    )
    
    logger.info(f"URL assinada gerada com expiração de {expiration_minutes} minutos")
    
    return url


def delete_from_gcs(blob_name: str) -> bool:
    """
    Deleta um arquivo do Google Cloud Storage.
    
    Args:
        blob_name: Nome do blob no GCS
    
    Returns:
        True se deletado com sucesso, False caso contrário
    """
    if not GCS_BUCKET_NAME:
        raise ValueError("GCS_BUCKET_NAME não configurado nas variáveis de ambiente")
    
    try:
        client = get_storage_client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(blob_name)
        blob.delete()
        logger.info(f"Arquivo {blob_name} deletado com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao deletar {blob_name}: {e}")
        return False
