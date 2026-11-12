# Pomodoro (Cross-Platform Desktop App)

`pomodorotimer.online`의 직관적인 세션 전환/프리셋 구성과 `Pomotroid`의 다크 미니멀 원형 다이얼 감성을 결합한 크로스 플랫폼(Linux / macOS / Windows, PyQt5) 데스크톱 뽀모도로 타이머입니다. 할 일(To-Do) 기능을 배제하고 타이머와 집중 리듬에만 집중할 수 있도록 설계되었습니다.

## 주요 기능

- **네이티브 Always on Top (항상 위 고정)**:
  - 상단 타이틀바의 **핀(Pin) 아이콘** 또는 `ON TOP` 배지를 클릭하거나 `Ctrl + T` 단축키로 언제든 창을 최상단에 고정/해제할 수 있습니다.
  - 일반 모드와 화면 공간을 적게 차지하는 **미니 모드(`Ctrl + M`)**를 모두 지원합니다.
- **세션 빠른 전환 (`pomodorotimer.online` 스타일)**:
  - 상단 탭(`Focus` / `Short Break` / `Long Break`)을 클릭해 원하는 세션으로 즉시 전환할 수 있습니다.
- **인기 프리셋 기본 제공 + 프리셋별 시간·라운드 맞춤 저장**:
  - **기본 제공 프리셋**:
    - **Classic**: `25 / 5 / 15분` (6 라운드) — 표준 뽀모도로
    - **Deep Work**: `50 / 10 / 20분` (6 라운드) — 깊은 몰입 작업
    - **Study 45**: `45 / 15 / 30분` (6 라운드) — 학습 및 강의 리듬
    - **Quick Sprint**: `15 / 3 / 10분` (8 라운드) — 빠른 시작/단기 집중
    - **52 / 17 Rule**: `52 / 17 / 25분` (6 라운드) — 생산성 집중 비율
    - **Custom**: `90 / 30 / 30분` (4 라운드) — 장시간 몰입 등 사용자 정의
  - **프리셋별 상세 설정 (`Preset Duration & Rounds`)**:
    - 설정 화면(`Ctrl + ,`)에서 각 프리셋의 Focus, Short Break, Long Break 시간(분 단위)과 라운드 횟수를 자유롭게 수정할 수 있으며, 수정한 값은 각 프리셋별로 영구 저장됩니다 (`Reset to Default`로 초기값 복원 가능).
- **휴식 시간(Break) 맞춤 스트레칭 & 간단 운동 플로팅 가이드 창**:
  - **Short Break**와 **Long Break** 세션 동안 사무실·책상·의자를 활용해 바로 따라 할 수 있는 스트레칭/운동을 **애니메이션 벡터 일러스트가 포함된 별도 팝업 윈도우**와 데스크톱 알림으로 추천해 줍니다.
  - **Short Break**: 의자에 앉아서 하는 가벼운 스트레칭 (목·승모근 늘리기, 손목·전완근 스트레칭, 앉아서 상체 비틀기, 20-20-20 눈 피로 풀기, 거북목 턱 당기기, 날개뼈 모으기 등)
  - **Long Break**: 자리에서 일어나 몸을 깨우는 동작 포함 (책상 짚고 등·가슴 펴기, 의자 터치 스쿼트, 둔근 스트레칭, 종아리 까치발 들기, 일어서서 허리 젖히기, 책상 푸시업 등)
  - 일반 모드와 **미니 모드(`Ctrl + M`)** 모두에서 타이머 창 옆에 자동으로 뜨며, 우측 상단의 `다른 동작 ↻` 버튼으로 언제든 다른 동작을 볼 수 있습니다.
- **알림음 & 데스크톱 알림 & 자동 시작**:
  - 외부 오디오 파일 없이 자체 합성된 부드러운 화음 차임벨 사운드(집중 종료 / 휴식 종료 구분)를 재생하며, 음소거(`M`) 토글을 지원합니다 (Linux `paplay`/`aplay`, macOS `afplay`, Windows `winsound` 자동 지원).
  - 세션 종료 시 데스크톱 시스템 알림(Linux `notify-send`, macOS Notification Center `osascript`)을 표시합니다.
  - 집중 종료 후 휴식 자동 시작(`Auto-start Breaks`), 휴식 종료 후 집중 자동 시작(`Auto-start Focus`) 옵션을 제공합니다.
- **설정 자동 저장**:
  - 모든 프리셋, 분 단위 커스텀 시간, 항상 위 상태, 알림 설정은 `~/.config/pomodoro-app/settings.json`에 자동 저장됩니다.

## 설치 및 실행 방법 (`uv` 권장 — Linux / macOS / Windows 공통)

시스템 Python이나 전역 패키지를 건드리지 않고 [uv](https://docs.astral.sh/uv/)를 사용해 어떤 OS에서든 독립된 가상환경으로 바로 설치·실행할 수 있습니다.

### 1. 설치 없이 바로 실행 (`uvx`)
```bash
uvx --from git+https://github.com/jrkwon/pomodoro pomodoro
```

### 2. 전역 CLI/앱 도구로 설치 (`uv tool install`)
```bash
uv tool install git+https://github.com/jrkwon/pomodoro

# 이후 어디서든 아래 명령으로 실행:
pomodoro
```

### 3. 저장소 클론 후 실행 (`uv run`)
```bash
git clone https://github.com/jrkwon/pomodoro.git
cd pomodoro
uv run pomodoro
# 또는 단일 스크립트 실행 (PEP 723 인라인 메타데이터 지원)
uv run pomodoro.py
```

### 4. 시스템 Python으로 직접 실행
```bash
python3 pomodoro.py
```

### 데스크톱 앱 검색 & 시작 프로그램(Startup Application) 등록
앱을 처음 실행하거나 아래 명령을 실행하면 **데스크톱 앱 런처(`~/.local/share/applications/pomotroid-timer.desktop`, macOS `~/Applications/Pomodoro.app`)** 및 **로그인 시 자동 시작 프로그램(`~/.config/autostart/pomotroid-timer.desktop`, macOS `LaunchAgents`)**에 자동으로 등록됩니다. 설정(`Ctrl + ,`)의 `Start automatically on login (Startup App)` 체크박스에서 언제든 자동 시작 여부를 켜거나 끌 수 있습니다.

```bash
# 창을 띄우지 않고 데스크톱 앱 및 시작 프로그램으로 즉시 등록:
pomodoro --install

# 데스크톱 앱 및 시작 프로그램 등록 해제:
pomodoro --uninstall
```

## 단축키 안내

| 단축키 | 동작 |
| :--- | :--- |
| `Space` | 타이머 시작 / 일시정지 |
| `R` | 현재 세션 시간 초기화 (Reset) |
| `S` | 다음 세션으로 건너뛰기 (Skip) |
| `M` | 알림음 음소거 토글 (Mute) |
| `Ctrl + T` | Always on Top (항상 위) 켜기 / 끄기 |
| `Ctrl + M` | 컴팩트 미니 모드(Mini Mode) 전환 |
| `Ctrl + ,` | 프리셋 및 분 단위 설정 열기 / 닫기 |
| `Ctrl + Q` | 앱 종료 |
