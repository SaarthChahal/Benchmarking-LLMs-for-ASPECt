param(
  [string]$DockerImage = "geodynamics/aspect:latest",
  [string]$DockerCommand = "wsl docker",
  [switch]$KeepDuplicateRuns
)

$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
$inputDir = Join-Path $workspace "source_prm_dataset\files"
$runRoot = Join-Path $workspace "runs\aspect_selected"

$selectedPrms = @(
  "convection-box-particles__convection-box-particles.prm",
  "convection-box-particles__convection-box-particles.prm",
  "convection-box-particles__convection-box-particles.prm",
  "convection-box-particles__convection-box-particles.prm",
  "convection-box-particles__convection-box-particles.prm",
  "convection-box-particles__convection-box-particles.prm",
  "convection-box__tutorial-onset-of-convection__model_input__tutorial.prm",
  "convection-box__tutorial-onset-of-convection__model_input__tutorial.prm",
  "crystal_preferred_orientation_olivine_fraters_billen_2021__olivineA.prm",
  "crystal_preferred_orientation_olivine_fraters_billen_2021__olivineA.prm",
  "inclusions__ellipse_ref.prm",
  "inclusions__rectangle_ref.prm",
  "muparser_temperature_example__muparser-temperature-example.prm",
  "muparser_temperature_example__muparser-temperature-example.prm",
  "muparser_temperature_example__muparser-temperature-example.prm",
  "muparser_temperature_example__muparser-temperature-example.prm",
  "muparser_temperature_example__muparser-temperature-example.prm",
  "sinker-with-averaging__sinker-with-averaging.prm",
  "sinker-with-averaging__sinker-with-averaging.prm",
  "sinker-with-averaging__sinker-with-averaging.prm",
  "sinker-with-averaging__sinker-with-averaging.prm"
)

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

function Set-PrmOutputDirectory {
  param(
    [string]$SourcePath,
    [string]$DestinationPath
  )

  $content = Get-Content -LiteralPath $SourcePath -Raw
  $pattern = "(?m)^(\s*set\s+Output directory\s*=).*$"

  if ($content -match $pattern) {
    $content = [regex]::Replace($content, $pattern, '${1} output', 1)
  }
  elseif ($content -match "(?m)^(\s*set\s+Dimension\s*=.*)$") {
    $content = [regex]::Replace($content, "(?m)^(\s*set\s+Dimension\s*=.*)$", "`$1`nset Output directory = output", 1)
  }
  else {
    $content = "set Output directory = output`n$content"
  }

  $content = $content -replace "`r`n", "`n"
  $content = $content -replace "`r", "`n"
  Set-Content -LiteralPath $DestinationPath -Value $content -NoNewline
}

New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

$preparedRuns = @()
$runNumber = 1

foreach ($prmName in $selectedPrms) {
  $sourcePath = Join-Path $inputDir $prmName
  if (-not (Test-Path -LiteralPath $sourcePath)) {
    throw "Missing input file: $sourcePath"
  }

  $caseName = [System.IO.Path]::GetFileNameWithoutExtension($prmName)
  $caseName = "{0:D2}_{1}" -f $runNumber, $caseName

  $caseDir = Join-Path $runRoot $caseName
  New-Item -ItemType Directory -Force -Path $caseDir | Out-Null

  $preparedPrm = Join-Path $caseDir "input.prm"
  Set-PrmOutputDirectory -SourcePath $sourcePath -DestinationPath $preparedPrm

  $preparedRuns += [pscustomobject]@{
    CaseName = $caseName
    PrmPath = $preparedPrm
  }
  $runNumber++
}

$runRootForDocker = if ($DockerCommand -eq "wsl docker") {
  ConvertTo-WslPath $runRoot
}
else {
  [System.IO.Path]::GetFullPath($runRoot)
}
Write-Host "Prepared $($preparedRuns.Count) ASPECT run directories under:"
Write-Host "  $runRoot"
Write-Host ""
Write-Host "Starting Docker image: $DockerImage"

foreach ($run in $preparedRuns) {
  Write-Host "=== Running $($run.CaseName) ==="

  $bashScript = "cd /workspace/$($run.CaseName) && aspect input.prm > aspect.log 2>&1"
  $dockerArgs = @(
    "run",
    "--rm",
    "-v",
    "${runRootForDocker}:/workspace",
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

  if ($LASTEXITCODE -ne 0) {
    throw "ASPECT failed for $($run.CaseName). Check $($run.PrmPath | Split-Path -Parent)\aspect.log"
  }
}

Write-Host ""
Write-Host "Done. Each case has:"
Write-Host "  input.prm   copied/rewritten parameter file"
Write-Host "  aspect.log  ASPECT console output"
Write-Host "  output\     ASPECT generated files"
