[CmdletBinding()]
param(
    [switch]$ActualPublicationContext,
    [switch]$RequireWorkflowScope
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-PreflightResult {
    param(
        [Parameter(Mandatory = $true)]
        [string]$State,
        [Parameter(Mandatory = $true)]
        [int]$ExitCode,
        [string]$Login = "",
        [AllowNull()]
        [Nullable[bool]]$PushPermission = $null,
        [AllowNull()]
        [Nullable[bool]]$WorkflowScope = $null,
        [Parameter(Mandatory = $true)]
        [string]$NextAction
    )

    [ordered]@{
        state = $State
        login = $Login
        push_permission = $PushPermission
        workflow_scope = $WorkflowScope
        next_action = $NextAction
    } | ConvertTo-Json -Compress
    exit $ExitCode
}

function Invoke-GhText {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $output = @(& gh @Arguments 2>&1)
    [pscustomobject]@{
        ExitCode = $LASTEXITCODE
        Text = ($output -join "`n")
    }
}

if (-not $ActualPublicationContext) {
    Write-PreflightResult `
        -State "RETRY_ACTUAL_CONTEXT" `
        -ExitCode 2 `
        -NextAction "Rerun once in the actual publication context; do not ask the Owner to log in."
}

$auth = Invoke-GhText -Arguments @("auth", "status", "-h", "github.com")
$user = Invoke-GhText -Arguments @("api", "user", "--jq", ".login")
$permission = Invoke-GhText -Arguments @(
    "api",
    "repos/Jacelber/mtgo-data",
    "--jq",
    ".permissions.push"
)

$login = if ($user.ExitCode -eq 0) { $user.Text.Trim() } else { "" }
$pushPermission = if ($permission.ExitCode -eq 0) {
    $permission.Text.Trim() -eq "true"
} else {
    $null
}
$workflowScope = if ($RequireWorkflowScope -and $auth.ExitCode -eq 0) {
    $auth.Text -match '(?im)Token scopes:.*\bworkflow\b'
} elseif ($RequireWorkflowScope) {
    $null
} else {
    $false
}

if ($user.ExitCode -eq 0 -and $permission.ExitCode -eq 0) {
    if ($login -ne "Jacelber" -or -not $pushPermission) {
        Write-PreflightResult `
            -State "PERMISSION_MISSING" `
            -ExitCode 4 `
            -Login $login `
            -PushPermission $pushPermission `
            -WorkflowScope $workflowScope `
            -NextAction "Stop and report the identity or repository permission mismatch; do not request login as a generic fix."
    }

    if ($RequireWorkflowScope -and $workflowScope -ne $true) {
        $state = if ($auth.ExitCode -eq 0) {
            "PERMISSION_MISSING"
        } else {
            "RETRY_ACTUAL_CONTEXT"
        }
        $exitCode = if ($state -eq "PERMISSION_MISSING") { 4 } else { 2 }
        Write-PreflightResult `
            -State $state `
            -ExitCode $exitCode `
            -Login $login `
            -PushPermission $pushPermission `
            -WorkflowScope $workflowScope `
            -NextAction "Stop without a login request unless an actual-context authentication rejection is confirmed."
    }

    Write-PreflightResult `
        -State "READY" `
        -ExitCode 0 `
        -Login $login `
        -PushPermission $pushPermission `
        -WorkflowScope $workflowScope `
        -NextAction "Continue with the repository-specific command-scoped publication path."
}

$combinedError = "$($auth.Text)`n$($user.Text)`n$($permission.Text)"
$authenticationFailure = $combinedError -match "(?i)(bad credentials|invalid token|token.*invalid|HTTP 401|authentication failed)"
$networkFailure = $combinedError -match "(?i)(could not resolve|connection.*(failed|reset|timed out)|network is unreachable|TLS|timeout)"

if ($auth.ExitCode -ne 0 -and $user.ExitCode -ne 0 -and $authenticationFailure) {
    Write-PreflightResult `
        -State "AUTH_REJECTED" `
        -ExitCode 3 `
        -NextAction "Stop and ask the Owner to restore GitHub authentication; include only this state, not raw credential output."
}

if ($networkFailure) {
    Write-PreflightResult `
        -State "NETWORK_ERROR" `
        -ExitCode 5 `
        -NextAction "Stop and report a network or GitHub availability failure; do not ask the Owner to log in."
}

Write-PreflightResult `
    -State "RETRY_ACTUAL_CONTEXT" `
    -ExitCode 2 `
    -NextAction "The credential context was unavailable; retry the actual publication context once, then report a context failure without requesting login."
