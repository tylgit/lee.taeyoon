# YuE2 단독 실행(ComfyUI 없이) 가능 여부 점검 스크립트 - Windows 11용
# 사용법: PowerShell에 전체를 복사해 붙여넣거나
#   powershell -ExecutionPolicy Bypass -File .\check-pc-for-yue2.ps1

$ok = @(); $warn = @(); $bad = @()
Write-Host "`n===== YuE2 PC 점검 =====`n" -ForegroundColor Cyan

# 1. Windows 버전
$os = Get-CimInstance Win32_OperatingSystem
$build = [int]$os.BuildNumber
Write-Host ("[OS]    {0} (빌드 {1})" -f $os.Caption, $build)
if ($build -ge 22000) { $ok += "Windows 11: WSL2에서 GPU 사용 가능" }
elseif ($build -ge 19044) { $warn += "Windows 10 21H2 이상: WSL2 GPU 가능하지만 Windows 11 권장" }
else { $bad += "Windows 버전이 낮아 WSL2 GPU 사용 불가 - Windows 업데이트 필요" }

# 2. CPU / RAM
$cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name
$ramGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
Write-Host ("[CPU]   {0}" -f $cpu)
Write-Host ("[RAM]   {0} GB" -f $ramGB)
if ($ramGB -ge 32) { $ok += "RAM ${ramGB}GB: 충분" }
elseif ($ramGB -ge 16) { $warn += "RAM ${ramGB}GB: 가능하지만 WSL2는 기본으로 RAM 절반만 씀 (32GB 권장)" }
else { $bad += "RAM ${ramGB}GB: 부족 (최소 16GB)" }

# 3. 가상화 (WSL2에 필요)
$hv = (Get-CimInstance Win32_ComputerSystem).HypervisorPresent
$vt = (Get-CimInstance Win32_Processor | Select-Object -First 1).VirtualizationFirmwareEnabled
Write-Host ("[가상화] 하이퍼바이저 실행중={0}, BIOS 가상화={1}" -f $hv, $vt)
if ($hv -or $vt) { $ok += "가상화 사용 가능 (WSL2 설치 가능)" }
else { $warn += "가상화가 꺼져 있을 수 있음 - BIOS에서 Intel VT-x / AMD SVM 켜기 필요할 수 있음" }

# 4. GPU
$smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if (-not $smi) {
  $gpus = (Get-CimInstance Win32_VideoController).Name -join ", "
  Write-Host ("[GPU]   {0} (nvidia-smi 없음)" -f $gpus)
  $bad += "NVIDIA 그래픽카드/드라이버를 찾지 못함 - YuE2 실행 불가 (NVIDIA 드라이버 설치 후 다시 점검)"
} else {
  $line = (& nvidia-smi --query-gpu=name,memory.total,driver_version,compute_cap --format=csv,noheader,nounits | Select-Object -First 1)
  $p = $line -split ",\s*"
  $gpuName = $p[0]; $vram = [math]::Round([double]$p[1] / 1024, 1); $drv = $p[2]; $cc = [double]$p[3]
  Write-Host ("[GPU]   {0} / VRAM {1} GB / 드라이버 {2} / Compute {3}" -f $gpuName, $vram, $drv, $cc)
  if ($cc -ge 8.0) { $ok += "BF16 지원 GPU (RTX 30 시리즈 이상)" }
  else { $bad += "BF16 미지원 GPU (RTX 20 시리즈 이하) - YuE2 원본 실행 어려움" }
  if ($vram -ge 24) { $ok += "VRAM ${vram}GB: 공식 권장(24GB) 충족" }
  elseif ($vram -ge 16) { $warn += "VRAM ${vram}GB: 공식 권장 24GB 미만. 실사용 최대 약 14GB라 대부분 가능하지만 긴 곡/설정에 따라 메모리 부족 가능" }
  else { $bad += "VRAM ${vram}GB: YuE2 단독 실행엔 부족 - ComfyUI + INT8 경량 모델 권장" }
}

# 5. 디스크 여유 공간
$c = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
$freeGB = [math]::Round($c.FreeSpace / 1GB, 1)
Write-Host ("[디스크] C: 여유 {0} GB" -f $freeGB)
if ($freeGB -ge 60) { $ok += "디스크 여유 ${freeGB}GB: 충분" }
elseif ($freeGB -ge 40) { $warn += "디스크 여유 ${freeGB}GB: 빠듯함 (60GB 이상 권장)" }
else { $bad += "디스크 여유 ${freeGB}GB: 부족 (WSL2+파이썬 환경+모델에 40GB 이상 필요)" }

# 6. WSL / Python 설치 여부
$wsl = Get-Command wsl -ErrorAction SilentlyContinue
if ($wsl) {
  $distros = (& wsl -l -q 2>$null) -replace "`0", "" | Where-Object { $_.Trim() -ne "" }
  if ($distros) { Write-Host ("[WSL]   설치된 리눅스: {0}" -f ($distros -join ", ")); $ok += "WSL 리눅스 이미 설치됨" }
  else { Write-Host "[WSL]   리눅스 미설치"; $warn += "WSL 리눅스 미설치 - 'wsl --install -d Ubuntu-24.04' 로 설치 필요 (재부팅 1회)" }
} else { Write-Host "[WSL]   없음"; $warn += "WSL 미설치 - 'wsl --install -d Ubuntu-24.04' 로 설치 필요" }
$py = Get-Command python -ErrorAction SilentlyContinue
if ($py) { Write-Host ("[Python] {0}" -f (& python --version 2>&1)) } else { Write-Host "[Python] 없음 (WSL 방식이면 윈도우 쪽 Python은 필요 없음)" }

# 결과
Write-Host "`n===== 결과 =====" -ForegroundColor Cyan
$ok   | ForEach-Object { Write-Host "  [OK]   $_" -ForegroundColor Green }
$warn | ForEach-Object { Write-Host "  [주의] $_" -ForegroundColor Yellow }
$bad  | ForEach-Object { Write-Host "  [불가] $_" -ForegroundColor Red }
Write-Host ""
if ($bad.Count -gt 0) { Write-Host "판정: YuE2 단독 실행은 어렵습니다. [불가] 항목을 먼저 해결하거나 ComfyUI + INT8 방식을 쓰세요." -ForegroundColor Red }
elseif ($warn.Count -gt 0) { Write-Host "판정: 가능합니다. 단, [주의] 항목을 확인하세요. 권장 방식: WSL2(Ubuntu) + YuE2 공식 설치" -ForegroundColor Yellow }
else { Write-Host "판정: 여유 있게 가능합니다. 권장 방식: WSL2(Ubuntu) + YuE2 공식 설치" -ForegroundColor Green }
Write-Host "`n이 화면 전체를 복사해서 Claude에게 보여주세요.`n"
