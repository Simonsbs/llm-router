# start-llm-router.ps1
param(
    [string]$ImageName     = "simongpt-llm-router",
    [string]$ContainerName = "llm-router",
    [string]$ApiKey,
    [string]$JwtSecret,
    [string]$OllamaUrl     = "http://host.docker.internal:11434",
    [int]   $Port          = 8080
)

# Load .env values
$envVars = @{}
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Write-Host "🔍 Reading .env file..."
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^[ \t]*([^#=]+)[ \t]*=[ \t]*(.*)') {
            $key = $matches[1].Trim()
            $val = $matches[2].Trim('"')
            $envVars[$key] = $val

            switch ($key) {
                "LLM_ROUTER_API_KEY" { if (-not $ApiKey)   { $ApiKey   = $val } }
                "JWT_SECRET_KEY"     { if (-not $JwtSecret){ $JwtSecret= $val } }
                "OLLAMA_URL"         { if ($OllamaUrl -eq "http://host.docker.internal:11434") { $OllamaUrl = $val } }
            }
        }
    }
}

# Validate required fields
if (-not $ApiKey) {
    Write-Error "❌ LLM_ROUTER_API_KEY not set. Provide -ApiKey or set it in .env"
    exit 1
}
if (-not $JwtSecret) {
    Write-Error "❌ JWT_SECRET_KEY not set. Provide -JwtSecret or set it in .env"
    exit 1
}

# Always override explicit values
$envVars["LLM_ROUTER_API_KEY"] = $ApiKey
$envVars["JWT_SECRET_KEY"]     = $JwtSecret
$envVars["OLLAMA_URL"]         = $OllamaUrl

Write-Host "⏳ Building Docker image '$ImageName'..."
docker build -t $ImageName .
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Build failed"
    exit 1
}

Write-Host "🛑 Stopping & removing any existing '$ContainerName' container..."
$existing = docker ps -a --filter "name=^$ContainerName$" --format "{{.ID}}"
if ($existing) {
    docker stop $ContainerName | Out-Null
    docker rm   $ContainerName | Out-Null
    Write-Host "➡️ Removed old container"
} else {
    Write-Host "⚠️ No existing container found"
}

Write-Host "🚀 Running new container '$ContainerName'..."
$dockerArgs = @(
    "run", "-d",
    "--name", $ContainerName,
    "-p", "${Port}:${Port}"
)

# Add all env vars as -e key=value
$envVars.GetEnumerator() | ForEach-Object {
    $dockerArgs += "-e"
    $dockerArgs += "$($_.Key)=$($_.Value)"
}

$dockerArgs += $ImageName

# Execute the docker run safely
docker @dockerArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Failed to start container"
    exit 1
}

Write-Host "✅ Container '$ContainerName' is running and listening on port $Port."
