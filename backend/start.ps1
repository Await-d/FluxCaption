$ErrorActionPreference = "Stop"
$script:ScriptDir = Split-Path -Parent $PSCommandPath

function Initialize-LocalDatabaseFallback {
    if ($env:DATABASE_URL -and $env:DATABASE_URL -notmatch '@(postgres|mysql|mssql|db)(:|/|$)') {
        return
    }

    $sqlitePath = (Join-Path $script:ScriptDir "fluxcaption.db") -replace '\\', '/'
    if (Test-Path -LiteralPath (Join-Path $script:ScriptDir "fluxcaption.db")) {
        Remove-Item -LiteralPath (Join-Path $script:ScriptDir "fluxcaption.db") -Force
    }
    $env:DATABASE_URL = "sqlite:///$sqlitePath"
    $env:DB_VENDOR = "sqlite"
    Write-Host "Using local SQLite database for Windows startup: $env:DATABASE_URL"
}

function Resolve-PythonExecutable {
    $candidates = @()

    if ($env:VIRTUAL_ENV) {
        $candidates += (Join-Path $env:VIRTUAL_ENV "Scripts\python.exe")
    }

    $candidates += (Join-Path $script:ScriptDir ".venv\Scripts\python.exe")
    $candidates += (Join-Path $script:ScriptDir "venv\Scripts\python.exe")
    $candidates += (Join-Path $script:ScriptDir "env\Scripts\python.exe")

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return [PSCustomObject]@{
                FilePath = $candidate
                BaseArgs = @()
                Display = $candidate
            }
        }
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return [PSCustomObject]@{
            FilePath = $pythonCommand.Source
            BaseArgs = @()
            Display = $pythonCommand.Source
        }
    }

    $pyCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCommand) {
        return [PSCustomObject]@{
            FilePath = $pyCommand.Source
            BaseArgs = @("-3.11")
            Display = "$($pyCommand.Source) -3.11"
        }
    }

    throw "Python executable not found. Activate a virtual environment or install Python 3.11+."
}

function Invoke-PythonModule {
    param (
        $PythonCommand,
        [string[]]$ModuleArgs,
        [string]$ErrorMessage
    )

    $commandArgs = @($PythonCommand.BaseArgs) + @("-m") + $ModuleArgs
    & $PythonCommand.FilePath @commandArgs
    if ($LASTEXITCODE -ne 0) {
        throw $ErrorMessage
    }
}

$resolvedPython = Resolve-PythonExecutable
$pythonCommand = $resolvedPython
$celeryProcess = $null

Initialize-LocalDatabaseFallback

Write-Host "=========================================="
Write-Host "FluxCaption Backend Startup (Windows)"
Write-Host "=========================================="
Write-Host "Using Python: $($pythonCommand.Display)"

try {
    Invoke-PythonModule -PythonCommand $pythonCommand -ModuleArgs @("alembic", "--version") -ErrorMessage "Alembic is not installed in the selected Python environment. Run 'pip install -r requirements.txt' in backend first."
    Invoke-PythonModule -PythonCommand $pythonCommand -ModuleArgs @("celery", "--version") -ErrorMessage "Celery is not installed in the selected Python environment. Run 'pip install -r requirements.txt' in backend first."
    Invoke-PythonModule -PythonCommand $pythonCommand -ModuleArgs @("uvicorn", "--version") -ErrorMessage "Uvicorn is not installed in the selected Python environment. Run 'pip install -r requirements.txt' in backend first."

    Write-Host ""
    Write-Host "[1/3] Running database migrations..."
    Invoke-PythonModule -PythonCommand $pythonCommand -ModuleArgs @("alembic", "upgrade", "head") -ErrorMessage "Database migration failed!"
    Write-Host "Database migrations completed"

    Write-Host ""
    Write-Host "[2/3] Starting Celery worker..."
    $celeryArgs = @($pythonCommand.BaseArgs) + @(
        "-m", "celery",
        "-A", "app.workers.celery_app",
        "worker",
        "-l", "INFO",
        "-Q", "translate,scan,asr",
        "--pool=solo"
    )
    $celeryProcess = Start-Process -FilePath $pythonCommand.FilePath -ArgumentList $celeryArgs -PassThru
    Write-Host "Celery worker started (PID: $($celeryProcess.Id))"

    Write-Host ""
    Write-Host "[3/3] Starting FastAPI application..."
    Write-Host "=========================================="
    $reloadEnabled = $env:FLUXCAPTION_RELOAD -in @("1", "true", "TRUE", "yes", "YES")
    if ($reloadEnabled) {
        Write-Host "Uvicorn reload: enabled"
    } else {
        Write-Host "Uvicorn reload: disabled (set FLUXCAPTION_RELOAD=1 to enable)"
    }

    $uvicornArgs = @($pythonCommand.BaseArgs) + @(
        "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000"
    )
    if ($reloadEnabled) {
        $uvicornArgs += "--reload"
    }
    & $pythonCommand.FilePath @uvicornArgs
    $expectedStopExitCodes = @(0, 3, -1073741510, 3221225786)
    if ($expectedStopExitCodes -notcontains $LASTEXITCODE) {
        throw "FastAPI application failed to start."
    }
}
finally {
    if ($celeryProcess -and -not $celeryProcess.HasExited) {
        Write-Host ""
        Write-Host "Stopping Celery worker..."
        Stop-Process -Id $celeryProcess.Id -Force
    }
}
