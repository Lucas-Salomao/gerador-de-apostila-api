import sys
import os
import json
import logging
import uuid as uuid_lib
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from api.models import (
    BookRequest, ProgressUpdate, ApostilaResponse, ApostilasListResponse,
    CreateJobRequest, CreateJobResponse, JobStatusResponse
)
from api.database import get_db, init_db
from api.db_models import Apostila, GenerationJob
from api.storage import upload_to_gcs, generate_signed_url
from api.auth_middleware import get_current_user, AuthenticatedUser
from api.worker import start_generation_job

from api.agent import agent_book_generator

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Gerador de Apostila API",
    description="API para geração de apostilas técnicas usando Agentes AI",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Inicializa o banco de dados na inicialização."""
    try:
        init_db()
        logger.info("Banco de dados inicializado com sucesso")
    except Exception as e:
        logger.warning(f"Não foi possível inicializar o banco de dados: {e}")

@app.get("/")
async def root():
    return {"message": "Book Generator API is running. Go to /docs for Swagger UI."}

@app.get("/health")
async def health_check():
    """
    Health check endpoint (público).
    Usado para monitoramento e load balancers.
    """
    return {"status": "healthy", "service": "gerador-de-apostila-api"}

@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    Faz o download do arquivo gerado localmente (fallback).
    """
    # Sanitiza o filename para prevenir Path Traversal
    safe_filename = os.path.basename(filename)
    
    if not safe_filename or safe_filename != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    base_dir = os.getcwd()
    file_path = os.path.join(base_dir, safe_filename)
    
    real_file_path = os.path.realpath(file_path)
    real_base_dir = os.path.realpath(base_dir)
    
    if not real_file_path.startswith(real_base_dir):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if os.path.exists(real_file_path) and os.path.isfile(real_file_path):
        return FileResponse(real_file_path, filename=safe_filename, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    raise HTTPException(status_code=404, detail="File not found")

# ===== NOVOS ENDPOINTS PARA HISTÓRICO DE APOSTILAS =====

@app.get("/apostilas/{user_id}", response_model=ApostilasListResponse)
async def list_apostilas(
    user_id: str, 
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Lista todas as apostilas de um usuário.
    """
    logger.info(f"Listando apostilas do usuário: {user_id}")
    
    apostilas = db.query(Apostila).filter(Apostila.user_id == user_id).order_by(Apostila.created_at.desc()).all()
    
    response_list = []
    for a in apostilas:
        response_list.append(ApostilaResponse(
            id=str(a.id),
            user_id=a.user_id,
            title=a.title,
            theme=a.theme,
            area_tecnologica=a.area_tecnologica,
            target_audience=a.target_audience,
            num_chapters=a.num_chapters,
            gcs_url=a.gcs_url,
            file_size_bytes=a.file_size_bytes,
            created_at=a.created_at.isoformat() + "Z" if a.created_at else ""
        ))
    
    return ApostilasListResponse(apostilas=response_list, total=len(response_list))

@app.get("/apostilas/{user_id}/{apostila_id}/download")
async def download_apostila(
    user_id: str, 
    apostila_id: str, 
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Gera URL assinada para download de uma apostila do GCS.
    """
    logger.info(f"Gerando URL de download para apostila {apostila_id}")
    
    # Validar apostila_id como UUID para prevenir Open Redirect
    try:
        uuid_lib.UUID(apostila_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de apostila inválido")
    
    apostila = db.query(Apostila).filter(
        Apostila.id == apostila_id,
        Apostila.user_id == user_id
    ).first()
    
    if not apostila:
        raise HTTPException(status_code=404, detail="Apostila não encontrada")
    
    try:
        signed_url = generate_signed_url(apostila.gcs_blob_name, expiration_minutes=60)
        return RedirectResponse(url=signed_url)
    except Exception as e:
        logger.error(f"Erro ao gerar URL assinada: {e}")
        raise HTTPException(status_code=500, detail="Erro ao gerar link de download")

@app.get("/apostilas/{user_id}/{apostila_id}/preview")
async def preview_apostila(
    user_id: str, 
    apostila_id: str, 
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Retorna o arquivo DOCX diretamente para preview no navegador.
    Este endpoint baixa do GCS e retorna como StreamingResponse.
    """
    from api.storage import download_from_gcs
    import io
    
    logger.info(f"Gerando preview para apostila {apostila_id}")
    
    # Validar apostila_id como UUID para prevenir Open Redirect
    try:
        uuid_lib.UUID(apostila_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de apostila inválido")
    
    apostila = db.query(Apostila).filter(
        Apostila.id == apostila_id,
        Apostila.user_id == user_id
    ).first()
    
    if not apostila:
        raise HTTPException(status_code=404, detail="Apostila não encontrada")
    
    try:
        # Baixar do GCS
        file_bytes = download_from_gcs(apostila.gcs_blob_name)
        
        # Retornar como StreamingResponse
        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'inline; filename="{apostila.title}.docx"',
                "Access-Control-Allow-Origin": "*"
            }
        )
    except Exception as e:
        logger.error(f"Erro ao fazer preview: {e}")
        raise HTTPException(status_code=500, detail="Erro ao carregar documento")

# ===== ENDPOINT DE GERAÇÃO COM PERSISTÊNCIA =====

@app.post("/generate-book")
async def generate_book(
    request: BookRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Inicia a geração do livro e retorna um stream de eventos (SSE).
    Ao final, faz upload para GCS e salva no banco de dados.
    """
    logger.info(f"Recebida solicitação de geração de livro: {request.theme} (user: {current_user.sub})")
    
    # Variáveis para capturar o resultado final
    final_export_path = None
    final_title = None

    async def event_generator():
        nonlocal final_export_path, final_title
        
        try:
            iterator = agent_book_generator(
                area_tecnologica=request.area_tecnologica,
                custom_audience=request.target_audience,
                custom_theme=request.theme,
                custom_num_chapters=request.num_chapters
            )

            for item in iterator:
                update = None
                
                if isinstance(item, dict):
                    if item.get("type") == "progress":
                        update = ProgressUpdate(
                            type="progress",
                            text=item.get("text"),
                            value=item.get("value")
                        )
                    elif "final_state" in item:
                        final_state = item["final_state"]
                        status = final_state.get("status")
                        
                        if status == "error":
                            update = ProgressUpdate(
                                type="error",
                                text=final_state.get("message", "Erro desconhecido")
                            )
                        else:
                            export_path = final_state.get("export_path", "")
                            filename = os.path.basename(export_path) if export_path else ""
                            final_export_path = export_path
                            final_title = final_state.get("title", filename)
                            
                            # Tentar fazer upload para GCS e salvar no banco
                            download_url = f"/download/{filename}"  # Fallback local
                            apostila_id = None
                            
                            # DEBUG: Log das condições
                            logger.info(f"DEBUG - user_id: '{request.user_id}'")
                            logger.info(f"DEBUG - export_path: '{export_path}'")
                            logger.info(f"DEBUG - file exists: {os.path.exists(export_path) if export_path else False}")
                            
                            if request.user_id and export_path and os.path.exists(export_path):
                                logger.info("DEBUG - Condições atendidas, tentando salvar...")
                                try:
                                    # Upload para GCS
                                    logger.info(f"DEBUG - Fazendo upload para GCS: {filename}")
                                    gcs_url, blob_name, file_size = upload_to_gcs(export_path, filename)
                                    logger.info(f"DEBUG - Upload concluído: {gcs_url}")
                                    
                                    # Salvar no banco de dados
                                    logger.info("DEBUG - Salvando no banco de dados...")
                                    db = next(get_db())
                                    try:
                                        apostila = Apostila(
                                            user_id=request.user_id,
                                            title=final_title,
                                            theme=request.theme,
                                            area_tecnologica=request.area_tecnologica,
                                            target_audience=request.target_audience,
                                            num_chapters=request.num_chapters,
                                            gcs_url=gcs_url,
                                            gcs_blob_name=blob_name,
                                            file_size_bytes=file_size
                                        )
                                        db.add(apostila)
                                        db.commit()
                                        db.refresh(apostila)
                                        apostila_id = str(apostila.id)
                                        
                                        # Gerar URL de download via GCS
                                        download_url = f"/apostilas/{request.user_id}/{apostila_id}/download"
                                        logger.info(f"Apostila salva com sucesso: {apostila_id}")
                                        
                                        # Limpar arquivo temporário após upload
                                        # Validar que o arquivo está no diretório temporário (previne Path Traversal)
                                        import tempfile
                                        temp_dir = tempfile.gettempdir()
                                        real_path = os.path.realpath(export_path)
                                        if real_path.startswith(os.path.realpath(temp_dir)):
                                            try:
                                                os.remove(export_path)
                                                logger.info(f"Arquivo temporário removido: {export_path}")
                                            except Exception as cleanup_err:
                                                logger.warning(f"Não foi possível remover arquivo temporário: {cleanup_err}")
                                        else:
                                            logger.warning(f"Tentativa de remover arquivo fora do diretório temporário: {export_path}")
                                    finally:
                                        db.close()
                                        
                                except Exception as e:
                                    logger.error(f"Erro ao salvar apostila: {e}")
                                    import traceback
                                    logger.error(traceback.format_exc())
                                    # Continua com download local
                            else:
                                logger.warning(f"DEBUG - Condições NÃO atendidas para salvar. user_id={bool(request.user_id)}, export_path={bool(export_path)}, exists={os.path.exists(export_path) if export_path else False}")
                            
                            final_state["download_url"] = download_url
                            if apostila_id:
                                final_state["apostila_id"] = apostila_id
                            
                            update = ProgressUpdate(
                                type="done",
                                text="Geração concluída!",
                                value=100,
                                payload=final_state
                            )
                elif isinstance(item, str):
                    update = ProgressUpdate(
                        type="content",
                        text=item
                    )
                
                if update:
                    yield f"data: {update.model_dump_json()}\n\n"
                    
        except Exception as e:
            logger.error(f"Erro durante a geração: {e}")
            error_update = ProgressUpdate(type="error", text=str(e))
            yield f"data: {error_update.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Accel-Buffering": "no",  # Desabilita buffering no proxy/reverse proxy
            "Connection": "keep-alive",
        }
    )


# ===== ENDPOINTS DE JOBS (POLLING) =====

@app.post("/jobs/generate", response_model=CreateJobResponse)
async def create_generation_job(
    request: CreateJobRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Cria um novo job de geração de apostila.
    Retorna job_id para polling de status.
    """
    logger.info(f"Criando job de geração: {request.theme} (user: {current_user.sub})")
    
    # Criar job no banco
    job = GenerationJob(
        user_id=current_user.sub,
        theme=request.theme,
        area_tecnologica=request.area_tecnologica,
        target_audience=request.target_audience,
        num_chapters=request.num_chapters,
        status="pending",
        progress=0,
        current_step="Aguardando início..."
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    job_id = str(job.id)
    logger.info(f"Job criado: {job_id}")
    
    # Iniciar worker em background
    start_generation_job(job_id)
    
    return CreateJobResponse(
        job_id=job_id,
        status="pending",
        message="Job de geração criado. Use GET /jobs/{job_id}/status para acompanhar."
    )


@app.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Retorna o status atual de um job de geração.
    Use este endpoint para polling (recomendado: a cada 20 segundos).
    
    Nota: Este endpoint não requer autenticação porque:
    1. O job_id (UUID) é secreto e só conhecido por quem criou
    2. Evita problemas de token expirado durante geração longa (até 60min)
    """
    # Validar job_id como UUID
    try:
        uuid_lib.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de job inválido")
    
    # Buscar job apenas pelo ID (UUID funciona como autenticação)
    job = db.query(GenerationJob).filter(
        GenerationJob.id == job_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    
    return JobStatusResponse(
        id=str(job.id),
        status=job.status,
        progress=job.progress or 0,
        current_step=job.current_step,
        content=job.content,
        apostila_id=str(job.apostila_id) if job.apostila_id else None,
        download_url=job.download_url,
        error_message=job.error_message,
        theme=job.theme,
        area_tecnologica=job.area_tecnologica,
        target_audience=job.target_audience,
        num_chapters=job.num_chapters,
        created_at=job.created_at.isoformat() + "Z" if job.created_at else "",
        updated_at=job.updated_at.isoformat() + "Z" if job.updated_at else ""
    )


@app.get("/jobs/user/active")
async def get_user_active_jobs(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Retorna jobs ativos do usuário (pending ou processing).
    Útil para reconexão após fechar o navegador.
    """
    jobs = db.query(GenerationJob).filter(
        GenerationJob.user_id == current_user.sub,
        GenerationJob.status.in_(["pending", "processing"])
    ).order_by(GenerationJob.created_at.desc()).all()
    
    return {
        "jobs": [job.to_dict() for job in jobs],
        "total": len(jobs)
    }
