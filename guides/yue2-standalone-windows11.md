# 🎵 ComfyUI 없이 YuE2만 쓰기 — Windows 11 초보자 가이드

## 결론 먼저

| 방식 | 난이도 | 추천 |
|---|---|---|
| **A. WSL2(윈도우 속 리눅스) + YuE2 공식 설치** | ★★☆ | ✅ **추천** — 공식 설치법(리눅스 기준)을 그대로 따를 수 있어 오류가 적음 |
| B. 윈도우에 YuE2 공식 코드를 바로 설치 | ★★★ | ❌ 비추천 — 공식 설치법이 리눅스 기준이라 윈도우에서는 오류가 남 (수정 버전 미반영) |
| C. ComfyUI 사용 (기존 가이드) | ★☆☆ | 가장 쉬움. VRAM 16GB 미만이면 이쪽 (INT8 경량 모델) |

YuE2 공식 요구사항: **Linux, Python 3.12, BF16을 지원하는 NVIDIA GPU, VRAM 24GB 권장**
→ Windows 11에는 **WSL2**가 기본으로 들어 있고 NVIDIA GPU도 그대로 쓸 수 있어서, "리눅스 조건"을 해결할 수 있습니다.

---

## 1단계. 내 PC 점검하기 (3분)

1. 시작 버튼 → `PowerShell` 검색 → 실행
2. 아래 둘 중 하나로 점검 스크립트 실행
   - **방법 ①** `check-pc-for-yue2.ps1` 파일 내용을 전체 복사 → PowerShell에 붙여넣기 → `Enter`
   - **방법 ②** 파일을 `다운로드` 폴더에 저장한 뒤:
     ```powershell
     cd $HOME\Downloads
     powershell -ExecutionPolicy Bypass -File .\check-pc-for-yue2.ps1
     ```
3. 마지막 **판정** 줄 확인

| 판정 | 다음 할 일 |
|---|---|
| 🟢 여유 있게 가능 / 🟡 가능(주의) | 2단계로 |
| 🔴 어려움 | `[불가]` 항목 해결, 또는 ComfyUI + INT8 가이드로 |

### 점검 기준표

| 항목 | 최소 | 권장 | 이유 |
|---|---|---|---|
| Windows | 11 (빌드 22000↑) | 최신 업데이트 | WSL2에서 GPU 사용 |
| GPU | NVIDIA RTX 30 시리즈↑ | RTX 40/50 시리즈 | BF16 지원 필요 |
| VRAM | 16GB | 24GB | 실사용 최대 약 14GB (개발팀 측정) |
| RAM | 16GB | 32GB | WSL2는 기본으로 RAM의 절반만 사용 |
| C: 여유 공간 | 40GB | 60GB↑ | 리눅스 + 파이썬 환경 + 모델 |
| 가상화 | 켜짐 | — | WSL2 필수 (꺼져 있으면 BIOS에서 켜기) |

> 💡 결과를 모르겠으면 **화면 전체를 복사해서 Claude에게 붙여넣으세요.**

---

## 2단계. WSL2 + Ubuntu 설치 (15분, 재부팅 1회)

1. PowerShell을 **관리자 권한으로 실행**합니다. (시작 → PowerShell 우클릭 → 관리자 권한으로 실행)
2. 다음 명령을 입력합니다.
   ```powershell
   wsl --install -d Ubuntu-24.04
   ```
3. **재부팅**합니다.
4. 재부팅하면 Ubuntu 창이 뜹니다. 사용자 이름과 비밀번호를 만드세요. 비밀번호는 입력해도 화면에 안 보이는 게 정상입니다.
5. Ubuntu 창에서 GPU가 보이는지 확인합니다.
   ```bash
   nvidia-smi
   ```
   → 그래픽카드 이름이 나오면 성공입니다. **리눅스 안에 NVIDIA 드라이버를 따로 설치하지 마세요.** 윈도우 드라이버를 그대로 씁니다.

✅ **체크포인트**: Ubuntu 창에서 `nvidia-smi`를 입력하면 내 GPU가 보인다.

---

## 3단계. Claude Code를 WSL 안에 설치

Ubuntu 창에서:
```bash
curl -fsSL https://claude.ai/install.sh | bash
```
설치가 끝나면 Ubuntu 창을 닫았다가 다시 열고 `claude`를 입력한 뒤 로그인합니다.
(설치 방법은 바뀔 수 있습니다. 안 되면 `https://code.claude.com/docs`를 확인하세요.)

