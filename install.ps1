# .hub installer for Windows
#
# Interactive:
#   install.bat                              install on this PC
#   install.bat -Ssh user@host               install on a remote Linux server (uses install.sh)
#   install.bat -Ssh user@host -Port 2222
#   install.bat -Ref v0.6.0                  install a specific tag or branch (default: latest tag)
#
# Non-interactive (used by the GUI installer), enabled by -Token:
#   install.ps1 -Token T -Password W [-Proxy P] [-Dir D]
#   install.ps1 -Check -Token T ...          only check the folder, proxy and token
# -Password is the password for the Telegram bot, written to config/telegram.toml; it is required
#
# Exit codes: 10 proxy does not work, 11 token is invalid, 12 Telegram is unreachable.
# Lines starting with @@ are read by the GUI: @@DIR_STATE=, @@BOT=, @@DIR=

param(
    [string]$Ssh = '',
    [int]$Port = 22,
    [string]$Ref = '',
    [string]$Dir = '',
    [string]$Token = '',
    [string]$Password = '',
    [string]$Proxy = '',
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
$RepoUrl = 'https://github.com/funpayhub/funpayhub'
try { [Console]::OutputEncoding = New-Object Text.UTF8Encoding $false } catch {}

function Info($text) { Write-Host '(・ω・) ' -ForegroundColor Cyan -NoNewline; Write-Host $text }
function Ok($text)   { Write-Host '(＾▽＾) ' -ForegroundColor Green -NoNewline; Write-Host $text }
function Warn($text) { Write-Host '(ಠ_ಠ) ' -ForegroundColor Yellow -NoNewline; Write-Host $text }
function Die($text)  { Write-Host '(x_x) ' -ForegroundColor Red -NoNewline; Write-Host $text; exit 1 }

function Check-Exit($what) {
    if ($LASTEXITCODE -ne 0) { Die "Не удалось выполнить: $what (код $LASTEXITCODE)" }
}

function Confirm($text, [bool]$default) {
    $hint = if ($default) { '[Y/n]' } else { '[y/N]' }
    $answer = Read-Host "$text $hint"
    if (-not $answer) { return $default }
    return $answer -match '^[yYдД]'
}

function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('Path', 'User')
}

function Write-Utf8($path, $text) {
    [IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding $false))
}

function Toml-Escape($text) {
    return $text.Replace('\', '\\').Replace('"', '\"')
}


# ---------- remote install ----------

if ($Ssh) {
    $shScript = Join-Path $PSScriptRoot 'install.sh'
    if (-not (Test-Path $shScript)) { Die 'Рядом с install.ps1 должен лежать install.sh' }
    Info "Копирую установщик на $Ssh"
    scp.exe -q -P $Port $shScript "${Ssh}:.dothub-install.sh"
    Check-Exit 'scp'
    $refArg = if ($Ref) { "--ref $Ref" } else { '' }
    ssh.exe -t -p $Port $Ssh "bash .dothub-install.sh $refArg; rm -f .dothub-install.sh"
    exit $LASTEXITCODE
}


# ---------- system ----------

function Ensure-Tool($command, $wingetId, $name, $url) {
    if (Get-Command $command -ErrorAction SilentlyContinue) { return }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Die "Не найдены $name и winget. Установите $name вручную: $url"
    }
    Info "Устанавливаю $name"
    winget install -e --id $wingetId --source winget --silent --accept-package-agreements --accept-source-agreements
    Check-Exit "winget install $wingetId"
    Refresh-Path
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        Die "$name установлен, но не найден в PATH. Перезапустите установщик"
    }
}


# ---------- folder, proxy and token ----------

function Resolve-InstallDir($path) {
    return $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($path)
}

function Get-DirState($path) {
    if (Test-Path (Join-Path $path 'launcher.py')) { return 'installed' }
    if ((Test-Path $path) -and (Get-ChildItem -Force $path | Select-Object -First 1)) { return 'notempty' }
    return 'empty'
}

