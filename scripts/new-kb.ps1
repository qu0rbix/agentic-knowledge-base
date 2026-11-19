# usage: scripts\new-kb.ps1 <target-folder>
# Copies the template into a new folder, initialises git, and tells you how to start.
param([Parameter(Mandatory = $true)][string]$Target)
$here = Split-Path -Parent $PSScriptRoot
if (Test-Path $Target) { Write-Error "$Target already exists"; exit 1 }
Copy-Item -Recurse (Join-Path $here 'template') $Target
Set-Location $Target
git init -q; git config core.longpaths true
git add -A; git commit -qm "New knowledge base from agentic-knowledge-base template"
Write-Host "Created $Target. Next:"
Write-Host "  cd `"$Target`"; claude"
Write-Host "  then say: set up this KB   (runs the init-kb interview)"
