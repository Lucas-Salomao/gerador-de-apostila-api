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

## Variáveis de Ambiente

Se sua aplicação precisar de variáveis de ambiente (como chaves de API), você pode configurá-las durante o deploy ou no console do Cloud Run.

Para configurar via linha de comando durante o deploy, adicione a flag `--set-env-vars` no comando `gcloud run deploy` dentro do arquivo `deploy.ps1`. Exemplo:

```powershell
gcloud run deploy $SERVICE_NAME `
    --source . `
    --region $REGION `
    --allow-unauthenticated `
    --port 8080 `
    --set-env-vars "GOOGLE_API_KEY=sua_chave,OUTRA_VAR=valor"
```

Ou configure pelo Console do Google Cloud após o deploy.
