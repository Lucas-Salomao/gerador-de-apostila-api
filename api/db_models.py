"""
Modelos do banco de dados para persistência de apostilas.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class Apostila(Base):
    """
    Modelo para armazenar metadados das apostilas geradas.
    """
    __tablename__ = "apostilas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    theme = Column(Text, nullable=False)
    area_tecnologica = Column(String(255), nullable=False)
    target_audience = Column(String(255), nullable=False)
    num_chapters = Column(Integer, nullable=False)
    gcs_url = Column(String(1000), nullable=False)
    gcs_blob_name = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Converte o modelo para dicionário."""
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "title": self.title,
            "theme": self.theme,
            "area_tecnologica": self.area_tecnologica,
            "target_audience": self.target_audience,
            "num_chapters": self.num_chapters,
            "gcs_url": self.gcs_url,
            "file_size_bytes": self.file_size_bytes,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