# Returns @(http code, body). Code is '000' when Telegram is unreachable.
function Invoke-Telegram($url) {
    $curlArgs = @('-s', '--max-time', '15', '-w', '\n%{http_code}')
    if ($script:Proxy) { $curlArgs += @('--proxy', $script:Proxy) }
    $out = (& curl.exe @curlArgs $url) -join "`n"
    $i = $out.LastIndexOf("`n")
    if ($i -lt 0) { return @($out, '') }
    return @($out.Substring($i + 1), $out.Substring(0, $i))
}

function Test-Proxy {
    if ($script:Proxy -notmatch '^(socks5|http|https)://') {
        Warn 'Прокси должен начинаться с socks5://, http:// или https://'
        return $false
    }
    $code = (Invoke-Telegram 'https://api.telegram.org')[0]
    if ($code -eq '000') {
        Warn 'Не удалось подключиться к Telegram через этот прокси'
        return $false
    }
    Ok 'Прокси работает'
    return $true
}

# Returns 0 if the token is valid, 1 if not, 2 if Telegram is unreachable, 3 on an unexpected answer.
function Test-Token {
    if ($script:Token -notmatch '^\d+:[A-Za-z0-9_-]+$') {
        Warn 'Это не похоже на токен. Его можно получить у @BotFather'
        return 1
    }
    $code, $body = Invoke-Telegram "https://api.telegram.org/bot$($script:Token)/getMe"
    switch ($code) {
        '200' {
            $script:BotName = ($body | ConvertFrom-Json).result.username
            Ok "Токен подходит, бот @$($script:BotName)"
            return 0
        }
        { $_ -in '401', '404' } { Warn 'Telegram не принял токен, проверьте его'; return 1 }
        '000' { Warn 'Не удалось подключиться к Telegram. Возможно, нужен прокси'; return 2 }
        default { Warn "Неожиданный ответ Telegram (HTTP $code)"; return 3 }
    }
}

function Ask-InstallDir {
    $default = Join-Path $env:USERPROFILE 'dothub'
    while ($true) {
        $path = Read-Host "Куда установить .hub? [$default]"
        if (-not $path) { $path = $default }
        $path = Resolve-InstallDir $path

        $state = Get-DirState $path
        if ($state -ne 'empty') {
            if ($state -eq 'installed') { Warn ".hub уже установлен в $path" } else { Warn "Папка $path не пустая" }
            if (-not (Confirm 'Всё равно установить сюда?' $false)) { continue }
        }

        try {
            New-Item -ItemType Directory -Force $path | Out-Null
        } catch {
            Warn "Не удалось создать папку $path"
            continue
        }
        return $path
    }
}

function Ask-Proxy {
    while ($true) {
        $script:Proxy = Read-Host 'Прокси для Telegram (socks5://user:pass@host:port или http://...), Enter — без прокси'
        if (-not $script:Proxy -or (Test-Proxy)) { return }
    }
}

# Returns $false when Telegram is unreachable, so the proxy can be asked again.
function Ask-Token {
    while ($true) {
        $script:Token = Read-Host 'Токен Telegram-бота (выглядит так: 123456789:AAHg7K...)'
        switch (Test-Token) {
            0 { return $true }
            2 { return $false }
        }
    }
}

# Telegram trims messages, so a password with spaces at the ends could never be typed to the bot.
function Ask-Password {
    while ($true) {
        $script:Password = (Read-Host 'Пароль для доступа к боту (его нужно будет отправить боту при первом обращении)').Trim()
        if ($script:Password) { return }
        Warn 'Пароль обязателен'
    }
}


# ---------- main ----------

$interactive = -not $Token
if ($interactive) {
    Write-Host ''
    Write-Host '(◕‿◕) ' -ForegroundColor Cyan -NoNewline
    Write-Host 'Привет! Это установщик .hub'
    Write-Host ''
}

if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
    Die 'Не найден curl.exe. Нужна Windows 10 (1803) или новее'
}

