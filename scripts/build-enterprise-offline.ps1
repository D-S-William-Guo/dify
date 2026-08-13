param(
  [string]$Version = "1.16.0-enterprise",
  [string]$OutputDir = "dist/offline",
  [switch]$CheckOnly,
  [ValidateSet("smart", "rebuild", "reuse")]
  [string]$Mode = "reuse"
)

$ErrorActionPreference = "Stop"

$baselineTag = "1.16.0"
$baselineCommit = "5c6372d2f76d240265b92fd27c16bc772ffcb107"

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

$previousEnterpriseVersion = $env:DIFY_ENTERPRISE_VERSION
$previousDebug = $env:DEBUG
$previousEnterpriseEnabled = $env:ENTERPRISE_ENABLED
$previousComposeProfiles = $env:COMPOSE_PROFILES
$env:DIFY_ENTERPRISE_VERSION = $Version
if (-not $env:DEBUG) {
  $env:DEBUG = "false"
}
if (-not $env:ENTERPRISE_ENABLED) {
  $env:ENTERPRISE_ENABLED = "false"
}
if (-not $env:COMPOSE_PROFILES) {
  $envValues = @{}
  foreach ($line in Get-Content $envFile) {
    if ($line -match '^\s*#' -or $line -notmatch '=') {
      continue
    }
    $key, $value = $line -split '=', 2
    $envValues[$key.Trim()] = $value.Trim()
  }
  $vectorStore = if ($envValues.ContainsKey("VECTOR_STORE") -and $envValues["VECTOR_STORE"]) { $envValues["VECTOR_STORE"] } else { "weaviate" }
  $dbType = if ($envValues.ContainsKey("DB_TYPE") -and $envValues["DB_TYPE"]) { $envValues["DB_TYPE"] } else { "postgresql" }
  $env:COMPOSE_PROFILES = "$vectorStore,$dbType,collaboration"
}

function Get-ImageCommitSha {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Image
  )

  try {
    $envLines = docker image inspect $Image --format '{{range .Config.Env}}{{println .}}{{end}}' 2>$null
    if ($LASTEXITCODE -ne 0) {
      return $null
    }
  }
  catch {
    return $null
  }

  foreach ($line in $envLines) {
    if ($line -like 'COMMIT_SHA=*') {
      return $line.Substring('COMMIT_SHA='.Length)
    }
  }

  return $null
}

function Test-ReusableImage {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Image,
    [Parameter(Mandatory = $true)]
    [string]$ExpectedCommitSha
  )

  $commitSha = Get-ImageCommitSha -Image $Image
  return -not [string]::IsNullOrEmpty($commitSha) -and $commitSha -eq $ExpectedCommitSha
}

# Read-only content gate mirror of verify_enterprise_image_content in the .sh
# script: a same-tag enterprise API image is only reusable when its
# /app/api/migrations/versions file set matches the repo at current HEAD and its
# request_builder.py contains _align_snapshot_to_composition. docker run never
# modifies the image.
function Test-EnterpriseImageContent {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Image
  )

  $repoMigrations = @(Get-ChildItem (Join-Path $repoRoot "api/migrations/versions") -Filter "*.py" |
    ForEach-Object { $_.Name } | Sort-Object)
  $imageMigrations = @(docker run --rm --entrypoint sh $Image -c 'ls -1 /app/api/migrations/versions/*.py 2>/dev/null | sed "s#.*/##"' 2>$null |
    ForEach-Object { $_ } | Sort-Object)
  if (($repoMigrations -join "`n") -ne ($imageMigrations -join "`n")) {
    throw "Image $Image is not reusable: image migration file set differs from the repository api/migrations/versions at current HEAD."
  }

  docker run --rm --entrypoint sh $Image -c 'grep -Fq _align_snapshot_to_composition /app/api/clients/agent_backend/request_builder.py' *> $null
  if ($LASTEXITCODE -ne 0) {
    throw "Image $Image is not reusable: /app/api/clients/agent_backend/request_builder.py does not contain _align_snapshot_to_composition."
  }
}

function Ensure-EnterpriseImage {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Image,
    [Parameter(Mandatory = $true)]
    [string]$Dockerfile,
    [Parameter(Mandatory = $true)]
    [string]$ContextPath,
    [Parameter(Mandatory = $true)]
    [string]$ExpectedCommitSha,
    [bool]$VerifyContent = $false
  )

  $reusable = Test-ReusableImage -Image $Image -ExpectedCommitSha $ExpectedCommitSha
  if ($CheckOnly -or $Mode -eq "reuse") {
    if (-not $reusable) {
      throw "Image $Image is not reusable. Expected COMMIT_SHA=$ExpectedCommitSha."
    }
    if ($VerifyContent) {
      Test-EnterpriseImageContent -Image $Image
    }
    Write-Host "Reusing enterprise image: $Image"
    return
  }
  if ($Mode -eq "smart" -and $reusable) {
    if ($VerifyContent) {
      Test-EnterpriseImageContent -Image $Image
    }
    Write-Host "Reusing enterprise image: $Image"
    return
  }

  Write-Host "Building enterprise image: $Image"
  docker build --build-arg COMMIT_SHA=$ExpectedCommitSha -f $Dockerfile -t $Image $ContextPath
}

