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

function Backup-IfExists {
  param([string]$Path)

  if (Test-Path -LiteralPath $Path) {
    $parent = Split-Path -Parent $Path
    $name = Split-Path -Leaf $Path
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backup = Join-Path $parent ($name + ".bak." + $stamp)
    Copy-Item -LiteralPath $Path -Destination $backup -Force
    return $backup
  }

  return $null
}

function Remove-FirstLineIfMatches {
  param(
    [string]$Path,
    [string]$Prefix
  )

  $content = Get-Content -LiteralPath $Path -Raw
  $lines = $content -split "`n", 2
  if ($lines.Count -gt 0) {
    $firstLine = $lines[0].TrimEnd("`r")
    if ($firstLine -like "$Prefix*") {
      $newContent = if ($lines.Count -gt 1) { $lines[1] } else { "" }
      Set-Content -LiteralPath $Path -Value $newContent -NoNewline
      return $true
    }
  }

  return $false
}

function Set-UnixLineEndings {
  param([string]$Path)

  $content = Get-Content -LiteralPath $Path -Raw
  $content = $content -replace "`r`n", "`n"
  $content = $content -replace "`r", "`n"
  Set-Content -LiteralPath $Path -Value $content -NoNewline
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

$workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
$sinkerMetaPath = Join-Path $BatchRoot "regenerated\sinker-with-averaging__sinker-with-averaging\meta-llama__llama-3.1-8b-instruct\input.prm"

$haikuPaths = @(
  (Join-Path $BatchRoot "regenerated\convection-box-particles__convection-box-particles\anthropic__claude-3-haiku\input.prm"),
  (Join-Path $BatchRoot "regenerated\muparser_temperature_example__muparser-temperature-example\anthropic__claude-3-haiku\input.prm"),
  (Join-Path $BatchRoot "regenerated\sinker-with-averaging__sinker-with-averaging\anthropic__claude-3-haiku\input.prm")
)

foreach ($path in $haikuPaths) {
  if (Test-Path -LiteralPath $path) {
    Backup-IfExists -Path $path | Out-Null
    $changed = Remove-FirstLineIfMatches -Path $path -Prefix "Here is the repaired ASPECT parameter file"
    Set-UnixLineEndings -Path $path
    if ($changed) {
      Write-Host "Repaired header in $path"
    }
  }
}

if (Test-Path -LiteralPath $sinkerMetaPath) {
  Backup-IfExists -Path $sinkerMetaPath | Out-Null
  $replacement = @"
set Dimension = 2
set Start time = 0
set End time = 0
set Output directory = output
set Pressure normalization = volume

subsection Geometry model
  set Model name = box

  subsection Box
    set X extent = 1.0000
    set Y extent = 1.0000
  end
end

subsection Boundary velocity model
  set Zero velocity boundary indicators = left, right, bottom, top
end

subsection Material model
  set Model name = simple
  set Material averaging = none

  subsection Simple model
    set Reference density = 1
    set Viscosity = 1
    set Thermal expansion coefficient = 0
    set Composition viscosity prefactor = 1e6
    set Density differential for compositional field 1 = 10
  end
end

subsection Gravity model
  set Model name = vertical

  subsection Vertical
    set Magnitude = 1
  end
end

subsection Initial temperature model
  set Model name = function

  subsection Function
    set Function expression = 0
  end
end

subsection Compositional fields
  set Number of fields = 1
end

subsection Initial composition model
  set Model name = function

  subsection Function
    set Variable names = x,y
    set Function expression = if( (sqrt((x-0.5)^2+(y-0.5)^2)>0.22) , 0 , 1 )
  end
end

subsection Mesh refinement
  set Initial global refinement = 6
  set Initial adaptive refinement = 0
end

subsection Postprocess
  set List of postprocessors = visualization, velocity statistics, composition statistics

  subsection Visualization
    set Output format = vtu
    set Time between graphical output = 0
    set List of output variables = material properties

    subsection Material properties
      set List of material properties = density, viscosity
    end
  end
end
"@
  Set-Content -LiteralPath $sinkerMetaPath -Value $replacement -NoNewline
  Write-Host "Replaced invalid sinker meta-llama input with a valid runnable version."
}

$missingCases = Get-ChildItem -LiteralPath $BatchRoot -Recurse -Filter "input.prm" |
  Where-Object { -not (Test-Path -LiteralPath (Join-Path $_.Directory.FullName "output")) } |
  ForEach-Object { $_.Directory.FullName.Substring($BatchRoot.Length + 1) }

if (-not $missingCases) {
  Write-Host "No missing output folders found under:"
  Write-Host "  $BatchRoot"
  exit 0
}

Write-Host "Will rerun $($missingCases.Count) cases missing output:"
$missingCases | ForEach-Object { Write-Host "  $_" }
Write-Host ""

foreach ($rel in $missingCases) {
  $caseDir = Join-Path $BatchRoot $rel
  $logPath = Join-Path $caseDir "aspect.log"

  if (Test-Path -LiteralPath $logPath) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Move-Item -LiteralPath $logPath -Destination (Join-Path $caseDir ("aspect.log.before-rerun." + $stamp)) -Force
  }

  Write-Host "=== Running $rel ==="
  $exitCode = Invoke-DockerAspect -RunRootForDocker $runRootForDocker -CaseRelativePath $rel
  Write-Host ("    -> exit_code={0}" -f $exitCode)
}

Write-Host ""
Write-Host "Done. Recheck missing outputs under:"
Write-Host "  $BatchRoot"
