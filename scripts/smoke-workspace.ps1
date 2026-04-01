param(
    [string]$ApiBaseUrl = "http://127.0.0.1:8000",
    [string]$ProjectId = "",
    [string]$EpisodeId = "",
    [ValidateSet("brief", "story_bible", "character", "script", "storyboard")]
    [string]$StartStage = "brief",
    [ValidateSet("approved", "request_changes", "rejected")]
    [string]$ReviewDecision = "approved",
    [int]$EpisodeNo = 1,
    [int]$TargetDurationSec = 75,
    [switch]$CreateViaApi
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$textStages = @("brief", "story_bible", "character", "script", "storyboard")
$reviewRequiredStages = @("brief", "storyboard")
$startIndex = [Array]::IndexOf($textStages, $StartStage)

if ($startIndex -lt 0) {
    throw "Unsupported text start stage: $StartStage"
}

if (([string]::IsNullOrWhiteSpace($ProjectId)) -xor ([string]::IsNullOrWhiteSpace($EpisodeId))) {
    throw "Provide both -ProjectId and -EpisodeId, or omit both and use -CreateViaApi."
}

if ([string]::IsNullOrWhiteSpace($ProjectId) -and [string]::IsNullOrWhiteSpace($EpisodeId)) {
    $CreateViaApi = $true
}

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Assert-True($Condition, [string]$Message) {
    if (-not $Condition) {
        throw "ASSERTION FAILED: $Message"
    }
}

function Invoke-Api {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Path,
        $Body = $null
    )

    $uri = "$ApiBaseUrl$Path"
    $params = @{
        Method = $Method
        Uri = $uri
        Headers = @{
            Accept = "application/json"
        }
    }

    if ($null -ne $Body) {
        $params.ContentType = "application/json"
        $params.Body = ($Body | ConvertTo-Json -Depth 10)
    }

    $response = Invoke-RestMethod @params
    if ($response -and $null -ne $response.data) {
        return $response.data
    }
    return $response
}

function New-SmokeProject {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    return Invoke-Api -Method POST -Path "/api/projects" -Body @{
        name = "Smoke Workspace $timestamp"
        source_mode = "adaptation"
        genre = "identity_reversal"
        target_platform = "douyin"
        target_audience = "demo-smoke"
    }
}

function New-SmokeEpisode([string]$ProjectIdValue) {
    return Invoke-Api -Method POST -Path "/api/projects/$ProjectIdValue/episodes" -Body @{
        episode_no = $EpisodeNo
        title = "Smoke Episode"
        target_duration_sec = $TargetDurationSec
    }
}

function Get-Workspace([string]$ProjectIdValue, [string]$EpisodeIdValue) {
    return Invoke-Api -Method GET -Path "/api/projects/$ProjectIdValue/episodes/$EpisodeIdValue/workspace"
}

function Get-Workflow([string]$ProjectIdValue, [string]$EpisodeIdValue) {
    return Invoke-Api -Method GET -Path "/api/projects/$ProjectIdValue/episodes/$EpisodeIdValue/workflow"
}

function Get-ExpectedStages {
    return $textStages[$startIndex..($textStages.Count - 1)]
}

function Get-ExpectedDocumentTypes {
    switch ($StartStage) {
        "brief" { return @("brief", "story_bible", "character_profile", "script_draft", "visual_spec") }
        "story_bible" { return @("story_bible", "character_profile", "script_draft", "visual_spec") }
        "character" { return @("character_profile", "script_draft", "visual_spec") }
        "script" { return @("script_draft", "visual_spec") }
        "storyboard" { return @("visual_spec") }
    }
}

Write-Step "Checking API health"
$health = Invoke-Api -Method GET -Path "/api/health"
Assert-True ($health.status -eq "ok") "API health endpoint should return ok"

if ($CreateViaApi) {
    Write-Step "Creating smoke project and episode via API"
    $project = New-SmokeProject
    $episode = New-SmokeEpisode -ProjectIdValue $project.id
    $ProjectId = $project.id
    $EpisodeId = $episode.id
} else {
    Write-Step "Using existing workspace identifiers"
}

Write-Host "ProjectId: $ProjectId"
Write-Host "EpisodeId: $EpisodeId"

Write-Step "Loading initial workspace"
$initialWorkspace = Get-Workspace -ProjectIdValue $ProjectId -EpisodeIdValue $EpisodeId
Assert-True ($initialWorkspace.episode.id -eq $EpisodeId) "Workspace should return the requested episode"

Write-Step "Starting workflow from $StartStage"
$startedWorkflow = Invoke-Api -Method POST -Path "/api/projects/$ProjectId/episodes/$EpisodeId/workflow/start" -Body @{
    start_stage = $StartStage
}
Assert-True ($startedWorkflow.workflow_kind -eq "episode") "Started workflow should be an episode workflow"
Assert-True ($startedWorkflow.status -eq "waiting_review") "Text workflow should finish in waiting_review"

