param(
 [Parameter(Mandatory=$true)][string]$PackagePath,
 [string]$TargetPath="C:\stock-bot"
)
$ErrorActionPreference="Stop"
$Python=Join-Path $TargetPath ".venv\Scripts\python.exe"
$Index="$TargetPath\runtime\codebase_baseline_v6\DUPLICATE_HASH_INDEX.json"
if(-not(Test-Path $Index)){throw "V6 BASELINE HASH INDEX NOT FOUND"}
if(-not(Test-Path $PackagePath)){throw "PACKAGE PATH NOT FOUND: $PackagePath"}

$Tmp=Join-Path $env:TEMP ("v6_preflight_"+[guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $Tmp -Force|Out-Null
try{
 if((Get-Item $PackagePath).PSIsContainer){
   $Scan=$PackagePath
 } else {
   Add-Type -AssemblyName System.IO.Compression.FileSystem
   [System.IO.Compression.ZipFile]::ExtractToDirectory($PackagePath,$Tmp)
   $Scan=$Tmp
 }

 $Existing=Get-Content $Index -Raw|ConvertFrom-Json
 $Exact=@()
 Get-ChildItem $Scan -Recurse -File |
   Where-Object {$_.Extension -in ".py",".ps1",".psm1"} |
   ForEach-Object{
      $Hash=(Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower()
      $prop=$Existing.PSObject.Properties[$Hash]
      if($null-ne $prop){
         $Exact += [pscustomobject]@{
           NewFile=$_.FullName
           ExistingFiles=($prop.Value -join "; ")
           SHA256=$Hash
         }
      }
   }

 Write-Host "=== V6 NEW PACKAGE DUPLICATE PREFLIGHT ==="
 Write-Host "EXACT DUPLICATES FOUND: $($Exact.Count)"
 if($Exact.Count-gt 0){
   $Exact|Format-Table -AutoSize
   Write-Host ""
   Write-Host "PREFLIGHT: BLOCKED - REVIEW EXISTING MODULES FIRST"
   exit 2
 }
 Write-Host "PREFLIGHT: PASS"
}
finally{
 Remove-Item $Tmp -Recurse -Force -ErrorAction SilentlyContinue
}
