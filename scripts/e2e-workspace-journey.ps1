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

Step "Health check"
if (-not $DryRun) {
  $health = Invoke-ApiGet "/health"
  Ensure ($health.status -eq "ok") "API health check failed."
}

$setupA = Invoke-ApiPost "/profile/setup" @{
  user_id = $UserId
  native_lang = "de"
  target_lang = "en"
  level = "A2"
  goal = "travel"
  preferences = @{}
}

$userA = if ($DryRun) { 101 } else { [int]$setupA.user_id }

Step "Create and switch to second workspace"
$workspaceB = Invoke-ApiPost "/workspaces" @{
  native_lang = "es"
  target_lang = "ru"
  goal = "relocation"
  make_active = $true
}

$workspaceBId = if ($DryRun) { 2 } else { [int]$workspaceB.id }
$activeB = Invoke-ApiGet "/workspaces/active"
$userB = if ($DryRun) { 202 } else { [int]$activeB.active_user_id }
Ensure ($userB -ne $userA) "Expected isolated learner user per workspace."

$setupB = Invoke-ApiPost "/profile/setup" @{
  user_id = $userB
  native_lang = "es"
  target_lang = "ru"
  level = "A1"
  goal = "relocation"
  preferences = @{}
}
if (-not $DryRun) {
  Ensure (([int]$setupB.user_id) -eq $userB) "Second workspace profile setup failed."
}

Step "Generate different progress in each workspace"
[void](Invoke-ApiPost "/vocab/add" @{ user_id = $userA; word = "airport"; translation = "airport" })
[void](Invoke-ApiPost "/vocab/add" @{ user_id = $userA; word = "hotel"; translation = "hotel" })
[void](Invoke-ApiPost "/vocab/add" @{ user_id = $userB; word = "gracias"; translation = "thanks" })

if (-not $DryRun) {
  $summaryA = Invoke-ApiGet "/progress/summary?user_id=$userA"
  $summaryB = Invoke-ApiGet "/progress/summary?user_id=$userB"
  Ensure ($summaryA.words_learned -eq 2) "Workspace A words_learned mismatch."
  Ensure ($summaryB.words_learned -eq 1) "Workspace B words_learned mismatch."
}

Step "Switch to workspace B and validate bootstrap context"
[void](Invoke-ApiPost "/workspaces/switch" @{ workspace_id = $workspaceBId })
$bootstrapB = Invoke-ApiGet "/app/bootstrap"
if (-not $DryRun) {
  Ensure (([int]$bootstrapB.user_id) -eq $userB) "Bootstrap user did not switch to workspace B."
  Ensure (([int]$bootstrapB.active_workspace_id) -eq $workspaceBId) "Active workspace id mismatch for B."
}

Step "Switch back to workspace A and validate persistence"
$workspaces = Invoke-ApiGet "/workspaces"
$workspaceAId = if ($DryRun) { 1 } else { [int](($workspaces.items | Where-Object { $_.target_lang -eq "en" })[0].id) }
[void](Invoke-ApiPost "/workspaces/switch" @{ workspace_id = $workspaceAId })
$bootstrapA = Invoke-ApiGet "/app/bootstrap"
if (-not $DryRun) {
  Ensure (([int]$bootstrapA.user_id) -eq $userA) "Bootstrap user did not switch back to workspace A."
  Ensure (([int]$bootstrapA.active_workspace_id) -eq $workspaceAId) "Active workspace id mismatch for A."

  $summaryAAfter = Invoke-ApiGet "/progress/summary?user_id=$userA"
  $summaryBAfter = Invoke-ApiGet "/progress/summary?user_id=$userB"
  Ensure ($summaryAAfter.words_learned -eq 2) "Workspace A progress did not persist."
  Ensure ($summaryBAfter.words_learned -eq 1) "Workspace B progress did not persist."
}

Write-Host "Workspace journey E2E completed successfully." -ForegroundColor Green
