"""
Worker para executar geração de apostilas em background.
Permite polling em vez de conexões longas (SSE).
"""
import threading
import logging
import os
import tempfile
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.db_models import GenerationJob, Apostila
from api.agent import agent_book_generator
from api.storage import upload_to_gcs

logger = logging.getLogger(__name__)

# Timeout máximo para jobs (60 minutos)
JOB_TIMEOUT_MINUTES = 60


def run_generation_job(job_id: str):
    """
    Executa a geração de apostila em background thread.
    Atualiza o banco de dados com o progresso.
    """
    db: Session = SessionLocal()
    
    try:
        # Buscar o job
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} não encontrado")
            return
        
        # Marcar como processing
        job.status = "processing"
        job.current_step = "Iniciando geração..."
        db.commit()
        
        logger.info(f"Iniciando job {job_id}: {job.theme}")
        
        # Variáveis para acumular conteúdo
        accumulated_content = ""
        final_export_path = None
        final_title = None
        
        # Executar geração
        try:
            iterator = agent_book_generator(
                area_tecnologica=job.area_tecnologica,
                custom_audience=job.target_audience,
                custom_theme=job.theme,
                custom_num_chapters=job.num_chapters,
                author_name=job.author_name or "SENAI"
            )
            
            for item in iterator:
                # Verificar timeout
                elapsed = datetime.utcnow() - job.created_at
                if elapsed > timedelta(minutes=JOB_TIMEOUT_MINUTES):
                    job.status = "timeout"
                    job.error_message = f"Job excedeu o tempo máximo de {JOB_TIMEOUT_MINUTES} minutos"
                    db.commit()
                    logger.warning(f"Job {job_id} timeout")
                    return
                
                if isinstance(item, dict):
                    if item.get("type") == "progress":
                        job.progress = item.get("value", 0)
                        job.current_step = item.get("text", "")
                        db.commit()
                    
                    # Capturar estado final (vem como {"final_state": {...}})
                    if "final_state" in item:
                        final_state = item.get("final_state", {})
                        final_export_path = final_state.get("export_path")
                        final_title = final_state.get("title")
                        logger.info(f"Capturado final_state: export_path={final_export_path}, title={final_title}")
                    
                    # Fallback: capturar diretamente se vier assim
                    elif "export_path" in item:
                        final_export_path = item.get("export_path")
                    if "title" in item and not final_title:
                        final_title = item.get("title")
                
                elif isinstance(item, str):
                    # Acumular conteúdo markdown
                    accumulated_content += item
                    job.content = accumulated_content
                    db.commit()
            
            # Geração concluída - fazer upload para GCS
            if final_export_path and os.path.exists(final_export_path):
                filename = f"{final_title or 'apostila'}.docx".replace(" ", "_")
                
                try:
                    # Upload para GCS
                    gcs_url, blob_name, file_size = upload_to_gcs(final_export_path, filename)
                    
                    # Criar registro de Apostila
                    apostila = Apostila(
                        user_id=job.user_id,
                        title=final_title or job.theme,
                        theme=job.theme,
                        area_tecnologica=job.area_tecnologica,
                        target_audience=job.target_audience,
                        num_chapters=job.num_chapters,
                        gcs_url=gcs_url,
                        gcs_blob_name=blob_name,
                        file_size_bytes=file_size
                    )
                    db.add(apostila)
                    db.commit()
                    db.refresh(apostila)
                    
                    # Atualizar job com resultado
                    job.apostila_id = apostila.id
                    job.download_url = f"/apostilas/{job.user_id}/{apostila.id}/download"
                    job.status = "completed"
                    job.progress = 100
                    job.current_step = "Geração concluída!"
                    db.commit()
                    
                    logger.info(f"Job {job_id} concluído com sucesso. Apostila: {apostila.id}")
                    
                    # Limpar arquivo temporário
                    temp_dir = tempfile.gettempdir()
                    real_path = os.path.realpath(final_export_path)
                    if real_path.startswith(os.path.realpath(temp_dir)):
                        try:
                            os.remove(final_export_path)
                            logger.info(f"Arquivo temporário removido: {final_export_path}")
                        except Exception as cleanup_err:
                            logger.warning(f"Não foi possível remover arquivo temporário: {cleanup_err}")
                    
                except Exception as upload_err:
                    logger.error(f"Erro no upload para GCS: {upload_err}")
                    job.status = "failed"
                    job.error_message = f"Erro no upload: {str(upload_err)}"
                    db.commit()
            else:
                # Sem arquivo de exportação
                job.status = "completed"
                job.progress = 100
                job.current_step = "Geração concluída (sem arquivo)"
                db.commit()
                logger.warning(f"Job {job_id} concluído mas sem arquivo de exportação")
        
        except Exception as gen_err:
            logger.error(f"Erro na geração do job {job_id}: {gen_err}")
            import traceback
            logger.error(traceback.format_exc())
            job.status = "failed"
            job.error_message = str(gen_err)
            db.commit()
    
    except Exception as e:
        logger.error(f"Erro fatal no worker para job {job_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = f"Erro fatal: {str(e)}"
                db.commit()
        except:
            pass
    
    finally:
        db.close()


def start_generation_job(job_id: str):
    """
    Inicia um job de geração em uma thread separada.
    """
    thread = threading.Thread(
        target=run_generation_job,
        args=(job_id,),
        daemon=True,
        name=f"generation-job-{job_id}"
    )
    thread.start()
    logger.info(f"Thread iniciada para job {job_id}")
    return thread
