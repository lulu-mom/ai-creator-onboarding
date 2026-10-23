# ai-creator-onboarding: install the whole toolkit. Safe to re-run (skips what exists).
# Usage: powershell -ExecutionPolicy Bypass -File setup.ps1 [-ProjectsDir C:\work]
param([string]$ProjectsDir = "$HOME\projects")

$ErrorActionPreference = "Continue"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$assets = Join-Path (Split-Path -Parent $here) "assets"
$skillsDir = "$HOME\.claude\skills"
$report = New-Object System.Collections.Generic.List[string]
function Say($m) { Write-Host "== $m"; $report.Add($m) }
function Has($c) { [bool](Get-Command $c -ErrorAction SilentlyContinue) }
function RefreshPath { $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User") }

# 1. Base programs
$winget = @{ node = "OpenJS.NodeJS.LTS"; git = "Git.Git"; python = "Python.Python.3.13"; ffmpeg = "Gyan.FFmpeg"; gh = "GitHub.cli" }
foreach ($cmd in $winget.Keys) {
  if (Has $cmd) { Say "$cmd ok" } else {
    winget install --id $winget[$cmd] -e --accept-source-agreements --accept-package-agreements --silent | Out-Null
    RefreshPath; Say "$cmd installed"
  }
}
# last30days calls python3; Windows only has the Store stub
if (-not ((Get-Command python3 -ErrorAction SilentlyContinue).Source -like "*Python*")) {
  $py = (Get-Command python).Source
  Copy-Item $py (Join-Path (Split-Path $py) "python3.exe") -ErrorAction SilentlyContinue
  Say "python3 alias created"
}

# 2. Python packages
python -m pip install -q -U faster-whisper silero-vad mediapipe yt-dlp "headroom-ai[all]" 2>$null
Say "python packages: faster-whisper, silero-vad, mediapipe, yt-dlp, headroom-ai"

# 3. Global npm tools
if (-not (Has hypit)) { npm install -g @hypit/hypit | Out-Null; Say "hypit CLI installed" } else { Say "hypit ok" }
if (-not (Has agent-browser)) { npm install -g agent-browser | Out-Null; agent-browser install | Out-Null; Say "agent-browser installed" } else { Say "agent-browser ok" }

# 4. Skills (global, Claude Code, copied)
$skillRepos = @(
  @("heygen-com/hyperframes", "*", $true),
  @("remotion-dev/skills", "*", $false),
  @("greensock/gsap-skills", "*", $false),
  @("Jakeschincariol/youtube-agent-skill", "*", $true),
  @("mattpocock/skills", "grill-me grilling research", $false),
  @("rebelytics/one-skill-to-rule-them-all", "*", $true),
  @("brightdata/skills", "*", $true),
  @("upload-post/upload-post-skills", "*", $true),
  @("vercel-labs/skills", "find-skills", $false),
  @("mvanhorn/last30days-skill", "*", $false),
  @("anthropics/knowledge-work-plugins", "search-strategy", $true),
  @("jimliu/baoyu-skills", "baoyu-youtube-transcript baoyu-url-to-markdown", $false),
  @("hypit-ai/hypit", "*", $false),
  @("vercel-labs/agent-browser", "*", $false),
  @("citrolabs/ego-lite", "ego-browser", $true)
)
foreach ($r in $skillRepos) {
  $npxArgs = @("-y", "skills", "add", $r[0], "-g", "-a", "claude-code", "-y", "--copy", "--skill") + ($r[1] -split " ")
  if ($r[2]) { $npxArgs += "--full-depth" }
  npx @npxArgs 2>&1 | Out-Null
  Say "skills: $($r[0]) [$($r[1])]"
}
# Workflow skills from this repo
npx -y skills add lulu-mom/ai-creator-onboarding -g -a claude-code -y --copy --skill link-to-build oss-scout ai-creator-onboarding 2>&1 | Out-Null
Say "skills: link-to-build, oss-scout, ai-creator-onboarding"

# 5. Plugin: ECC (Everything Claude Code)
$plugins = claude plugin list 2>&1 | Out-String
if ($plugins -notmatch "ecc@ecc") {
  claude plugin marketplace add https://github.com/affaan-m/ECC | Out-Null
  claude plugin install ecc@ecc | Out-Null
  Say "plugin ecc@ecc installed"
} else { Say "plugin ecc ok" }

# 6. MCP servers (no keys needed here; OAuth via /mcp later)
$mcp = claude mcp list 2>&1 | Out-String
if ($mcp -notmatch "higgsfield") { claude mcp add --transport http --scope user higgsfield https://mcp.higgsfield.ai/mcp | Out-Null; Say "mcp higgsfield added" }
if ($mcp -notmatch "meta-ads")   { claude mcp add --transport http --scope user meta-ads https://mcp.facebook.com/ads | Out-Null; Say "mcp meta-ads added" }
if ($mcp -notmatch "playwright") { claude mcp add --scope user playwright -- npx -y "@playwright/mcp@latest" | Out-Null; Say "mcp playwright added" }
if ($mcp -notmatch "headroom")   { headroom mcp install | Out-Null; Say "mcp headroom added" }
$bd = [Environment]::GetEnvironmentVariable("BRIGHTDATA_API_KEY","User")
if ($bd -and $mcp -notmatch "brightdata") { claude mcp add --scope user --transport sse brightdata "https://mcp.brightdata.com/sse?token=$bd" | Out-Null; Say "mcp brightdata added" }

# 7. OpenMontage
$om = Join-Path $ProjectsDir "OpenMontage"
if (-not (Test-Path $om)) {
  New-Item -ItemType Directory -Force $ProjectsDir | Out-Null
  git clone https://github.com/calesthio/OpenMontage.git $om | Out-Null
  Push-Location $om
  python -m venv .venv
  .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt 2>$null
  .\.venv\Scripts\python.exe -m pip install -q piper-tts 2>$null
  Push-Location remotion-composer; npm install 2>$null | Out-Null; Pop-Location
  if (-not (Test-Path .env)) { Copy-Item .env.example .env }
  Pop-Location
  Say "OpenMontage installed at $om"
} else { Say "OpenMontage ok" }

# 7-1. ECC common rules (plugin installs do not ship rules) + issue-worker agent
$eccRoot = Get-ChildItem "$HOME\.claude\plugins\cache\ecc\ecc" -Directory -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -Last 1
if ($eccRoot -and (Test-Path "$($eccRoot.FullName)\rules\common")) {
  New-Item -ItemType Directory -Force "$HOME\.claude\rules\ecc" | Out-Null
  Copy-Item -Recurse -Force "$($eccRoot.FullName)\rules\common" "$HOME\.claude\rules\ecc\"
  Say "ECC common rules -> ~/.claude/rules/ecc/common"
} else { Say "ECC rules not found (install plugin first, then re-run)" }
New-Item -ItemType Directory -Force "$HOME\.claude\agents" | Out-Null
Copy-Item -Force "$assets\agents\issue-worker.md" "$HOME\.claude\agents\issue-worker.md"
Say "agent issue-worker installed"

# 8. Global rules
$g = "$HOME\.claude\CLAUDE.md"
if (-not (Test-Path $g)) { Copy-Item "$assets\global-CLAUDE.md" $g; Say "global CLAUDE.md created" }
else { Say "global CLAUDE.md exists - merge assets\global-CLAUDE.md manually if sections are missing" }

Write-Host "`n===== SUMMARY ====="
$report | ForEach-Object { Write-Host " - $_" }
