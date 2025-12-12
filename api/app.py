import sys
import os
import json
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from api.models import BookRequest, ProgressUpdate

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

@app.get("/")
async def root():
    return {"message": "Book Generator API is running. Go to /docs for Swagger UI."}

@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    Faz o download do arquivo gerado.
    """
    # Sanitiza o filename para prevenir Path Traversal
    # Remove qualquer componente de caminho (../, /, \, etc.)
    safe_filename = os.path.basename(filename)
    
    # Verifica se o filename é válido após sanitização
    if not safe_filename or safe_filename != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # Define o diretório base permitido para downloads
    base_dir = os.getcwd()
    file_path = os.path.join(base_dir, safe_filename)
    
    # Verifica se o caminho resultante está dentro do diretório permitido
    # Isso previne ataques mesmo que o basename falhe
    real_file_path = os.path.realpath(file_path)
    real_base_dir = os.path.realpath(base_dir)
    
    if not real_file_path.startswith(real_base_dir):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if os.path.exists(real_file_path) and os.path.isfile(real_file_path):
        return FileResponse(real_file_path, filename=safe_filename, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    raise HTTPException(status_code=404, detail="File not found")

@app.post("/generate-book")
async def generate_book(request: BookRequest):
    """
    Inicia a geração do livro e retorna um stream de eventos (SSE).
    """
    logger.info(f"Recebida solicitação de geração de livro: {request.theme}")

    async def event_generator():
        try:
            # Call the synchronous generator from agent.py
            # Since it's a generator, we can iterate over it.
            # Note: If agent_book_generator is blocking, we might need to run it in a threadpool 
            # if we want to handle multiple requests concurrently without blocking the event loop.
            # For now, we'll iterate directly as it seems to be designed for streaming.
            
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
                        # Final state logic
                        final_state = item["final_state"]
                        status = final_state.get("status")
                        if status == "error":
                             update = ProgressUpdate(
                                type="error",
                                text=final_state.get("message", "Erro desconhecido")
                            )
                        else:
                            # Extract filename from export_path
                            export_path = final_state.get("export_path", "")
                            filename = os.path.basename(export_path) if export_path else ""
                            
                            # Update payload with download URL or filename
                            final_state["download_url"] = f"/download/{filename}"
                            
                            update = ProgressUpdate(
                                type="done",
                                text="Geração concluída!",
                                value=100,
                                payload=final_state
                            )
                elif isinstance(item, str):
                    # It's a content chunk (markdown)
                    update = ProgressUpdate(
                        type="content",
                        text=item
                    )
                
                if update:
                    # SSE format: data: <json>\n\n
                    yield f"data: {update.model_dump_json()}\n\n"
                    
        except Exception as e:
            logger.error(f"Erro durante a geração: {e}")
            error_update = ProgressUpdate(type="error", text=str(e))
            yield f"data: {error_update.model_dump_json()}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
