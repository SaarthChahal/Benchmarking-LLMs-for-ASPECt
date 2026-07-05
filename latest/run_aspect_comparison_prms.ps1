param(
  [string]$DockerImage = "geodynamics/aspect:latest",
  [string]$DockerCommand = "docker",
  [string]$RunId = (Get-Date -Format "yyyyMMdd_HHmmss"),
  [switch]$StopOnFailure
)

$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceDir = Join-Path $workspace "source_prm_dataset\files"
$regeneratedDir = Join-Path $workspace "runs\roundtrip_97prms_7models\regenerated_prms"
$runRoot = Join-Path $workspace ("runs\aspect_comparison_selected\" + $RunId)
$statusCsv = Join-Path $runRoot "run_status.csv"

$sourceBases = @(
  "convection-box-particles__convection-box-particles",
  "muparser_temperature_example__muparser-temperature-example",
  "sinker-with-averaging__sinker-with-averaging"
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

function ConvertTo-SafeName {
  param([string]$Name)
  return ($Name -replace '[<>:"/\\|?*]', '_')
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

New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

$runs = @()

foreach ($base in $sourceBases) {
  $sourcePath = Join-Path $sourceDir ($base + ".prm")
  if (-not (Test-Path -LiteralPath $sourcePath)) {
    throw "Missing source PRM: $sourcePath"
  }

  $sourceCaseRel = Join-Path "source" $base
  $sourceCaseDir = Join-Path $runRoot $sourceCaseRel
  New-Item -ItemType Directory -Force -Path $sourceCaseDir | Out-Null
  Set-PrmOutputDirectory -SourcePath $sourcePath -DestinationPath (Join-Path $sourceCaseDir "input.prm")

  $runs += [pscustomobject]@{
    Kind = "source"
    SourceName = $base
    ModelName = "source"
    OriginalPrm = $sourcePath
    CaseRelativePath = $sourceCaseRel
    CaseDirectory = $sourceCaseDir
  }

  $generatedMatches = Get-ChildItem -LiteralPath $regeneratedDir -Filter ($base + "__*.prm") | Sort-Object Name
  if ($generatedMatches.Count -ne 7) {
    Write-Warning "Expected 7 regenerated PRMs for $base, found $($generatedMatches.Count)."
  }

  foreach ($match in $generatedMatches) {
    $modelName = $match.BaseName.Substring($base.Length + 2)
    $safeModelName = ConvertTo-SafeName $modelName
    $generatedCaseRel = Join-Path (Join-Path "regenerated" $base) $safeModelName
    $generatedCaseDir = Join-Path $runRoot $generatedCaseRel
    New-Item -ItemType Directory -Force -Path $generatedCaseDir | Out-Null
    Set-PrmOutputDirectory -SourcePath $match.FullName -DestinationPath (Join-Path $generatedCaseDir "input.prm")

    $runs += [pscustomobject]@{
      Kind = "regenerated"
      SourceName = $base
      ModelName = $modelName
      OriginalPrm = $match.FullName
      CaseRelativePath = $generatedCaseRel
      CaseDirectory = $generatedCaseDir
    }
  }
}

$runRootForDocker = if ($DockerCommand -eq "wsl docker") {
  ConvertTo-WslPath $runRoot
}
else {
  [System.IO.Path]::GetFullPath($runRoot)
}

Write-Host "Prepared $($runs.Count) ASPECT comparison runs under:"
Write-Host "  $runRoot"
Write-Host ""
Write-Host "Expected layout:"
Write-Host "  source\<source-name>\output\"
Write-Host "  regenerated\<source-name>\<provider>__<model>\output\"
Write-Host ""
Write-Host "Starting Docker image: $DockerImage"

$results = @()

foreach ($run in $runs) {
  Write-Host "=== Running $($run.Kind): $($run.SourceName) [$($run.ModelName)] ==="
  $startedAt = Get-Date
  $exitCode = Invoke-DockerAspect -RunRootForDocker $runRootForDocker -CaseRelativePath $run.CaseRelativePath
  $finishedAt = Get-Date

  $logPath = Join-Path $run.CaseDirectory "aspect.log"
  $outputPath = Join-Path $run.CaseDirectory "output"
  $status = if ($exitCode -eq 0) { "success" } else { "failed" }

  $results += [pscustomobject]@{
    status = $status
    exit_code = $exitCode
    kind = $run.Kind
    source_name = $run.SourceName
    model_name = $run.ModelName
    case_directory = $run.CaseDirectory
    original_prm = $run.OriginalPrm
    aspect_log = $logPath
    output_directory = $outputPath
    started_at = $startedAt.ToString("s")
    finished_at = $finishedAt.ToString("s")
  }

  $results | Export-Csv -LiteralPath $statusCsv -NoTypeInformation

  if (($exitCode -ne 0) -and $StopOnFailure) {
    throw "ASPECT failed for $($run.SourceName) [$($run.ModelName)]. Check $logPath"
  }
}

Write-Host ""
Write-Host "Done. Status written to:"
Write-Host "  $statusCsv"
Write-Host ""
Write-Host "Summary:"
$results | Group-Object status | ForEach-Object {
  Write-Host ("  {0}: {1}" -f $_.Name, $_.Count)
}
