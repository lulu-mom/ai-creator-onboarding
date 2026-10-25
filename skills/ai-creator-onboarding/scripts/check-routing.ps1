# check-routing: list installed skills that are missing from the phrase -> skill routing table in CLAUDE.md.
# Usage: powershell -ExecutionPolicy Bypass -File check-routing.ps1 [-Rules $HOME\.claude\CLAUDE.md] [-Ignore a,b]
# A skill counts as listed when its name appears in backticks (`name`) in the rules file.
param(
  [string]$Rules = "$HOME\.claude\CLAUDE.md",
  [string]$SkillsDir = "$HOME\.claude\skills",
  [string[]]$Ignore = @()
)

if (-not (Test-Path $Rules)) { Write-Host "routing check: rules file not found: $Rules"; exit 2 }
if (-not (Test-Path $SkillsDir)) { Write-Host "routing check: skills folder not found: $SkillsDir"; exit 2 }

# "-File" passes "a,b" as one string, so split on commas ourselves
$Ignore = @($Ignore | ForEach-Object { $_ -split "," } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$text = [IO.File]::ReadAllText($Rules, [Text.Encoding]::UTF8)
$installed = Get-ChildItem $SkillsDir -Directory |
  Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } |
  ForEach-Object { $_.Name }
$missing = @($installed | Where-Object { ($Ignore -notcontains $_) -and (-not $text.Contains('`' + $_ + '`')) })

if ($missing.Count -eq 0) {
  Write-Host "routing check: OK - all $(@($installed).Count) installed skills are in the table ($($Ignore.Count) ignored)"
  exit 0
}
Write-Host "routing check: $($missing.Count) skill(s) missing from the table in $Rules"
$missing | ForEach-Object { Write-Host "  - $_" }
exit 1