Write-Step "Re-loading workflow and workspace after start"
$workflow = Get-Workflow -ProjectIdValue $ProjectId -EpisodeIdValue $EpisodeId
$workspaceAfterStart = Get-Workspace -ProjectIdValue $ProjectId -EpisodeIdValue $EpisodeId
$expectedStages = Get-ExpectedStages
$expectedDocumentTypes = Get-ExpectedDocumentTypes
$actualStageTypes = @($workspaceAfterStart.stage_tasks | ForEach-Object { $_.stage_type })
$actualDocumentTypes = @($workspaceAfterStart.documents | ForEach-Object { $_.document_type })
$actualShotCount = @($workspaceAfterStart.shots).Count
$expectedPendingBeforeReview = @($expectedStages | Where-Object { $_ -in $reviewRequiredStages }).Count

Assert-True ($workflow.status -eq "waiting_review") "Latest workflow should be waiting_review"
Assert-True ($workspaceAfterStart.latest_workflow.status -eq "waiting_review") "Workspace should surface latest waiting_review workflow"

foreach ($stage in $expectedStages) {
    Assert-True ($actualStageTypes -contains $stage) "Workspace should include stage task for $stage"
}

foreach ($documentType in $expectedDocumentTypes) {
    Assert-True ($actualDocumentTypes -contains $documentType) "Workspace should include document type $documentType"
}

Assert-True ($actualShotCount -ge 3) "Storyboard generation should create at least 3 shots"
Assert-True ($workspaceAfterStart.review_summary.pending_count -eq $expectedPendingBeforeReview) "Pending review count should match generated review gates"

$reviewTask = $workspaceAfterStart.stage_tasks |
    Where-Object { $_.stage_type -eq "storyboard" -and $_.review_status -eq "pending" } |
    Select-Object -First 1

if ($null -eq $reviewTask) {
    $reviewTask = $workspaceAfterStart.stage_tasks |
        Where-Object { $_.review_required -and ($_.review_status -eq "pending" -or $null -eq $_.review_status) } |
        Select-Object -First 1
}

Assert-True ($null -ne $reviewTask) "Workspace should expose a reviewable stage task"

Write-Step "Submitting review decision for $($reviewTask.stage_type)"
$review = Invoke-Api -Method POST -Path "/api/projects/$ProjectId/episodes/$EpisodeId/review" -Body @{
    stage_task_id = $reviewTask.id
    decision = $ReviewDecision
    decision_note = "Smoke script review for $($reviewTask.stage_type)"
}

Assert-True ($review.status -eq $ReviewDecision) "Review response should echo the submitted decision"
Assert-True ($review.stage_task_id -eq $reviewTask.id) "Review response should reference the reviewed stage task"

Write-Step "Re-loading workspace after review"
$workspaceAfterReview = Get-Workspace -ProjectIdValue $ProjectId -EpisodeIdValue $EpisodeId
$expectedPendingAfterReview = [Math]::Max(0, $expectedPendingBeforeReview - 1)

Assert-True ($workspaceAfterReview.review_summary.latest_decision.status -eq $ReviewDecision) "Latest review decision should match the submitted decision"
Assert-True ($workspaceAfterReview.review_summary.pending_count -eq $expectedPendingAfterReview) "Pending review count should drop by one after review submission"

if ($expectedPendingAfterReview -gt 0) {
    Assert-True ($workspaceAfterReview.review_summary.status -eq "pending") "Workspace should stay pending while review gates remain"
} else {
    Assert-True ($workspaceAfterReview.review_summary.status -eq $ReviewDecision) "Workspace summary should match the latest review decision once gates are cleared"
}

$shotTargetId = @($workspaceAfterReview.shots | Select-Object -First 1).id
Assert-True (-not [string]::IsNullOrWhiteSpace($shotTargetId)) "Workspace should expose at least one shot id for rerun testing"

Write-Step "Submitting rerun request"
$rerun = Invoke-Api -Method POST -Path "/api/projects/$ProjectId/episodes/$EpisodeId/workflow/rerun" -Body @{
    rerun_stage = "storyboard"
    target_shot_ids = @($shotTargetId)
}

Assert-True ($rerun.status -eq "accepted") "Rerun endpoint should return accepted"
Assert-True (@($rerun.target_shot_ids).Count -eq 1) "Rerun response should echo the target shot selection"

Write-Step "Smoke workflow completed"
Write-Host "All checks passed." -ForegroundColor Green
Write-Host "ProjectId: $ProjectId"
Write-Host "EpisodeId: $EpisodeId"