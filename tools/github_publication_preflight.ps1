[CmdletBinding()]
param(
    [switch]$ActualPublicationContext,
    [switch]$RequireWorkflowScope,
    [string]$PrBodyFile = "",
    [string]$BaseCommit = "",
    [string]$HeadCommit = "",
    [string]$RepositoryRoot = (Get-Location).Path,
    [string]$PythonExecutable = ""
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
        [string]$Reason = "",
        [Parameter(Mandatory = $true)]
        [string]$NextAction
    )

    $result = [ordered]@{
        state = $State
        login = $Login
        push_permission = $PushPermission
        workflow_scope = $WorkflowScope
        next_action = $NextAction
    }
    if ($Reason) {
        $result.reason = $Reason
    }
    $result | ConvertTo-Json -Compress
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

if (-not $PrBodyFile -or -not $BaseCommit -or -not $HeadCommit) {
    Write-PreflightResult `
        -State "PR_CONTRACT_INVALID" `
        -ExitCode 6 `
        -Reason "missing_pr_contract_input" `
        -NextAction "Prepare the exact PR body and supply its path plus the exact base and head commits; no GitHub call was made."
}

if (-not $PythonExecutable) {
    $PythonExecutable = Join-Path $RepositoryRoot ".venv\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {
    Write-PreflightResult `
        -State "LOCAL_VALIDATION_ERROR" `
        -ExitCode 7 `
        -Reason "python_executable_missing" `
        -NextAction "Supply the repository Python executable and rerun locally; no GitHub call was made."
}

$admissionScript = Join-Path $PSScriptRoot "..\ci_master_admission.py"
try {
    $contractOutput = @(& $PythonExecutable -B $admissionScript `
        --validate-pr-body $PrBodyFile `
        --base-commit $BaseCommit `
        --head-commit $HeadCommit `
        --repository-root $RepositoryRoot 2>&1)
    $contractExitCode = $LASTEXITCODE
} catch {
    Write-PreflightResult `
        -State "LOCAL_VALIDATION_ERROR" `
        -ExitCode 7 `
        -Reason "pr_contract_validator_invocation_failed" `
        -NextAction "Stop and repair the local validator invocation; no GitHub call was made."
}
$contractText = $contractOutput -join "`n"
try {
    $contract = $contractText | ConvertFrom-Json -ErrorAction Stop
} catch {
    Write-PreflightResult `
        -State "LOCAL_VALIDATION_ERROR" `
        -ExitCode 7 `
        -Reason "pr_contract_validator_output_invalid" `
        -NextAction "Stop and repair the local validator invocation; no GitHub call was made."
}

if ($contractExitCode -ne 0 -or [string]$contract.state -ne "READY") {
    $contractReason = if ($contract.PSObject.Properties["reason"]) {
        [string]$contract.reason
    } else {
        "pr_contract_validation_failed"
    }
    Write-PreflightResult `
        -State "PR_CONTRACT_INVALID" `
        -ExitCode 6 `
        -Reason $contractReason `
        -NextAction "Correct the prepared PR body or exact diff evidence and rerun locally; no GitHub call was made."
}

$auth = Invoke-GhText -Arguments @(
    "auth",
    "status",
    "--hostname",
    "github.com",
    "--json",
    "hosts"
)
$authenticationFailure = $auth.Text -match "(?i)(bad credentials|invalid token|token.*invalid|HTTP 401|authentication failed)"
$networkFailure = $auth.Text -match "(?i)(HTTP 5\d\d|could not resolve|connection.*(failed|reset|timed out)|network is unreachable|TLS|timeout|deadline exceeded)"

if ($authenticationFailure) {
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

if ($auth.ExitCode -ne 0) {
    Write-PreflightResult `
        -State "RETRY_ACTUAL_CONTEXT" `
        -ExitCode 2 `
        -NextAction "The credential context was unavailable; retry the actual publication context once, then report a context failure without requesting login."
}

try {
    $authDocument = $auth.Text | ConvertFrom-Json -ErrorAction Stop
    $hostProperty = $authDocument.hosts.PSObject.Properties["github.com"]
    if ($null -eq $hostProperty) {
        throw "github.com authentication state is missing"
    }
    $activeAccounts = @($hostProperty.Value | Where-Object { $_.active -eq $true })
} catch {
    Write-PreflightResult `
        -State "RETRY_ACTUAL_CONTEXT" `
        -ExitCode 2 `
        -NextAction "The structured credential state was unavailable; retry the actual publication context once, then report a context failure without requesting login."
}

if ($activeAccounts.Count -ne 1) {
    Write-PreflightResult `
        -State "RETRY_ACTUAL_CONTEXT" `
        -ExitCode 2 `
        -NextAction "Exactly one active GitHub account was not available; retry the actual publication context once, then report a context failure without requesting login."
}

$activeAccount = $activeAccounts[0]
$login = [string]$activeAccount.login
$scopeNames = @(([string]$activeAccount.scopes).Split(",") | ForEach-Object { $_.Trim() })
$workflowScope = if ($RequireWorkflowScope) {
    $scopeNames -contains "workflow"
} else {
    $false
}

if ([string]$activeAccount.state -ne "success") {
    Write-PreflightResult `
        -State "AUTH_REJECTED" `
        -ExitCode 3 `
        -Login $login `
        -WorkflowScope $workflowScope `
        -NextAction "Stop and ask the Owner to restore GitHub authentication; include only this state, not raw credential output."
}

if ($login -ne "Jacelber" -or ($RequireWorkflowScope -and -not $workflowScope)) {
    Write-PreflightResult `
        -State "PERMISSION_MISSING" `
        -ExitCode 4 `
        -Login $login `
        -WorkflowScope $workflowScope `
        -NextAction "Stop and report the identity or workflow-scope mismatch; do not request login as a generic fix."
}

$permission = Invoke-GhText -Arguments @(
    "api",
    "repos/Jacelber/mtgo-data",
    "--jq",
    ".permissions.push"
)
$authenticationFailure = $permission.Text -match "(?i)(bad credentials|invalid token|token.*invalid|HTTP 401|authentication failed)"
$networkFailure = $permission.Text -match "(?i)(HTTP 5\d\d|could not resolve|connection.*(failed|reset|timed out)|network is unreachable|TLS|timeout|deadline exceeded)"

if ($authenticationFailure) {
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

if ($permission.ExitCode -ne 0) {
    Write-PreflightResult `
        -State "RETRY_ACTUAL_CONTEXT" `
        -ExitCode 2 `
        -NextAction "The repository permission context was unavailable; retry the actual publication context once, then report a context failure without requesting login."
}

$pushPermission = $permission.Text.Trim() -eq "true"
if (-not $pushPermission) {
    Write-PreflightResult `
        -State "PERMISSION_MISSING" `
        -ExitCode 4 `
        -Login $login `
        -PushPermission $pushPermission `
        -WorkflowScope $workflowScope `
        -NextAction "Stop and report the repository push-permission mismatch; do not request login as a generic fix."
}

Write-PreflightResult `
    -State "READY" `
    -ExitCode 0 `
    -Login $login `
    -PushPermission $pushPermission `
    -WorkflowScope $workflowScope `
    -NextAction "Continue with the repository-specific command-scoped publication path."
