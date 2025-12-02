# Gerador de Livros com IA - API Backend

Este projeto implementa uma API RESTful para geração de livros técnicos utilizando o modelo Gemini do Google (via Vertex AI) e a biblioteca LangGraph. A aplicação foi desenhada para ser consumida por qualquer frontend, oferecendo endpoints para iniciar a geração, acompanhar o progresso via streaming (SSE) e baixar o resultado final em DOCX.

## Visão Geral

A API permite:

1.  **Gerar Livros Técnicos:** Recebe tema, área tecnológica, público-alvo e número de capítulos.
2.  **Streaming de Progresso:** Utiliza Server-Sent Events (SSE) para enviar atualizações em tempo real sobre cada etapa da geração (título, sumário, escrita de capítulos, revisão).
3.  **Exportação:** Disponibiliza o livro final formatado em DOCX para download.

## Tecnologias Utilizadas

*   **Python 3.13**
*   **FastAPI:** Framework web moderno e de alta performance.
*   **LangGraph:** Orquestração do fluxo de trabalho do agente.
*   **Google Vertex AI (Gemini):** Geração de conteúdo.
*   **python-docx:** Manipulação de arquivos Word.
*   **Docker:** Containerização da aplicação.

## Estrutura do Projeto

*   **`api/app.py`:** Ponto de entrada da aplicação FastAPI. Define as rotas e a configuração do servidor.
*   **`api/agent.py`:** Lógica do agente de IA (LangGraph), responsável por gerar o conteúdo.
*   **`api/models.py`:** Modelos de dados Pydantic para validação de requisições e respostas.
*   **`Dockerfile`:** Configuração para build da imagem Docker.

## Como Executar

### Pré-requisitos

*   Conta no Google Cloud com Vertex AI habilitado.
*   Variável de ambiente `GEMINI_API_KEY` ou credenciais do Google Cloud configuradas.

### Rodando Localmente

1.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```

2.  Inicie o servidor:
    ```bash
    uvicorn api.app:app --reload
    ```

3.  Acesse a documentação interativa (Swagger UI) em: `http://localhost:8000/docs`

### Rodando com Docker

1.  Construa a imagem:
    ```bash
    docker build -t gerador-apostila-api .
    ```

2.  Execute o container:
    ```bash
    docker run -p 8000:8000 --env-file .env gerador-apostila-api
    ```

## Endpoints Principais

### `POST /generate-book`

Inicia o processo de geração.

**Corpo da Requisição:**
```json
{
  "theme": "Introdução à IA",
  "area_tecnologica": "DESENVOLVIMENTO DE SISTEMAS",
  "target_audience": "Estudantes",
  "num_chapters": 5
}
```

**Resposta:** Stream de eventos (SSE) com atualizações de progresso e conteúdo.

### `GET /download/{filename}`

Baixa o arquivo DOCX gerado. O nome do arquivo é retornado no evento final do stream de geração.

## Licença

MIT