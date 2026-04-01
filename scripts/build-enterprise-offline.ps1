param(
  [string]$Version = "enterprise-local",
  [string]$OutputDir = "dist/offline"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$dockerDir = Join-Path $repoRoot "docker"
$envFile = Join-Path $dockerDir ".env"
$composeFiles = @(
  "-f", (Join-Path $dockerDir "docker-compose.yaml"),
  "-f", (Join-Path $dockerDir "docker-compose.enterprise.yaml")
)

if (-not (Test-Path $envFile)) {
  throw "Missing docker\.env. Copy docker\.env.example to docker\.env and fill in your deployment settings first."
}

$apiImage = "dify-api-enterprise:$Version"
$webImage = "dify-web-enterprise:$Version"
$outputPath = Join-Path $repoRoot $OutputDir
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null

Write-Host "Building enterprise API image: $apiImage"
docker build --build-arg COMMIT_SHA=$Version -f (Join-Path $repoRoot "api/Dockerfile") -t $apiImage (Join-Path $repoRoot "api")

Write-Host "Building enterprise Web image: $webImage"
docker build --build-arg COMMIT_SHA=$Version -f (Join-Path $repoRoot "web/Dockerfile") -t $webImage $repoRoot

Write-Host "Resolving compose image list"
$images = docker compose --env-file $envFile @composeFiles config --images `
  | Where-Object { $_ -and $_.Trim() } `
  | Sort-Object -Unique

if (-not $images) {
  throw "Unable to resolve images from docker compose configuration."
}

$remoteImages = $images | Where-Object { $_ -notin @($apiImage, $webImage) }
foreach ($image in $remoteImages) {
  Write-Host "Pulling dependency image: $image"
  docker pull $image
}

$manifestPath = Join-Path $outputPath "manifest-$Version.json"
$imagesPath = Join-Path $outputPath "images-$Version.txt"
$archivePath = Join-Path $outputPath "dify-enterprise-offline-$Version.tar"

$manifest = [ordered]@{
  version = $Version
  generated_at = [DateTime]::UtcNow.ToString("o")
  images = $images
}

$manifest | ConvertTo-Json -Depth 4 | Set-Content -Path $manifestPath -Encoding UTF8
$images | Set-Content -Path $imagesPath -Encoding UTF8

Write-Host "Saving offline image bundle to $archivePath"
docker save -o $archivePath $images

Write-Host "Offline bundle ready."
Write-Host "Manifest: $manifestPath"
Write-Host "Images : $imagesPath"
Write-Host "Archive: $archivePath"
