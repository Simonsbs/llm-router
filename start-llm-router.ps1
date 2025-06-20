param(
    [string]$ImageName     = "simongpt-llm-router",
    [string]$ContainerName = "llm-router",
    [string]$ApiKey,
    [string]$JwtSecret,
    [string]$OllamaUrl     = "http://host.docker.internal:11434",
    [int]   $Port          = 8080,
    [string]$DockerContext = "default",
    [ValidateSet("local", "remote")][string]$Target = "local"
)

# ────── Load .env ──────
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

if (-not $ApiKey)   { Write-Error "LLM_ROUTER_API_KEY not set."; exit 1 }
if (-not $JwtSecret){ Write-Error "JWT_SECRET_KEY not set."; exit 1 }

$envVars["LLM_ROUTER_API_KEY"] = $ApiKey
$envVars["JWT_SECRET_KEY"]     = $JwtSecret
$envVars["OLLAMA_URL"]         = $OllamaUrl

$RegistryHost  = "192.168.1.10:5000"
$RegistryImage = "$RegistryHost/$ImageName"

# ────── Build and push ──────
Write-Host "⏳ Building Docker image '$RegistryImage'..."

if ($DockerContext -ne "default") {
    $builderName = "builder-$DockerContext"
    if (-not (docker buildx ls | Select-String -Pattern $builderName)) {
        Write-Host "🔧 Creating remote buildx builder '$builderName'..."
        docker buildx create --name $builderName --driver docker-container --bootstrap $DockerContext | Out-Null
    }
    docker buildx use $builderName
    docker buildx build --builder $builderName --platform linux/amd64 --tag $RegistryImage --push .
} else {
    docker build -t $RegistryImage .
    docker push $RegistryImage
}

if ($LASTEXITCODE -ne 0) { Write-Error "Build failed"; exit 1 }

# ────── Deploy ──────
if ($Target -eq "local") {
    Write-Host "🛑 Stopping & removing local '$ContainerName'..."
    $existing = docker ps -a --filter "name=^$ContainerName$" --format "{{.ID}}"
    if ($existing) {
        docker stop $ContainerName | Out-Null
        docker rm   $ContainerName | Out-Null
        Write-Host "➡️ Removed old container"
    }

    Write-Host "🚀 Starting new local container '$ContainerName'..."
    $dockerArgs = @(
        "run", "-d",
        "--name", $ContainerName,
        "--restart", "always",
        "-p", "$Port`:$Port"
    ) + ($envVars.GetEnumerator() | ForEach-Object { "-e", "$($_.Key)=$($_.Value)" }) + @($RegistryImage)

    docker @dockerArgs
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to start local container"; exit 1 }

    Write-Host "✅ Local container '$ContainerName' is running on port $Port."

} else {
    Write-Host "🌐 Deploying to remote server (192.168.1.10)..."

    # Compose env vars string for remote shell
    $envStr = ($envVars.GetEnumerator() | ForEach-Object { "-e $($_.Key)=$($_.Value)" }) -join ' '

    # Remove existing container if exists
    Invoke-Expression "ssh simon@192.168.1.10 docker rm -f $ContainerName 2>`$null"

    # Run the container remotely
    $remoteRun = "docker run -d --name $ContainerName --restart always -p ${Port}:${Port} $envStr $RegistryImage"
    Invoke-Expression "ssh simon@192.168.1.10 $remoteRun"

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Remote deployment failed"
        exit 1
    }

    Write-Host "✅ Remote container '$ContainerName' deployed to 192.168.1.10:$Port."
}
