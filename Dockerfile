FROM python:3.13-slim-trixie

WORKDIR /app

# Install system dependencies if needed (e.g. for curl healthcheck)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK CMD curl --fail http://localhost:8000/ || exit 1

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]