param(
    [Parameter(Mandatory = $true)]
    [string]$TaskId,

    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$ApiKey = "replace_with_strong_random_secret",
    [int]$IntervalSeconds = 5,
    [int]$TimeoutSeconds = 180
)

$start = Get-Date

while ($true) {
    $rid = [guid]::NewGuid().ToString()
    $raw = curl.exe -s "$BaseUrl/api/v1/admin/images/upload-tasks/$TaskId" -H "X-Admin-Api-Key: $ApiKey" -H "X-Request-ID: $rid"

    try {
        $task = $raw | ConvertFrom-Json
    }
    catch {
        Write-Output "TASK_PARSE_ERROR: $raw"
        exit 2
    }

    $status = "$($task.status)"
    $attempts = "$($task.attempts)"
    $error = "$($task.error)"
    Write-Output "status=$status attempts=$attempts error=$error"

    if ($status -eq "succeeded") {
        Write-Output "PASS: upload completed"
        exit 0
    }

    if ($status -eq "failed") {
        Write-Output "FAIL: upload failed"
        exit 1
    }

    $elapsed = ((Get-Date) - $start).TotalSeconds
    if ($elapsed -ge $TimeoutSeconds) {
        Write-Output "TIMEOUT: task still in progress after $TimeoutSeconds seconds"
        exit 3
    }

    Start-Sleep -Seconds $IntervalSeconds
}