if ($interactive) {
    $installDir = Ask-InstallDir
    while ($true) {
        Ask-Proxy
        if (Ask-Token) { break }
    }
    Ask-Password
} else {
    $installDir = Resolve-InstallDir $(if ($Dir) { $Dir } else { Join-Path $env:USERPROFILE 'dothub' })
    Write-Host "@@DIR_STATE=$(Get-DirState $installDir)"
    $script:Password = $Password.Trim()
    if (-not $script:Password) { Die 'Не указан пароль для доступа к боту (-Password)' }
    if ($Proxy -and -not (Test-Proxy)) { exit 10 }
    switch (Test-Token) {
        0 { Write-Host "@@BOT=$($script:BotName)" }
        1 { exit 11 }
        2 { exit 12 }
        default { exit 13 }
    }
    if ($Check) { exit 0 }
    New-Item -ItemType Directory -Force $installDir | Out-Null
}

Ensure-Tool 'git' 'Git.Git' 'Git' 'https://git-scm.com/download/win'
Ensure-Tool 'uv' 'astral-sh.uv' 'uv' 'https://docs.astral.sh/uv/'
$uv = (Get-Command uv).Source

if (-not $Ref) {
    $Ref = (git ls-remote --tags --refs --sort=-v:refname $RepoUrl 'v*' | Select-Object -First 1) -replace '.*refs/tags/', ''
    if (-not $Ref) { Die 'Не удалось получить список версий .hub' }
}

$tmp = Join-Path ([IO.Path]::GetTempPath()) ('dothub-install-' + [guid]::NewGuid())
$src = Join-Path $tmp 'src'
try {
    Info "Скачиваю .hub $Ref"
    git -c advice.detachedHead=false clone -q --depth 1 --branch $Ref $RepoUrl $src
    Check-Exit 'git clone'
    if (-not (Test-Path (Join-Path $src 'bootstrap.py'))) { Die "Версия $Ref не поддерживается установщиком" }

    $requires = '3'
    $match = Select-String -Path (Join-Path $src 'pyproject.toml') -Pattern '^requires-python\s*=\s*"(.+)"'
    if ($match) { $requires = $match.Matches[0].Groups[1].Value }

    Info "Устанавливаю Python $requires"
    & $uv venv -q --clear --python $requires (Join-Path $installDir '.venv')
    Check-Exit 'uv venv'

    Info 'Устанавливаю .hub и его зависимости, это может занять пару минут'
    $releaseScript = Join-Path $tmp 'install_release.py'
    Write-Utf8 $releaseScript @'
import sys
import shutil
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import bootstrap
import launcher

bootstrap.setup_logging(Path('logs'))
bootstrap.install(Path('releases').resolve())
shutil.copy2(launcher.__file__, 'launcher.py')
'@
    $env:HUBPLATFORM_UV_BIN = $uv
    Push-Location $installDir
    try {
        & (Join-Path $installDir '.venv\Scripts\python.exe') $releaseScript $src
        Check-Exit 'установка .hub'
    } finally {
        Pop-Location
    }
} finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}

$configDir = Join-Path $installDir 'config'
$config = Join-Path $configDir 'telegram.toml'
New-Item -ItemType Directory -Force $configDir | Out-Null
if (Test-Path $config) {
    Copy-Item $config "$config.bak" -Force
    Warn "Старый $config сохранён в telegram.toml.bak"
}
Write-Utf8 $config ("[bot]`ntoken = `"$($script:Token)`"`n" +
    "password = `"$(Toml-Escape $script:Password)`"`nproxy = `"$(Toml-Escape $script:Proxy)`"`n")

Write-Utf8 (Join-Path $installDir 'start.bat') @'
@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" launcher.py %*
if errorlevel 1 pause
'@

Write-Host ''
Ok ".hub установлен в $installDir"
Write-Host "@@DIR=$installDir"
Info "Запуск: $installDir\start.bat"
if ($interactive -and (Confirm 'Запустить .hub сейчас?' $true)) {
    Start-Process -FilePath (Join-Path $installDir 'start.bat') -WorkingDirectory $installDir
    Ok ".hub запущен в отдельном окне. Напишите боту @$($script:BotName) в Telegram и отправьте ему пароль"
}
