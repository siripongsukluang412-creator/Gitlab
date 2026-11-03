$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Get-Command py -ErrorAction SilentlyContinue) {
    py .\electrical.py @args
} else {
    python .\electrical.py @args
}
