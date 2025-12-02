from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class BookRequest(BaseModel):
    theme: str = Field(..., description="O tema principal do livro", example="Inteligência Artificial Generativa")
    area_tecnologica: str = Field(..., description="A área tecnológica do livro", example="DESENVOLVIMENTO DE SISTEMAS")
    target_audience: str = Field(..., description="O público-alvo do livro", example="Estudantes de Tecnologia")
    num_chapters: int = Field(5, description="Número de capítulos desejados", ge=1, le=100, example=5)

class ProgressUpdate(BaseModel):
    type: str = Field(..., description="Tipo de atualização (progress, content, error, done)")
    text: Optional[str] = Field(None, description="Texto descritivo do progresso ou conteúdo")
    value: Optional[int] = Field(None, description="Valor percentual do progresso (0-100)")
    payload: Optional[Dict[str, Any]] = Field(None, description="Dados adicionais (ex: estado final)")
