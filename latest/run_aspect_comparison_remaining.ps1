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
$runRoot = Join-Path $workspace ("runs\aspect_comparison_remaining\" + $RunId)
$statusCsv = Join-Path $runRoot "run_status.csv"

$remainingRuns = @(
  [pscustomobject]@{
    Kind = "regenerated"
    SourceName = "muparser_temperature_example__muparser-temperature-example"
    ModelName = "openai__gpt-4o"
  },
  [pscustomobject]@{
    Kind = "regenerated"
    SourceName = "muparser_temperature_example__muparser-temperature-example"
    ModelName = "openai__gpt-4o-mini"
  },
  [pscustomobject]@{
    Kind = "regenerated"
    SourceName = "muparser_temperature_example__muparser-temperature-example"
    ModelName = "qwen__qwen3-32b"
  },
  [pscustomobject]@{
    Kind = "source"
    SourceName = "sinker-with-averaging__sinker-with-averaging"
    ModelName = "source"
  },
  [pscustomobject]@{
    Kind = "regenerated"
    SourceName = "sinker-with-averaging__sinker-with-averaging"
    ModelName = "anthropic__claude-3.5-haiku"
  },
  [pscustomobject]@{
    Kind = "regenerated"
    SourceName = "sinker-with-averaging__sinker-with-averaging"
    ModelName = "anthropic__claude-3-haiku"
  },
  [pscustomobject]@{
    Kind = "regenerated"
    SourceName = "sinker-with-averaging__sinker-with-averaging"
    ModelName = "deepseek__deepseek-v3.2"
  },
  [pscustomobject]@{
    Kind = "regenerated"
    SourceName = "sinker-with-averaging__sinker-with-averaging"
    ModelName = "meta-llama__llama-3.1-8b-instruct"
  },
  [pscustomobject]@{
    Kind = "regenerated"
    SourceName = "sinker-with-averaging__sinker-with-averaging"
    ModelName = "openai__gpt-4o"
  },
  [pscustomobject]@{
    Kind = "regenerated"
    SourceName = "sinker-with-averaging__sinker-with-averaging"
    ModelName = "openai__gpt-4o-mini"
  },
  [pscustomobject]@{
    Kind = "regenerated"
    SourceName = "sinker-with-averaging__sinker-with-averaging"
    ModelName = "qwen__qwen3-32b"
  }
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

$preparedRuns = @()

foreach ($run in $remainingRuns) {
  if ($run.Kind -eq "source") {
    $prmPath = Join-Path $sourceDir ($run.SourceName + ".prm")
    $caseRel = Join-Path "source" $run.SourceName
  }
  else {
    $prmPath = Join-Path $regeneratedDir ($run.SourceName + "__" + $run.ModelName + ".prm")
    $caseRel = Join-Path (Join-Path "regenerated" $run.SourceName) (ConvertTo-SafeName $run.ModelName)
  }

  if (-not (Test-Path -LiteralPath $prmPath)) {
    throw "Missing PRM: $prmPath"
  }

  $caseDir = Join-Path $runRoot $caseRel
  New-Item -ItemType Directory -Force -Path $caseDir | Out-Null
  Set-PrmOutputDirectory -SourcePath $prmPath -DestinationPath (Join-Path $caseDir "input.prm")

  $preparedRuns += [pscustomobject]@{
    Kind = $run.Kind
    SourceName = $run.SourceName
    ModelName = $run.ModelName
    OriginalPrm = $prmPath
    CaseRelativePath = $caseRel
    CaseDirectory = $caseDir
  }
}

$runRootForDocker = if ($DockerCommand -eq "wsl docker") {
  ConvertTo-WslPath $runRoot
}
else {
  [System.IO.Path]::GetFullPath($runRoot)
}

Write-Host "Prepared $($preparedRuns.Count) remaining ASPECT comparison runs under:"
Write-Host "  $runRoot"
Write-Host ""
Write-Host "Starting Docker image: $DockerImage"

$results = @()

foreach ($run in $preparedRuns) {
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
  Write-Host ("    -> {0} ({1})" -f $status.ToUpperInvariant(), $finishedAt.ToString("HH:mm:ss"))

  if (($exitCode -ne 0) -and $StopOnFailure) {
    throw "ASPECT failed for $($run.SourceName) [$($run.ModelName)]. Check $logPath"
  }
}

Write-Host ""
Write-Host "Done. Status written to:"
Write-Host "  $statusCsv"

