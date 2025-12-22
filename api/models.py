from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class BookRequest(BaseModel):
    theme: str = Field(..., description="O tema principal do livro", example="Inteligência Artificial Generativa")
    area_tecnologica: str = Field(..., description="A área tecnológica do livro", example="DESENVOLVIMENTO DE SISTEMAS")
    target_audience: str = Field(..., description="O público-alvo do livro", example="Estudantes de Tecnologia")
    num_chapters: int = Field(5, description="Número de capítulos desejados", ge=1, le=100, example=5)
    user_id: Optional[str] = Field(None, description="ID do usuário que está gerando a apostila")

class ProgressUpdate(BaseModel):
    type: str = Field(..., description="Tipo de atualização (progress, content, error, done)")
    text: Optional[str] = Field(None, description="Texto descritivo do progresso ou conteúdo")
    value: Optional[int] = Field(None, description="Valor percentual do progresso (0-100)")
    payload: Optional[Dict[str, Any]] = Field(None, description="Dados adicionais (ex: estado final)")

class ApostilaResponse(BaseModel):
    """Modelo de resposta para uma apostila."""
    id: str
    user_id: str
    title: str
    theme: str
    area_tecnologica: str
    target_audience: str
    num_chapters: int
    gcs_url: str
    file_size_bytes: Optional[int] = None
    created_at: str
    download_url: Optional[str] = None

class ApostilasListResponse(BaseModel):
    """Modelo de resposta para lista de apostilas."""
    apostilas: List[ApostilaResponse]
    total: int


# === Modelos para Jobs de Geração (Polling) ===

class CreateJobRequest(BaseModel):
    """Request para criar um novo job de geração."""
    theme: str = Field(..., description="O tema principal do livro")
    area_tecnologica: str = Field(..., description="A área tecnológica do livro")
    target_audience: str = Field(..., description="O público-alvo do livro")
    num_chapters: int = Field(5, description="Número de capítulos desejados", ge=1, le=100)
    author_name: Optional[str] = Field("SENAI", description="Nome do autor/docente")

class CreateJobResponse(BaseModel):
    """Response ao criar um job de geração."""
    job_id: str
    status: str
    message: str

class JobStatusResponse(BaseModel):
    """Response com status completo de um job."""
    id: str
    status: str  # pending, processing, completed, failed, timeout
    progress: int
    current_step: Optional[str] = None
    content: Optional[str] = None
    apostila_id: Optional[str] = None
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    theme: str
    area_tecnologica: str
    target_audience: str
    num_chapters: int
    created_at: str
    updated_at: str


# === Modelos para Refinamento de Tema ===

class RefineThemeRequest(BaseModel):
    """Request para refinar/melhorar o tema da apostila."""
    theme: str = Field(..., description="O tema a ser refinado/melhorado", min_length=1)

class RefineThemeResponse(BaseModel):
    """Response com o tema refinado."""
    refined_theme: str = Field(..., description="O tema refinado e melhorado")

