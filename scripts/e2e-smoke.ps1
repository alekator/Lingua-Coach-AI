param(
  [string]$BaseUrl = "http://localhost:8000",
  [int]$UserId = 1,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Step([string]$Message) {
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-ApiGet([string]$Path) {
  $url = "$BaseUrl$Path"
  if ($DryRun) {
    Write-Host "[DRY-RUN] GET $url"
    return @{}
  }
  return Invoke-RestMethod -Method Get -Uri $url
}

function Invoke-ApiPost([string]$Path, [object]$Body) {
  $url = "$BaseUrl$Path"
  if ($DryRun) {
    $json = $Body | ConvertTo-Json -Depth 8 -Compress
    Write-Host "[DRY-RUN] POST $url $json"
    return @{}
  }
  $jsonBody = $Body | ConvertTo-Json -Depth 8
  return Invoke-RestMethod -Method Post -Uri $url -ContentType "application/json" -Body $jsonBody
}

Step "Health check"
if (-not $DryRun) {
  $health = Invoke-ApiGet "/health"
  if ($health.status -ne "ok") {
    throw "API health check failed"
  }
}

Step "Bootstrap"
$bootstrap = Invoke-ApiGet "/app/bootstrap"

if ($DryRun) {
  $bootstrap = @{
    user_id = $UserId
    needs_onboarding = $true
  }
}

$targetLang = "en"
$nativeLang = "ru"
$goal = "travel"

if ($bootstrap.needs_onboarding) {
  Step "Placement test start"
  $start = Invoke-ApiPost "/profile/placement-test/start" @{
    user_id = $UserId
    native_lang = $nativeLang
    target_lang = $targetLang
  }

  if ($DryRun) {
    $start = @{
      session_id = 101
      total_questions = 3
    }
  }

  $sessionId = [int]$start.session_id
  $totalQuestions = [int]$start.total_questions

  for ($i = 0; $i -lt $totalQuestions; $i++) {
    Step "Placement answer $($i + 1)/$totalQuestions"
    [void](Invoke-ApiPost "/profile/placement-test/answer" @{
      session_id = $sessionId
      answer = "I practice English every day and can explain my plans clearly."
    })
  }

  Step "Placement finish"
  $finish = Invoke-ApiPost "/profile/placement-test/finish" @{
    session_id = $sessionId
  }

  $level = if ($DryRun) { "B1" } else { $finish.level }

  Step "Profile setup/update"
  [void](Invoke-ApiPost "/profile/setup" @{
    user_id = $UserId
    native_lang = $nativeLang
    target_lang = $targetLang
    level = $level
    goal = $goal
    preferences = @{ strictness = "medium" }
  })
}

Step "Chat lesson"
$chatStart = Invoke-ApiPost "/chat/start" @{
  user_id = $UserId
  mode = "chat"
}

$chatSessionId = if ($DryRun) { 555 } else { [int]$chatStart.session_id }

[void](Invoke-ApiPost "/chat/message" @{
  session_id = $chatSessionId
  text = "I did a mistake yesterday."
})

[void](Invoke-ApiPost "/chat/end" @{
  session_id = $chatSessionId
})

Step "Vocab add"
[void](Invoke-ApiPost "/vocab/add" @{
  user_id = $UserId
  word = "achieve"
  translation = "to achieve"
  example = "I want to achieve my goals."
})

Step "Progress summary"
$summary = Invoke-ApiGet "/progress/summary?user_id=$UserId"
if (-not $DryRun) {
  if ($null -eq $summary.words_learned) {
    throw "Progress summary response is missing expected fields"
  }
  Write-Host "Smoke complete. Streak=$($summary.streak_days), Minutes=$($summary.minutes_practiced), Words=$($summary.words_learned)" -ForegroundColor Green
} else {
  Write-Host "Dry-run smoke flow complete." -ForegroundColor Green
}
