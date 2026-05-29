param(
    [ValidateSet("setup", "start", "open", "stop", "status", "logs")]
    [string]$QuickAction = "open",
    [string]$JellyfinBaseUrl,
    [string]$JellyfinApiKey,
    [string]$MediaPath,
    [string]$InitialAdminUsername = "admin",
    [string]$InitialAdminPassword,
    [switch]$NoBrowser,
    [switch]$NonInteractive,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

$script:RepoRoot = Split-Path -Parent $PSCommandPath
$script:EnvExample = Join-Path $script:RepoRoot ".env.example"
$script:EnvFile = Join-Path $script:RepoRoot ".env"

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "=========================================="
    Write-Host $Title
    Write-Host "=========================================="
}

function Format-EnvValue {
    param([string]$Value)
    if ($null -eq $Value) {
        return ""
    }

    $normalized = $Value.Trim()
    if ($normalized -match "\s|#") {
        return '"' + ($normalized -replace '"', '\"') + '"'
    }

    return $normalized
}

function Ensure-EnvFile {
    if (-not (Test-Path -LiteralPath $script:EnvExample)) {
        throw ".env.example not found in repository root."
    }

    if (-not (Test-Path -LiteralPath $script:EnvFile)) {
        Copy-Item -LiteralPath $script:EnvExample -Destination $script:EnvFile
        Write-Host "Created .env from .env.example"
    }
}

function Get-EnvValue {
    param([string]$Key)
    if (-not (Test-Path -LiteralPath $script:EnvFile)) {
        return ""
    }

    $content = [System.IO.File]::ReadAllText($script:EnvFile)
    $match = [regex]::Match($content, "(?m)^$([regex]::Escape($Key))=(.*)$")
    if (-not $match.Success) {
        return ""
    }

    return $match.Groups[1].Value.Trim().Trim('"')
}

function Set-EnvValue {
    param(
        [string]$Key,
        [string]$Value
    )

    Ensure-EnvFile
    $content = [System.IO.File]::ReadAllText($script:EnvFile)
    $formatted = Format-EnvValue -Value $Value
    $replacement = "$Key=$formatted"
    $pattern = "(?m)^$([regex]::Escape($Key))=.*$"

    if ([regex]::IsMatch($content, $pattern)) {
        $updated = [regex]::Replace($content, $pattern, $replacement)
    }
    else {
        $separator = "`r`n"
        if ($content.EndsWith("`n")) {
            $separator = ""
        }
        $updated = $content + $separator + $replacement + "`r`n"
    }

    [System.IO.File]::WriteAllText($script:EnvFile, $updated, [System.Text.UTF8Encoding]::new($false))
}

function Prompt-Value {
    param(
        [string]$Label,
        [string]$CurrentValue,
        [switch]$Secret
    )

    if ($NonInteractive) {
        return $CurrentValue
    }

    if ($Secret) {
        $prompt = if ($CurrentValue) { "$Label (leave blank to keep current)" } else { $Label }
        $secure = Read-Host -Prompt $prompt -AsSecureString
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        try {
            $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
        }
        finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }

        if ([string]::IsNullOrWhiteSpace($plain)) {
            return $CurrentValue
        }

        return $plain
    }

    $displayDefault = if ($CurrentValue) { " [$CurrentValue]" } else { "" }
    $value = Read-Host -Prompt ($Label + $displayDefault)
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $CurrentValue
    }

    return $value.Trim()
}

function Ensure-DockerCompose {
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $docker) {
        throw "Docker Desktop is not installed or docker is not on PATH."
    }

    if (-not $WhatIf) {
        & $docker.Source compose version | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose is not available. Open Docker Desktop and try again."
        }
    }
}

function Invoke-DockerCompose {
    param([string[]]$Arguments)
    $display = "docker compose " + ($Arguments -join " ")
    if ($WhatIf) {
        Write-Host "[WhatIf] $display"
        return
    }

    $docker = Get-Command docker -ErrorAction Stop
    & $docker.Source compose @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $display"
    }
}

function Normalize-MediaPath {
    param([string]$Value)
    if (-not $Value) {
        return $Value
    }

    return ($Value.Trim() -replace "\\", "/")
}

