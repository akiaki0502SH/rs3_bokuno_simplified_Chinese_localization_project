param([string]$Rom,[string]$Case,[string]$Kind='inspect',[int]$Id=15,[switch]$Special,[switch]$Destroyed,[switch]$Extended)
$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if(Get-Process Mesen -ErrorAction SilentlyContinue){throw 'An existing Mesen process is running'}
$absoluteProject=[System.IO.Path]::GetFullPath($PWD.Path)
if($absoluteProject -ne 'G:\CodexProjects\Bokuno中文化工程\bokuno_cn'){throw 'Wrong project directory'}
$folder=Join-Path $absoluteProject 'qa/postbattle_feedback_v289_20261013_01'
if(-not(Test-Path -LiteralPath $folder)){New-Item -ItemType Directory -Path $folder|Out-Null}
$prefix=Join-Path $folder $Case
if(Test-Path -LiteralPath ($prefix+'_trace.txt')){throw 'Choose a fresh case name'}
$env:CN_REWARD_SEED=(Resolve-Path 'qa/bmsg_controlled_native26405_20261008_02_native_ui_before_inject.mss').Path
$env:CN_REWARD_PREFIX=$prefix
$env:CN_REWARD_KIND=$Kind
$env:CN_REWARD_ID=$Id.ToString()
$env:CN_REWARD_SPECIAL=if($Special){'1'}else{'0'}
$env:CN_REWARD_DESTROYED=if($Destroyed){'1'}else{'0'}
$env:CN_REWARD_EXTENDED=if($Extended){'1'}else{'0'}
$exe=(Resolve-Path 'qa/mesen_isolated_runner/Mesen.exe').Path
$absoluteRom=(Resolve-Path $Rom).Path
$lua=(Resolve-Path 'tools/mesen_v289_postbattle_probe_v1.lua').Path
$proc=Start-Process -FilePath $exe -ArgumentList @('--testrunner',('"'+$absoluteRom+'"'),('"'+$lua+'"'),'--timeout=60000') -WindowStyle Hidden -PassThru
$proc.WaitForExit()
[pscustomobject]@{case=$Case;exit=$proc.ExitCode;kind=$Kind;id=$Id;ROM=$Rom;ROM_SHA256=(Get-FileHash -LiteralPath $absoluteRom).Hash;controlled_display=$true;private_state_unchanged=$true}|ConvertTo-Json|Set-Content -LiteralPath ($prefix+'_execution.json') -Encoding UTF8
Get-Content -LiteralPath ($prefix+'_trace.txt') -Tail 5
if($proc.ExitCode -ne 0){throw 'Native display probe failed'}
