param(
  [string]$BaseUrl = "http://localhost:8000",
  [int]$UserId = 1,
  [string]$AudioSamplePath = ""
)

$ErrorActionPreference = "Stop"

function Invoke-TimedJson {
  param(
    [string]$Method,
    [string]$Url,
    [object]$Body = $null
  )
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  if ($null -eq $Body) {
    $resp = Invoke-RestMethod -Method $Method -Uri $Url
  } else {
    $json = $Body | ConvertTo-Json -Depth 8
    $resp = Invoke-RestMethod -Method $Method -Uri $Url -ContentType "application/json" -Body $json
  }
  $sw.Stop()
  return [PSCustomObject]@{
    DurationMs = [math]::Round($sw.Elapsed.TotalMilliseconds, 2)
    Body       = $resp
  }
}

Write-Host "== LinguaCoach Local Runtime E2E ==" -ForegroundColor Cyan

$results = @()

$health = Invoke-TimedJson -Method Get -Url "$BaseUrl/health"
$results += [PSCustomObject]@{ Name = "api.health"; DurationMs = $health.DurationMs; Ok = $true }

$runtime = Invoke-TimedJson -Method Get -Url "$BaseUrl/settings/ai-runtime?probe=true"
$results += [PSCustomObject]@{ Name = "settings.ai-runtime(probe)"; DurationMs = $runtime.DurationMs; Ok = $true }

$setup = Invoke-TimedJson -Method Post -Url "$BaseUrl/profile/setup" -Body @{
  user_id = $UserId
  native_lang = "en"
  target_lang = "ru"
  level = "A2"
  goal = "travel"
  preferences = @{ strictness = "medium" }
}
$results += [PSCustomObject]@{ Name = "profile.setup"; DurationMs = $setup.DurationMs; Ok = $true }

$start = Invoke-TimedJson -Method Post -Url "$BaseUrl/chat/start" -Body @{
  user_id = $UserId
  mode = "chat"
}
$results += [PSCustomObject]@{ Name = "chat.start"; DurationMs = $start.DurationMs; Ok = $true }

$sessionId = [int]$start.Body.session_id
$msg = Invoke-TimedJson -Method Post -Url "$BaseUrl/chat/message" -Body @{
  session_id = $sessionId
  text = "I want to check in at the hotel and ask for late checkout."
}
$results += [PSCustomObject]@{ Name = "chat.message"; DurationMs = $msg.DurationMs; Ok = $true }

$translate = Invoke-TimedJson -Method Post -Url "$BaseUrl/translate" -Body @{
  user_id = $UserId
  text = "Where is the nearest train station?"
  source_lang = "en"
  target_lang = "ru"
  voice = $false
}
$results += [PSCustomObject]@{ Name = "translate.text"; DurationMs = $translate.DurationMs; Ok = $true }

if ($AudioSamplePath -and (Test-Path $AudioSamplePath)) {
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  $form = @{
    file = Get-Item $AudioSamplePath
    user_id = "$UserId"
    target_lang = "ru"
    language_hint = "auto"
    voice_name = "alloy"
  }
  $voiceResp = Invoke-RestMethod -Method Post -Uri "$BaseUrl/voice/message" -Form $form
  $sw.Stop()
  $results += [PSCustomObject]@{
    Name = "voice.message"
    DurationMs = [math]::Round($sw.Elapsed.TotalMilliseconds, 2)
    Ok = $true
  }
} else {
  Write-Host "Skipping voice.message (AudioSamplePath not provided or file not found)." -ForegroundColor Yellow
}

$avg = [math]::Round((($results | Measure-Object -Property DurationMs -Average).Average), 2)
$max = [math]::Round((($results | Measure-Object -Property DurationMs -Maximum).Maximum), 2)

Write-Host "`n== Results ==" -ForegroundColor Green
$results | Format-Table -AutoSize
Write-Host "Average latency: $avg ms"
Write-Host "Max latency: $max ms"
Write-Host "Stability: $($results.Count)/$($results.Count) successful calls"