function Invoke-Setup {
    Write-Section "FluxCaption Quick Setup"
    Ensure-EnvFile

    $jellyfinBaseUrlCurrent = Get-EnvValue -Key "JELLYFIN_BASE_URL"
    $jellyfinApiKeyCurrent = Get-EnvValue -Key "JELLYFIN_API_KEY"
    $mediaPathCurrent = Get-EnvValue -Key "MEDIA_PATH"
    $adminUserCurrent = (Get-EnvValue -Key "INITIAL_ADMIN_USERNAME")
    if (-not $adminUserCurrent) {
        $adminUserCurrent = "admin"
    }
    $adminPasswordCurrent = Get-EnvValue -Key "INITIAL_ADMIN_PASSWORD"

    if (-not $JellyfinBaseUrl) {
        $JellyfinBaseUrl = Prompt-Value -Label "Jellyfin URL (example: http://192.168.1.10:8096)" -CurrentValue $jellyfinBaseUrlCurrent
    }
    if (-not $JellyfinApiKey) {
        $JellyfinApiKey = Prompt-Value -Label "Jellyfin API Key" -CurrentValue $jellyfinApiKeyCurrent -Secret
    }
    if (-not $MediaPath) {
        $MediaPath = Prompt-Value -Label "Media folder path for Docker (example: D:/Media)" -CurrentValue $mediaPathCurrent
    }
    $MediaPath = Normalize-MediaPath -Value $MediaPath

    if (-not $InitialAdminUsername) {
        $InitialAdminUsername = $adminUserCurrent
    }
    $InitialAdminUsername = Prompt-Value -Label "Initial admin username" -CurrentValue $InitialAdminUsername

    if (-not $InitialAdminPassword) {
        $InitialAdminPassword = Prompt-Value -Label "Initial admin password" -CurrentValue $adminPasswordCurrent -Secret
    }

    if ($JellyfinBaseUrl) { Set-EnvValue -Key "JELLYFIN_BASE_URL" -Value $JellyfinBaseUrl }
    if ($JellyfinApiKey) { Set-EnvValue -Key "JELLYFIN_API_KEY" -Value $JellyfinApiKey }
    if ($MediaPath) { Set-EnvValue -Key "MEDIA_PATH" -Value $MediaPath }
    if ($InitialAdminUsername) { Set-EnvValue -Key "INITIAL_ADMIN_USERNAME" -Value $InitialAdminUsername }
    if ($InitialAdminPassword) { Set-EnvValue -Key "INITIAL_ADMIN_PASSWORD" -Value $InitialAdminPassword }

    Write-Host ""
    Write-Host "Setup completed."
    Write-Host "Next step: double-click quick-start.cmd"
}

function Invoke-Start {
    Write-Section "FluxCaption Quick Start"
    Ensure-EnvFile
    Ensure-DockerCompose

    Write-Host "Starting Docker services..."
    Invoke-DockerCompose -Arguments @("up", "-d", "--build")

    Write-Host ""
    Write-Host "FluxCaption is starting."
    Write-Host "App URL: http://localhost"
    Write-Host "API Docs: http://localhost/docs"
    Write-Host ""
    Write-Host "If this is the first start and you did not set INITIAL_ADMIN_PASSWORD,"
    Write-Host "run quick-logs.cmd and look for 'INITIAL ADMIN CREDENTIALS'."

    if (-not $NoBrowser) {
        if ($WhatIf) {
            Write-Host "[WhatIf] Would open http://localhost"
        }
        else {
            Start-Process "http://localhost"
        }
    }
}

function Invoke-Open {
    Write-Section "Open FluxCaption"
    if ($WhatIf) {
        Write-Host "[WhatIf] Would open http://localhost"
        return
    }

    Start-Process "http://localhost"
}

function Invoke-Stop {
    Write-Section "Stop FluxCaption"
    Ensure-DockerCompose
    Invoke-DockerCompose -Arguments @("stop")
    Write-Host "Stopped Docker services."
}

function Invoke-Status {
    Write-Section "FluxCaption Status"
    Ensure-DockerCompose
    Invoke-DockerCompose -Arguments @("ps")
}

function Invoke-Logs {
    Write-Section "FluxCaption Backend Logs"
    Ensure-DockerCompose
    Invoke-DockerCompose -Arguments @("logs", "--tail=200", "backend")
}

switch ($QuickAction) {
    "setup" { Invoke-Setup }
    "start" { Invoke-Start }
    "open" { Invoke-Open }
    "stop" { Invoke-Stop }
    "status" { Invoke-Status }
    "logs" { Invoke-Logs }
    default { throw "Unknown action: $QuickAction" }
}
