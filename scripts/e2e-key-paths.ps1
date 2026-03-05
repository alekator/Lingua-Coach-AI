param(
  [string]$BaseUrl = "http://localhost:8000",
  [int]$UserId = 1,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Step([string]$Message) {
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Ensure([bool]$Condition, [string]$Message) {
  if (-not $Condition) {
    throw $Message
  }
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
    $json = $Body | ConvertTo-Json -Depth 10 -Compress
    Write-Host "[DRY-RUN] POST $url $json"
    return @{}
  }
  $jsonBody = $Body | ConvertTo-Json -Depth 10
  return Invoke-RestMethod -Method Post -Uri $url -ContentType "application/json" -Body $jsonBody
}

$nativeLang = "ru"
$targetLang = "en"
$goal = "travel"

Step "Health check"
if (-not $DryRun) {
  $health = Invoke-ApiGet "/health"
  Ensure ($health.status -eq "ok") "API health check failed."
}

Step "Bootstrap + onboarding/profile"
$bootstrap = Invoke-ApiGet "/app/bootstrap"
if ($DryRun) {
  $bootstrap = @{
    user_id = $UserId
    needs_onboarding = $true
  }
}

if ($bootstrap.needs_onboarding) {
  $placement = Invoke-ApiPost "/profile/placement-test/start" @{
    user_id = $UserId
    native_lang = $nativeLang
    target_lang = $targetLang
  }
  if ($DryRun) {
    $placement = @{
      session_id = 1001
      total_questions = 3
    }
  }

  $placementSessionId = [int]$placement.session_id
  $totalQuestions = [int]$placement.total_questions
  Ensure ($totalQuestions -ge 1) "Placement start returned invalid total_questions."

  for ($i = 0; $i -lt $totalQuestions; $i++) {
    [void](Invoke-ApiPost "/profile/placement-test/answer" @{
      session_id = $placementSessionId
      answer = "I can explain plans and ask follow-up questions in English."
    })
  }

  $placementFinish = Invoke-ApiPost "/profile/placement-test/finish" @{
    session_id = $placementSessionId
  }
  $level = if ($DryRun) { "B1" } else { [string]$placementFinish.level }

  [void](Invoke-ApiPost "/profile/setup" @{
    user_id = $UserId
    native_lang = $nativeLang
    target_lang = $targetLang
    level = $level
    goal = $goal
    preferences = @{
      strictness = "medium"
      daily_minutes = 15
      persona_style = "coach"
    }
  })
}

Step "Daily planning path"
$plan = Invoke-ApiGet "/plan/today?user_id=$UserId&time_budget_minutes=15"
$sessionPlan = Invoke-ApiGet "/coach/session/today?user_id=$UserId&time_budget_minutes=15"
$nextActions = Invoke-ApiGet "/coach/next-actions?user_id=$UserId"
$dailyChallenge = Invoke-ApiGet "/coach/daily-challenge?user_id=$UserId"
$reactivation = Invoke-ApiGet "/coach/reactivation?user_id=$UserId"

if (-not $DryRun) {
  Ensure ($plan.tasks.Count -ge 1) "Daily plan does not contain tasks."
  Ensure ($sessionPlan.steps.Count -ge 1) "Coach session plan does not contain steps."
  Ensure ($nextActions.items.Count -ge 1) "Coach next actions are empty."
  Ensure ($null -ne $dailyChallenge.title -and $dailyChallenge.title.Length -gt 0) "Daily challenge title is missing."
  Ensure ($null -ne $reactivation.eligible) "Reactivation response is malformed."
}

Step "Chat learning path"
$chatStart = Invoke-ApiPost "/chat/start" @{
  user_id = $UserId
  mode = "chat"
}
$chatSessionId = if ($DryRun) { 2001 } else { [int]$chatStart.session_id }

$chatReply = Invoke-ApiPost "/chat/message" @{
  session_id = $chatSessionId
  text = "I did a mistake at airport yesterday."
}

[void](Invoke-ApiPost "/chat/end" @{
  session_id = $chatSessionId
})

if (-not $DryRun) {
  Ensure ($null -ne $chatReply.assistant_text -and $chatReply.assistant_text.Length -gt 0) "Chat reply is empty."
}

Step "Scenario path"
$scenarios = Invoke-ApiGet "/scenarios"
if ($DryRun) {
  $scenarios = @{
    items = @(@{ id = "job-interview" }, @{ id = "travel-hotel" })
  }
}
Ensure ($scenarios.items.Count -ge 1) "No scenarios returned."

$scenarioId = [string]$scenarios.items[0].id
$scenarioSelect = Invoke-ApiPost "/scenarios/select" @{
  user_id = $UserId
  scenario_id = $scenarioId
}

$scenarioScript = Invoke-ApiGet "/scenarios/script?scenario_id=$scenarioId&user_id=$UserId"
if ($DryRun) {
  $scenarioScript = @{
    steps = @(@{ id = "step-1" })
  }
}
Ensure ($scenarioScript.steps.Count -ge 1) "Scenario script does not contain steps."

$firstStepId = [string]$scenarioScript.steps[0].id
$scenarioTurn = Invoke-ApiPost "/scenarios/turn" @{
  user_id = $UserId
  scenario_id = $scenarioId
  step_id = $firstStepId
  user_text = "I would like to book a room and confirm details."
}
if (-not $DryRun) {
  Ensure ($null -ne $scenarioTurn.score) "Scenario turn score is missing."
}

Step "Progress + retention path"
[void](Invoke-ApiPost "/vocab/add" @{
  user_id = $UserId
  word = "achieve"
  translation = "to achieve"
  example = "I want to achieve my goals."
})

$summary = Invoke-ApiGet "/progress/summary?user_id=$UserId"
$journal = Invoke-ApiGet "/progress/journal?user_id=$UserId"
$weeklyGoal = Invoke-ApiGet "/progress/weekly-goal?user_id=$UserId"
$weeklyReview = Invoke-ApiGet "/progress/weekly-review?user_id=$UserId"
$rewards = Invoke-ApiGet "/progress/rewards?user_id=$UserId"

if (-not $DryRun) {
  Ensure ($null -ne $summary.words_learned) "Progress summary contract mismatch."
  Ensure ($null -ne $journal.weekly_sessions) "Progress journal contract mismatch."
  Ensure ($null -ne $weeklyGoal.target_minutes) "Weekly goal contract mismatch."
  Ensure ($null -ne $weeklyReview.next_focus) "Weekly review contract mismatch."
  Ensure ($null -ne $rewards.items) "Rewards contract mismatch."
}

Write-Host "Key E2E paths completed successfully." -ForegroundColor Green
