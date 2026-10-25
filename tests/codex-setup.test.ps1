# Test for setup.ps1 step 10 (Codex). Runs only that step against throwaway CODEX_HOME folders; your real ~/.codex is only read.
# Usage: powershell -ExecutionPolicy Bypass -File tests\codex-setup.test.ps1
param(
  [string]$Setup = (Join-Path $PSScriptRoot "..\skills\ai-creator-onboarding\scripts\setup.ps1"),
  [string]$Assets = (Join-Path $PSScriptRoot "..\skills\ai-creator-onboarding\assets")
)
$ErrorActionPreference = "Stop"
$src = Get-Content $Setup -Raw
$start = $src.IndexOf("# 10. OpenAI Codex")
$end = $src.IndexOf('Write-Host "`n===== SUMMARY =====')
if ($start -lt 0 -or $end -lt 0) { throw "step 10 not found" }
$block = $src.Substring($start, $end - $start)
$fails = 0
function Check($name, $cond) { if ($cond) { Write-Host "PASS $name" } else { Write-Host "FAIL $name"; $script:fails++ } }

function Run-Block($codexHomeDir, $skillsDirForTest) {
  $script:report = New-Object System.Collections.Generic.List[string]
  function Say($m) { $script:report.Add($m) }
  function Has($c) { ($c -ne "headroom") -and [bool](Get-Command $c -ErrorAction SilentlyContinue) }   # never touch the real config
  $codexHome = $codexHomeDir; $useCodex = $true; $codexSkillsDir = $skillsDirForTest
  $assets = $Assets; $here = Split-Path -Parent $Setup
  $ErrorActionPreference = "Continue"
  Invoke-Expression $block
  return $script:report
}

$tmp = Join-Path $env:TEMP ("codex-block-test-" + [guid]::NewGuid().ToString("N").Substring(0,8))
$skills = Join-Path $tmp "skills"; New-Item -ItemType Directory -Force $skills | Out-Null

# Case 1: fresh home, empty AGENTS.md
$h1 = Join-Path $tmp "fresh"; New-Item -ItemType Directory -Force $h1 | Out-Null
New-Item -ItemType File (Join-Path $h1 "AGENTS.md") | Out-Null
$r1 = Run-Block $h1 $skills
$cfg1 = Get-Content (Join-Path $h1 "config.toml") -Raw
Check "fresh: AGENTS.md copied over empty file" ((Get-Item (Join-Path $h1 "AGENTS.md")).Length -gt 1000)
Check "fresh: fallback key at top" ($cfg1 -match '^(project_doc_max_bytes = 65536\n)?project_doc_fallback_filenames = \["CLAUDE.md"\]' -or $cfg1 -match '^project_doc_max_bytes')
Check "fresh: higgsfield block" ($cfg1 -match '(?m)^\[mcp_servers\.higgsfield\]\nurl = "https://mcp.higgsfield.ai/mcp"')
Check "fresh: meta-ads block" ($cfg1 -match '(?m)^\[mcp_servers\.meta-ads\]')
Check "fresh: playwright block" ($cfg1 -match '(?m)^\[mcp_servers\.playwright\]')
$bdSet = [bool][Environment]::GetEnvironmentVariable("BRIGHTDATA_API_KEY","User")
if ($bdSet) {
  Check "fresh: brightdata uses env var name only" ($cfg1 -match 'bearer_token_env_var = "BRIGHTDATA_API_KEY"')
  $key = [Environment]::GetEnvironmentVariable("BRIGHTDATA_API_KEY","User")
  Check "fresh: key value not written" (-not $cfg1.Contains($key))
}
# Case 2: re-run is a no-op
$before = $cfg1
$r2 = Run-Block $h1 $skills
$after = Get-Content (Join-Path $h1 "config.toml") -Raw
Check "rerun: config unchanged" ($before -eq $after)
Check "rerun: AGENTS.md reported as existing" (($r2 -join "`n") -match "AGENTS.md exists")

# Case 3: copy of the real config keeps everything and stays parseable by codex
$h3 = Join-Path $tmp "real"; New-Item -ItemType Directory -Force $h3 | Out-Null
$real = Join-Path $HOME ".codex\config.toml"
if (Test-Path $real) {
  Copy-Item $real (Join-Path $h3 "config.toml")
  $r3 = Run-Block $h3 $skills
  $c3 = Get-Content (Join-Path $h3 "config.toml") -Raw
  Check "real copy: no duplicate mcp tables" ((([regex]::Matches($c3, '(?m)^\[mcp_servers\.higgsfield\]')).Count) -eq 1)
  $env:CODEX_HOME = $h3
  $ErrorActionPreference = "Continue"
  $list = cmd /c "codex mcp list 2>nul" | Out-String
  Remove-Item Env:CODEX_HOME
  Check "real copy: codex parses config" ($list -match "higgsfield" -and $list -match "brightdata|meta-ads")
}
# Case 4: servers already present in other TOML shapes are not added twice
$h4 = Join-Path $tmp "shapes"; New-Item -ItemType Directory -Force $h4 | Out-Null
$shapes = "model = `"x`"`n[mcp_servers.'meta-ads']`nurl = `"https://mcp.facebook.com/ads`"`n[ mcp_servers.`"higgsfield`" ]`nurl = `"https://mcp.higgsfield.ai/mcp`"`n[mcp_servers]`nplaywright = { command = `"npx`", args = [`"-y`", `"@playwright/mcp@latest`"] }`n"
[IO.File]::WriteAllText((Join-Path $h4 "config.toml"), $shapes)
$null = Run-Block $h4 $skills
$c4 = Get-Content (Join-Path $h4 "config.toml") -Raw
Check "shapes: quoted meta-ads not duplicated" (([regex]::Matches($c4, "meta-ads")).Count -eq 1)
Check "shapes: spaced higgsfield not duplicated" (([regex]::Matches($c4, "higgsfield")).Count -eq 2)
Check "shapes: inline playwright not duplicated" (([regex]::Matches($c4, "(?m)^\[mcp_servers\.playwright\]")).Count -eq 0)
Check "shapes: backup is the first-run original" ((Get-Content (Join-Path $h4 "config.toml.onboarding.bak") -Raw) -eq $shapes)
Remove-Item -Recurse -Force $tmp
Write-Host "failures: $fails"
exit $fails