---

## 4단계. Claude에게 YuE2 설치 맡기기

Ubuntu 창의 `claude`에 아래 지시서를 붙여넣으세요.

### 📜 지시서 — YuE2 단독 설치 (WSL2)

```text
나는 초보자야. Windows 11의 WSL2 Ubuntu에서 ComfyUI 없이 YuE2 공식 코드만으로
노래를 만들고 싶어. 아래 순서대로 진행하고, 단계마다 쉬운 한국어로 알려줘.
명령을 실행하기 전에는 무슨 명령인지 한 줄로 설명해줘.

[내 PC 점검 결과]
(여기에 check-pc-for-yue2.ps1 결과 화면을 붙여넣기)

1. 환경 확인: nvidia-smi, 디스크 여유 공간, RAM(free -h)을 확인해줘.
   WSL에 할당된 RAM이 부족하면 %UserProfile%\.wslconfig 설정 방법을 알려줘.
2. m-a-p(Multimodal Art Projection)의 YuE2 공식 GitHub 저장소와
   Hugging Face 모델 페이지(m-a-p/YuE2-3B)를 찾아 README의 설치 방법을 따라줘.
   - 작업 폴더는 WSL 안의 ~/yue2 로 해줘. (/mnt/c 아래는 느리니까 쓰지 마)
   - 파이썬은 README가 요구하는 버전(3.12)으로 가상환경을 따로 만들어줘.
   - PyTorch는 내 GPU/드라이버에 맞는 CUDA 버전으로 설치해줘.
3. 모델 파일을 받은 뒤, 모든 파일 크기를 Hugging Face 원본과 바이트 단위로 비교해서 검증해줘.
4. README의 예제 명령으로 짧은 테스트 곡을 하나 만들어줘.
   - 장르: "Korean, ballad, female vocal, piano, emotional, slow tempo"
   - 가사: [verse]/[chorus] 구간 표시가 있는 짧은 한국어 가사 (새로 작성)
   - 메모리 부족이 나면 README의 저메모리 옵션을 찾아 적용해줘.
5. 결과 파일을 윈도우 탐색기에서 열 수 있게 C:\Users\<내이름>\Music\YuE2 로 복사해줘.
6. 앞으로 쓰기 쉽게 "가사 파일 + 장르 문장 → 노래 N곡 생성" 스크립트(make_song.sh)를
   만들어주고, 곡마다 악보(ABC) 파일도 같이 저장되게 해줘.
7. 라이선스(개인 상업적 이용 가능 여부)를 모델 페이지에서 확인해서 알려줘.
```

✅ **체크포인트**: 윈도우의 `음악\YuE2` 폴더에서 테스트 곡이 재생된다. 🎉

---

## 5단계. 이후 사용법

Ubuntu 창을 열고 `claude`를 실행한 뒤 이렇게 말하면 됩니다.

- 곡 만들기: **"'금요일 밤 퇴근길 드라이브' 주제로 시티팝 가사 쓰고, 여자 보컬 2곡, 남자 보컬 2곡 만들어줘"**
- 편곡하기: **"3번 곡 악보에서 코드는 지우고 멜로디만 남겨서 트로트 버전으로 다시 만들어줘"**

---

## 🆘 자주 막히는 곳

| 증상 | 해결 |
|---|---|
| `wsl --install`에서 가상화 오류 | BIOS에서 Intel VT-x / AMD SVM 켜기 (Claude에게 "내 메인보드 BIOS에서 가상화 켜는 법" 질문) |
| Ubuntu에서 `nvidia-smi` 안 됨 | 윈도우 쪽 NVIDIA 드라이버를 최신으로 업데이트한 뒤 PowerShell에서 `wsl --shutdown` 실행하고 다시 켜기 |
| `CUDA out of memory` | 가사를 짧게 줄이기, 저메모리 옵션 쓰기, 안 되면 ComfyUI + INT8 방식 |
| 설치 중 오류가 계속 남 | 오류 전체를 Claude에게 붙여넣기. 3번 이상 실패하면 ComfyUI 방식이 더 빠름 |
| C: 공간 부족 | Claude에게 "WSL 배포판을 D: 드라이브로 옮겨줘" |
