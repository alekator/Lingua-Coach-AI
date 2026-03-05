param(
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if ($DryRun) {
  Write-Host "[DRY-RUN] ..\\..\\.venv\\Scripts\\python.exe -m pytest tests/test_teacher_eval_harness.py tests/test_content_quality.py -q"
  exit 0
}

Push-Location "services/api"
try {
  ..\..\.venv\Scripts\python.exe -m pytest tests/test_teacher_eval_harness.py tests/test_content_quality.py -q
} finally {
  Pop-Location
}