Ensure-EnterpriseImage `
  -Image $apiImage `
  -Dockerfile (Join-Path $repoRoot "api/Dockerfile") `
  -ContextPath (Join-Path $repoRoot "api") `
  -ExpectedCommitSha $Version `
  -VerifyContent $true

Ensure-EnterpriseImage `
  -Image $webImage `
  -Dockerfile (Join-Path $repoRoot "web/Dockerfile") `
  -ContextPath $repoRoot `
  -ExpectedCommitSha $Version

try {
  Write-Host "Using DIFY_ENTERPRISE_VERSION=$Version"

  Write-Host "Resolving compose image list"
  $rawImages = @(docker compose --env-file $envFile @composeFiles config --images |
    Where-Object { $_ -and $_.Trim() })
  $images = @($rawImages | Sort-Object -Unique)

  if (-not $images) {
    throw "Unable to resolve images from docker compose configuration."
  }

  $apiCount = @($rawImages | Where-Object { $_ -eq $apiImage }).Count
  $webCount = @($rawImages | Where-Object { $_ -eq $webImage }).Count
  $apiTagEntries = @($images | Where-Object { $_ -like 'dify-api-enterprise:*' }).Count
  $webTagEntries = @($images | Where-Object { $_ -like 'dify-web-enterprise:*' }).Count

  if ($apiCount -ne 4) {
    throw "Required-image assertion failed: enterprise API image $apiImage must resolve for api, worker, worker_beat and api_websocket (found $apiCount)."
  }
  if ($webCount -ne 1) {
    throw "Required-image assertion failed: enterprise Web image $webImage must resolve exactly once (found $webCount)."
  }
  if ($apiTagEntries -ne 1) {
    throw "Required-image assertion failed: exactly one enterprise API tag expected (found $apiTagEntries)."
  }
  if ($webTagEntries -ne 1) {
    throw "Required-image assertion failed: exactly one enterprise Web tag expected (found $webTagEntries)."
  }
  foreach ($required in @(
    "langgenius/dify-agent-backend:1.16.0",
    "langgenius/dify-agent-local-sandbox:1.16.0"
  )) {
    if ($images -notcontains $required) {
      throw "Required-image assertion failed: missing required image $required."
    }
  }

  foreach ($image in $images) {
    if ($image -eq $apiImage -or $image -eq $webImage) {
      continue
    }
    docker image inspect $image *> $null
    if ($LASTEXITCODE -eq 0) {
      Write-Host "Reusing local dependency image: $image"
    }
    elseif ($CheckOnly) {
      Write-Host "Dry-run: dependency image $image is not local; pull would run on the build machine."
    }
    else {
      Write-Host "Pulling dependency image: $image"
      docker pull $image
    }
  }

  $manifestPath = Join-Path $outputPath "manifest-$Version.json"
  $imagesPath = Join-Path $outputPath "images-$Version.txt"
  $archivePath = Join-Path $outputPath "dify-enterprise-offline-$Version.tar"

  $images | Set-Content -Path $imagesPath -Encoding UTF8

  $enterpriseCommit = (git rev-parse HEAD).Trim()

  function Get-DockerImageField {
    param(
      [Parameter(Mandatory = $true)]
      [string]$Image,
      [Parameter(Mandatory = $true)]
      [string]$Template
    )

    try {
      $output = docker image inspect $Image --format $Template 2>$null
      if ($LASTEXITCODE -ne 0) {
        return ""
      }
    }
    catch {
      return ""
    }
    $value = ($output -join "`n").Trim()
    if ($value -eq "<no value>") {
      return ""
    }
    return $value
  }

  $manifestImages = foreach ($name in $images) {
    @{
      name = $name
      id = Get-DockerImageField -Image $name -Template '{{.Id}}'
      digest = Get-DockerImageField -Image $name -Template '{{index .RepoDigests 0}}'
    }
  }

  $manifest = [ordered]@{
    version = $Version
    baseline = [ordered]@{
      tag = $baselineTag
      commit = $baselineCommit
    }
    enterprise_commit = $enterpriseCommit
    image_tag = $Version
    generated_at = [DateTime]::UtcNow.ToString("o")
    images = $manifestImages
  }

  $manifest | ConvertTo-Json -Depth 5 | Set-Content -Path $manifestPath -Encoding UTF8

  Write-Host "Manifest written: $manifestPath"
  Write-Host "Images written  : $imagesPath"

  if ($CheckOnly) {
    Write-Host "Dry-run complete (no docker build/pull/save executed)."
    Write-Host "Manifest: $manifestPath"
    Write-Host "Images : $imagesPath"
    return
  }

  Write-Host "Saving offline image bundle to $archivePath"
  docker save -o $archivePath $images

  Write-Host "Offline bundle ready."
  Write-Host "Manifest: $manifestPath"
  Write-Host "Images : $imagesPath"
  Write-Host "Archive: $archivePath"
}
finally {
  if ($null -eq $previousEnterpriseVersion) {
    Remove-Item Env:DIFY_ENTERPRISE_VERSION -ErrorAction SilentlyContinue
  }
  else {
    $env:DIFY_ENTERPRISE_VERSION = $previousEnterpriseVersion
  }
  if ($null -eq $previousDebug) {
    Remove-Item Env:DEBUG -ErrorAction SilentlyContinue
  }
  else {
    $env:DEBUG = $previousDebug
  }
  if ($null -eq $previousEnterpriseEnabled) {
    Remove-Item Env:ENTERPRISE_ENABLED -ErrorAction SilentlyContinue
  }
  else {
    $env:ENTERPRISE_ENABLED = $previousEnterpriseEnabled
  }
  if ($null -eq $previousComposeProfiles) {
    Remove-Item Env:COMPOSE_PROFILES -ErrorAction SilentlyContinue
  }
  else {
    $env:COMPOSE_PROFILES = $previousComposeProfiles
  }
}
