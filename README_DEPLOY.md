# Deploy no Google Cloud Run

Este guia explica como implantar a API "Gerador de Apostila" no Google Cloud Run.

## Pré-requisitos

1.  **Google Cloud SDK**: Instale o [Google Cloud CLI](https://cloud.google.com/sdk/docs/install).
2.  **Conta Google Cloud**: Tenha uma conta ativa e um projeto criado.
3.  **Faturamento Ativo**: O projeto precisa ter uma conta de faturamento vinculada (Cloud Run tem um nível gratuito generoso, mas exige faturamento ativado).

## Passo a Passo

1.  **Login no Google Cloud**:
    Abra o terminal e execute:
    ```powershell
    gcloud auth login
    ```

2.  **Configurar o Projeto**:
    Defina o projeto que você criou como padrão:
    ```powershell
    gcloud config set project ID_DO_SEU_PROJETO
    ```

3.  **Executar o Script de Deploy**:
    Execute o script `deploy.ps1` que automatiza o processo de build e deploy.
    ```powershell
    .\deploy.ps1
    ```
    
    *Nota: Se for a primeira vez, o script irá habilitar as APIs necessárias (Cloud Build e Cloud Run), o que pode levar alguns minutos.*

4.  **Acessar a API**:
    Ao final do deploy, o script exibirá a URL do serviço (Service URL). Você pode acessar essa URL no navegador para ver a mensagem de boas-vindas ou adicionar `/docs` para ver a documentação Swagger.

## Gerenciando Variáveis de Ambiente

Você pode adicionar variáveis de ambiente (como `GOOGLE_API_KEY`) de duas formas:

### Opção 1: Via Google Cloud Console (Interface Web)
1.  Acesse o [Google Cloud Console](https://console.cloud.google.com/run).
2.  Clique no serviço **gerador-de-apostila-api**.
3.  Clique em **EDITAR E IMPLEMENTAR NOVA REVISÃO** (Edit & Deploy New Revision) no topo.
4.  Vá na aba **Contêiner** (Container).
5.  Role até a seção **Variáveis de ambiente** (Environment variables).
6.  Clique em **ADICIONAR VARIÁVEL** (Add Variable).
    *   **Nome**: `GOOGLE_API_KEY`
    *   **Valor**: Sua chave da API.
7.  Clique em **IMPLANTAR** (Deploy) no final da página.

### Opção 2: Via Linha de Comando (gcloud)
Você pode atualizar as variáveis de um serviço já implantado com o comando:

```powershell
gcloud run services update gerador-de-apostila-api `
    --update-env-vars "GOOGLE_API_KEY=sua_chave_aqui" `
    --region us-east1
```

Para adicionar múltiplas variáveis, separe por vírgula:
`--update-env-vars "VAR1=valor1,VAR2=valor2"`
