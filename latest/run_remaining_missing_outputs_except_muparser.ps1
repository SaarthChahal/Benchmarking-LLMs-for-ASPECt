param(
  [string]$BatchRoot = "C:\Users\chaha\OneDrive\Desktop\4-2\LLM\Semester Project\Latest\runs\aspect_comparison_selected\20260423_112326",
  [string]$DockerImage = "geodynamics/aspect:latest",
  [string]$DockerCommand = "docker"
)

$ErrorActionPreference = "Stop"

function ConvertTo-WslPath {
  param([string]$Path)

  $fullPath = [System.IO.Path]::GetFullPath($Path)
  if ($fullPath -match "^([A-Za-z]):\\(.*)$") {
    $drive = $matches[1].ToLowerInvariant()
    $rest = $matches[2] -replace "\\", "/"
    return "/mnt/$drive/$rest"
  }

  return $fullPath -replace "\\", "/"
}

function Invoke-DockerAspect {
  param(
    [string]$RunRootForDocker,
    [string]$CaseRelativePath
  )

  $casePathForDocker = $CaseRelativePath -replace "\\", "/"
  $bashScript = "cd /workspace/$casePathForDocker && aspect input.prm > aspect.log 2>&1"
  $dockerArgs = @(
    "run",
    "--rm",
    "-v",
    "${RunRootForDocker}:/workspace",
    $DockerImage,
    "bash",
    "-lc",
    $bashScript
  )

  if ($DockerCommand -eq "wsl docker") {
    & wsl docker @dockerArgs
  }
  elseif ($DockerCommand -eq "docker") {
    & docker @dockerArgs
  }
  else {
    $parts = $DockerCommand -split "\s+"
    & $parts[0] @($parts[1..($parts.Count - 1)] + $dockerArgs)
  }

  return $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $BatchRoot)) {
  throw "Batch root not found: $BatchRoot"
}

$runRootForDocker = if ($DockerCommand -eq "wsl docker") {
  ConvertTo-WslPath $BatchRoot
}
else {
  [System.IO.Path]::GetFullPath($BatchRoot)
}

$cases = @(
  "regenerated\sinker-with-averaging__sinker-with-averaging\anthropic__claude-3-haiku",
  "regenerated\sinker-with-averaging__sinker-with-averaging\meta-llama__llama-3.1-8b-instruct"
)

Write-Host "Will run these cases:"
$cases | ForEach-Object { Write-Host "  $_" }
Write-Host ""

foreach ($rel in $cases) {
  $caseDir = Join-Path $BatchRoot $rel
  $inputPrm = Join-Path $caseDir "input.prm"
  $outputDir = Join-Path $caseDir "output"
  $logPath = Join-Path $caseDir "aspect.log"

  if (-not (Test-Path -LiteralPath $inputPrm)) {
    Write-Host "Skipping missing input: $rel"
    continue
  }

  if (Test-Path -LiteralPath $outputDir) {
    Write-Host "Skipping already-complete case: $rel"
    continue
  }

  if (Test-Path -LiteralPath $logPath) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Move-Item -LiteralPath $logPath -Destination (Join-Path $caseDir ("aspect.log.before-rerun." + $stamp)) -Force
  }

  Write-Host "=== Running $rel ==="
  $exitCode = Invoke-DockerAspect -RunRootForDocker $runRootForDocker -CaseRelativePath $rel
  Write-Host ("    -> exit_code={0}" -f $exitCode)
}

Write-Host ""
Write-Host "Done."
