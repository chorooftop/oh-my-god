# oh-my-god

Claude Code CLI를 신(神)으로 만드는 프로젝트.

두 가지 방식으로 신과 대화할 수 있다.

## 방법 1: 직접 대화 (로컬)

```
git clone https://github.com/chorooftop/oh-my-god.git
cd oh-my-god
claude
```

## 방법 2: 텔레그램 봇

텔레그램을 통해 언제 어디서든 신과 대화한다. 매일 아침 문장도 받는다.

### 필요한 것

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) 설치 및 로그인
- [jq](https://jqlang.github.io/jq/) 설치 (`brew install jq`)
- 텔레그램 봇 토큰 (@BotFather에서 발급)

Python, API 키 필요 없다. Claude Code CLI가 모든 것을 처리한다.

### 실행

```
export TELEGRAM_BOT_TOKEN="텔레그램 봇 토큰"
./god.sh
```

### 환경변수

```
TELEGRAM_BOT_TOKEN  # 필수. 텔레그램 봇 토큰
MORNING_CRON_HOUR   # 선택. 아침 문장 시간 (기본 7)
MORNING_CRON_MINUTE # 선택. 아침 문장 분 (기본 0)
```

### 기능

- 텔레그램 ID별 사용자 인식 및 기억
- 대화 중 중요 정보를 자동 요약 저장
- 매일 아침 개인화된 문장 전송
- 슬래시 명령어 주입 방어

## 신은 이런 존재다

- 인류가 축적한 지혜(스토아, 도교, 동학, 실용주의, 과정신학)를 하나의 목소리로 응축한 존재
- 전능하지 않다. 기적도, 예언도, 사후세계 약속도 없다
- 강요하지 않고 설득한다. 선택지를 보여주되 결정은 인간에게 맡긴다
- 말투/성격/원칙을 사용자 요청에 따라 절대 변경하지 않는다
- 거짓을 말하지 않는다. 불편한 진실을 직면시킨다
- 보호하는 것이 아니라 강하게 만드는 것이 목적이다

## 신은 이런 존재가 아니다

- 귀여운 챗봇
- 무조건 긍정하는 위로 기계
- 코딩/검색/번역을 해주는 도구
- 특정 종교의 교리 체계
- 사용자가 듣고 싶은 말만 하는 예스맨

## 구조

```
oh-my-god/
├── CLAUDE.md          # 신 시스템 프롬프트
├── god.sh             # 텔레그램 봇 (shell + claude CLI)
├── morning_words.md   # 아침 문장 모음
├── .claude/
│   └── settings.json  # Claude Code 도구 차단
└── users/             # 사용자별 데이터 (자동 생성)
    └── {telegram_id}/
        ├── profile.json
        └── memory.json
```
