$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$tmpRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("bullydetector_publish_" + [guid]::NewGuid().ToString("N"))

New-Item -ItemType Directory -Path $tmpRoot | Out-Null

try {
    Push-Location $repoRoot
    $prefix = $tmpRoot.TrimEnd("\") + "\"
    git checkout-index -a -f --prefix="$prefix"
    Pop-Location

    Push-Location $tmpRoot
    git init | Out-Null
    git add -A
    git commit -m "Publish clean snapshot" | Out-Null
    git remote add origin https://github.com/ThantHtetMyet/Toxic-Speech-Detection.git
    git push -f origin HEAD:main
    Pop-Location
}
finally {
    if (Get-Location) {
        try { Pop-Location } catch {}
    }
    Remove-Item -Recurse -Force $tmpRoot -ErrorAction SilentlyContinue
}
