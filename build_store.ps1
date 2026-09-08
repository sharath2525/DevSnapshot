[CmdletBinding()]
param(
    [ValidatePattern('^[1-9][0-9]{0,4}\.[0-9]{1,5}\.[0-9]{1,5}\.0$')]
    [string]$Version = '1.0.0.0'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$versionParts = $Version.Split('.') | ForEach-Object { [int]$_ }
if ($versionParts | Where-Object { $_ -gt 65535 }) {
    throw 'Each MSIX version component must be between 0 and 65535.'
}

$repoRoot = $PSScriptRoot
$tempEnvironment = Join-Path ([IO.Path]::GetTempPath()) ("ds-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
$storeBuild = Join-Path $repoRoot 'build\store'
$appDist = Join-Path $storeBuild 'app-dist'
$pyInstallerWork = Join-Path $storeBuild 'pyinstaller'
$packageRoot = Join-Path $storeBuild 'package'
$packageAssets = Join-Path $packageRoot 'Assets'
$storeOutput = Join-Path $repoRoot 'dist\store'
$listingOutput = Join-Path $storeOutput 'listing'
$msixPath = Join-Path $storeOutput ("DevSnapshot_{0}_x64.msix" -f $Version)
$existingVenvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
$createdTemporaryEnvironment = $false

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE`: $FilePath"
    }
}

try {
    if (Test-Path -LiteralPath $existingVenvPython) {
        $python = $existingVenvPython
    }
    else {
        $launcher = Get-Command py -ErrorAction SilentlyContinue
        if (-not $launcher) {
            throw 'Python launcher (py.exe) was not found. Install Python 3.12 for Windows.'
        }
        Invoke-Checked $launcher.Source '-3.12' '-m' 'venv' $tempEnvironment
        $python = Join-Path $tempEnvironment 'Scripts\python.exe'
        $createdTemporaryEnvironment = $true
    }

    Invoke-Checked $python '-m' 'pip' 'install' '--disable-pip-version-check' '-r' (Join-Path $repoRoot 'requirements.txt')
    Invoke-Checked $python '-B' '-m' 'unittest' 'discover' '-s' (Join-Path $repoRoot 'tests') '-v'

    if (Test-Path -LiteralPath $storeBuild) {
        Remove-Item -LiteralPath $storeBuild -Recurse -Force
    }
    if (Test-Path -LiteralPath $storeOutput) {
        Remove-Item -LiteralPath $storeOutput -Recurse -Force
    }
    New-Item -ItemType Directory -Path $appDist, $pyInstallerWork, $packageRoot, $packageAssets, $listingOutput -Force | Out-Null

    $originalPath = $env:PATH
    try {
        $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot;$env:SystemRoot\System32\Wbem;$env:SystemRoot\System32\WindowsPowerShell\v1.0\;$env:SystemRoot\System32\OpenSSH\"
        Invoke-Checked $python '-B' '-m' 'PyInstaller' '--clean' '--noconfirm' '--distpath' $appDist '--workpath' $pyInstallerWork (Join-Path $repoRoot 'DevSnapshotStore.spec')
    }
    finally {
        $env:PATH = $originalPath
    }

    $appOutput = Join-Path $appDist 'DevSnapshot'
    $appExe = Join-Path $appOutput 'DevSnapshot.exe'
    if (-not (Test-Path -LiteralPath $appExe)) {
        throw "Store build did not produce $appExe"
    }

    $previousSmoke = $env:DEVSNAPSHOT_SMOKE_TEST
    $env:DEVSNAPSHOT_SMOKE_TEST = '1'
    try {
        $smoke = Start-Process -FilePath $appExe -PassThru -Wait
        if ($smoke.ExitCode -ne 0) {
            throw "Store executable smoke test failed with exit code $($smoke.ExitCode)"
        }
    }
    finally {
        if ($null -eq $previousSmoke) {
            Remove-Item Env:DEVSNAPSHOT_SMOKE_TEST -ErrorAction SilentlyContinue
        }
        else {
            $env:DEVSNAPSHOT_SMOKE_TEST = $previousSmoke
        }
    }

    Get-ChildItem -LiteralPath $appOutput -Force | Copy-Item -Destination $packageRoot -Recurse -Force
    Copy-Item -LiteralPath (Join-Path $repoRoot 'LICENSE') -Destination $packageRoot
    Copy-Item -LiteralPath (Join-Path $repoRoot 'README.md') -Destination $packageRoot
    Copy-Item -LiteralPath (Join-Path $repoRoot 'PRIVACY.md') -Destination $packageRoot

    Invoke-Checked $python '-B' (Join-Path $repoRoot 'store\generate_store_assets.py') `
        '--source' (Join-Path $repoRoot 'resources\icons\devsnapshot.png') `
        '--package-output' $packageAssets `
        '--listing-output' $listingOutput

    $manifestTemplate = Get-Content -LiteralPath (Join-Path $repoRoot 'store\AppxManifest.xml.template') -Raw
    $manifest = $manifestTemplate.Replace('__VERSION__', $Version)
    $manifestPath = Join-Path $packageRoot 'AppxManifest.xml'
    Set-Content -LiteralPath $manifestPath -Value $manifest -Encoding utf8

    $makeAppx = Get-ChildItem -Path "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\makeappx.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName |
        Select-Object -Last 1
    if (-not $makeAppx) {
        throw 'MakeAppx.exe was not found. Install the Windows 10/11 SDK.'
    }

    Invoke-Checked $makeAppx.FullName 'pack' '/d' $packageRoot '/p' $msixPath '/o'
    Write-Host ''
    Write-Host "Microsoft Store package: $msixPath"
    Write-Host "Store listing logo: $listingOutput\DevSnapshot-StoreLogo-300x300.png"
    Write-Host 'The MSIX is intentionally unsigned for Partner Center submission.'
}
finally {
    if ($createdTemporaryEnvironment -and (Test-Path -LiteralPath $tempEnvironment)) {
        Remove-Item -LiteralPath $tempEnvironment -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path -LiteralPath $storeBuild) {
        Remove-Item -LiteralPath $storeBuild -Recurse -Force -ErrorAction SilentlyContinue
    }
}
