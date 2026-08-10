param(
  [string]$Version = "1.16.0-enterprise",
  [string]$OutputDir = "dist/offline"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$outputPath = Join-Path $repoRoot $OutputDir
$manifestPath = Join-Path $outputPath "manifest-$Version.json"
$imagesPath = Join-Path $outputPath "images-$Version.txt"
$archivePath = Join-Path $outputPath "dify-enterprise-config-$Version.tar.gz"

if (-not (Test-Path $manifestPath) -or -not (Test-Path $imagesPath)) {
  throw "Missing offline manifest or image list for version $Version. Run build-enterprise-offline with Mode=reuse after image validation first."
}

$requiredFiles = @(
  "docker/docker-compose.yaml",
  "docker/docker-compose.enterprise.yaml",
  "docker/.env.example",
  "$OutputDir/manifest-$Version.json",
  "$OutputDir/images-$Version.txt"
)

$envExampleFiles = Get-ChildItem -Path (Join-Path $repoRoot "docker/envs") -Recurse -File -Filter "*.env.example" |
  ForEach-Object {
    $relativePath = Resolve-Path -Path $_.FullName -Relative -RelativeBasePath $repoRoot
    $relativePath -replace "\\", "/"
  } |
  Sort-Object

if (-not $envExampleFiles -or $envExampleFiles.Count -eq 0) {
  throw "Missing required docker/envs/*.env.example files."
}

$requiredFiles += $envExampleFiles

$requiredDirs = @(
  "docker/nginx",
  "docker/ssrf_proxy"
)

foreach ($path in $requiredFiles) {
  if (-not (Test-Path (Join-Path $repoRoot $path) -PathType Leaf)) {
    throw "Missing required file: $path"
  }
}

foreach ($path in $requiredDirs) {
  if (-not (Test-Path (Join-Path $repoRoot $path) -PathType Container)) {
    throw "Missing required directory: $path"
  }
}

New-Item -ItemType Directory -Force -Path $outputPath | Out-Null

$archiveItems = $requiredFiles + $requiredDirs
$excludes = @(
  "--exclude=*.env",
  "--exclude=*.env.production",
  "--exclude=docker/volumes",
  "--exclude=docker/volumes/*",
  "--exclude=.git",
  "--exclude=.git/*",
  "--exclude=.cache",
  "--exclude=*/.cache/*",
  "--exclude=node_modules",
  "--exclude=*/node_modules/*",
  "--exclude=.venv",
  "--exclude=*/.venv/*",
  "--exclude=.next",
  "--exclude=*/.next/*"
)

tar --create --gzip --file $archivePath --directory $repoRoot @excludes @archiveItems

Write-Host "Enterprise configuration bundle ready."
Write-Host "Archive: $archivePath"
