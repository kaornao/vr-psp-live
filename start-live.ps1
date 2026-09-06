# Start VR/PSP live auto-updating local website
Set-Location $PSScriptRoot
Write-Host "Starting live board at http://127.0.0.1:8765/"
Write-Host "Keep this window open. Ctrl+C to stop."
python scripts\live_site.py --interval 45
