$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env. Please fill OPENAI_API_KEY before using LLM routing."
}

docker compose up -d mysql
python -m ProcureFlow.run_all

