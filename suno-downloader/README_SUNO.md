# Suno 노래 일괄 다운로드 (mp3 / srt / lrc / word.json)

Suno는 공식 공개 API를 제공하지 않습니다. 이 스크립트는 suno.com 웹사이트가
내부적으로 쓰는 것과 같은 방식(로그인 브라우저 쿠키)으로 **본인 계정**의 곡
목록을 가져와서, 곡마다 아래 파일을 저장합니다.

- `song.mp3` — 오디오
- `lyrics.srt` — 자막 형식 가사 (타임스탬프 포함)
- `lyrics.lrc` — 노래방/플레이어용 가사 (줄 단위 타임스탬프)
- `words.json` — 단어 단위 타이밍 원본 데이터 (word.json)
- `metadata.json` — 제목, 프롬프트, 태그 등 곡 정보

600곡처럼 많은 곡도 중단 후 재실행하면 이미 받은 곡은 건너뛰고 이어받습니다
(`manifest.json`에 진행 상황 기록).

> ⚠️ 본인 소유 계정/본인이 만든 곡에 대해서만 사용하세요. 쿠키는 로그인
> 세션 정보이므로 절대 남과 공유하지 마세요.

## 1. 준비

```bash
cd suno-downloader
pip install -r requirements.txt
```

## 2. 쿠키(로그인 정보) 가져오기

1. 크롬/엣지에서 **로그인한 상태로** `https://suno.com/create` 접속
2. `F12` (개발자 도구) → **Network(네트워크)** 탭 열기
3. 페이지를 새로고침(F5)
4. 요청 목록에서 `client?__clerk_api_version` 또는 `clerk.suno.com`이 포함된
   요청을 클릭
5. 오른쪽 **Headers → Request Headers**에서 `Cookie:` 옆의 값 전체를 복사
   (아주 긴 문자열입니다. 전체를 복사해야 합니다.)

## 3. 인증 테스트

쿠키가 제대로 동작하는지 먼저 확인하세요.

```bash
export SUNO_COOKIE="여기에_복사한_쿠키_전체_붙여넣기"
python suno_batch_download.py --test-auth
```

`Auth OK. Billing info: ...` 가 나오면 성공입니다.
`Auth FAILED`가 나오면 쿠키를 다시 복사하거나(로그아웃/재로그인 후 다시 시도),
`--clerk-domain auth.suno.com` 옵션을 추가해 보세요.

## 4. 목록만 먼저 확인 (선택)

```bash
python suno_batch_download.py --out-dir ./my_songs --list-only
```

`my_songs/clips_raw.json`에 몇 곡이 잡히는지 확인해서 600곡이 맞는지
검증할 수 있습니다.

## 5. 실제 다운로드 실행

```bash
python suno_batch_download.py --out-dir ./my_songs
```

- 처음엔 몇 곡만 테스트해보고 싶다면 `--limit 5` 추가
- 동시 다운로드 개수는 `--workers 3` (기본값 3, 서버 부담을 줄이려면 낮게 유지)
- 이미 받은 파일을 다시 받으려면 `--overwrite`

진행 중 콘솔에 곡마다 `mp3=ok lyrics=ok` 형태로 결과가 출력됩니다.
중간에 인터넷이 끊기거나 멈추면, 같은 명령을 다시 실행하면 이어서
받아지지 않은 곡만 처리합니다.

## 6. 결과 확인

```
my_songs/
  clips_raw.json         # 전체 곡 목록 원본
  manifest.json          # 곡별 다운로드 결과 기록
  노래제목__abcd1234/
    song.mp3
    lyrics.srt
    lyrics.lrc
    words.json
    metadata.json
  ...
```

## 참고 / 문제 해결

- 인스트루멘탈(가사 없는) 곡은 `lyrics=unavailable`로 표시되고 mp3만
  저장됩니다. 정상입니다.
- `status`가 `complete`가 아닌(아직 생성 중이거나 실패한) 곡은 mp3를
  건너뜁니다.
- Suno가 내부 API 구조를 바꾸면 스크립트가 실패할 수 있습니다. 이 스크립트는
  비공식 API를 리버스 엔지니어링한 것이라 Suno 쪽 변경에 취약합니다. 에러
  메시지를 알려주시면 스크립트를 그에 맞게 고칠 수 있습니다.
- 요청 간 기본 지연은 0.8초입니다 (`SUNO_REQUEST_DELAY` 환경변수로 조절
  가능). 너무 빠르게 요청하면 일시적으로 차단될 수 있으니 늘리는 것을
  권장합니다.
