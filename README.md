# EMail_Auto_Fowarder

네이버 메일함을 주기적으로 확인하고, 지정한 발신자 패턴과 일치하는 메일만 목표 주소로 자동 포워딩하는 Python 프로그램입니다.

## 진행 구조

1. 프로그램 시작
   - `main.py`에서 `MailWatcher`를 생성하고 `run()`을 실행합니다.
   - `.env` 또는 실행 환경의 환경 변수를 읽어 계정, 대상 주소, 발신자 조건, Polling 주기를 설정합니다.

2. 상태 파일 로드
   - `STATE_FILE`에서 마지막으로 처리한 UID인 `last_uid`를 읽습니다.
   - 상태 파일이 없으면 완전 최초 실행으로 판단합니다.
   - 완전 최초 실행에서는 현재 메일함의 가장 최근 UID를 `last_uid`로 저장하고, 기존 메일은 포워딩하지 않습니다.
   - 이전 형식의 상태 파일이 있어도 가능한 범위에서 `last_uid`로 변환합니다.

3. 발신자 검색어 준비
   - `TARGET_SENDERS` 값을 쉼표 기준으로 나눕니다.
   - 앞뒤 공백과 꺾쇠괄호를 제거하고 소문자로 정규화합니다.
   - 와일드카드 패턴은 서버의 `FROM` 검색에 사용할 수 있는 일부 문자열로 변환합니다.
   - 실제 와일드카드 일치 여부는 서버 검색 후 헤더 검사 단계에서 다시 확인합니다.

4. IMAP 연결
   - `IMAP_HOST`에 SSL로 연결합니다.
   - `NAVER_ID`와 `NAVER_APP_PASSWORD`로 로그인합니다.
   - 연결이 끊기거나 오류가 나면 `RECONNECT_DELAY` 초 후 다시 연결합니다.

5. Polling 반복
   - `POLL_INTERVAL` 초마다 Polling을 수행합니다.
   - 기본 확인 주기는 30초입니다.
   - 각 Polling마다 현재 메일함, 시간, 저장된 `last_uid`를 로그로 출력합니다.

6. 메일함 선택
   - `IMAP_MAILBOX`를 선택합니다.
   - 서버 응답의 `UIDNEXT` 값을 확인합니다.
   - `UIDNEXT - 1`이 현재 메일함에서 확인 가능한 마지막 UID입니다.
   - 새 UID가 없으면 이번 Polling을 종료합니다.

7. 서버에서 후보 메일 검색
   - 검색 범위는 `last_uid + 1:*`입니다.
   - 발신자 검색어가 있으면 다음 형태로 서버 검색을 수행합니다.

```text
UID SEARCH UID <last_uid+1>:* FROM "<검색어>"
```

   - 발신자 검색어가 여러 개면 각각 검색한 뒤 UID를 합칩니다.
   - 이 단계는 후보를 줄이기 위한 1차 필터입니다.

8. 헤더만 먼저 가져오기
   - 후보 UID들에 대해 본문을 바로 가져오지 않습니다.
   - 먼저 다음 방식으로 헤더만 조회합니다.

```text
FETCH <UID들> BODY.PEEK[HEADER]
```

   - `BODY.PEEK[HEADER]`를 사용해 메일 읽음 상태 변경을 피합니다.

9. 발신자 최종 확인
   - 헤더의 `From` 값을 파싱해 실제 이메일 주소만 추출합니다.
   - `TARGET_SENDERS`의 와일드카드 패턴과 비교합니다.
   - 조건과 맞지 않으면 해당 UID는 스킵합니다.

10. 조건이 맞는 메일 본문 조회
    - 발신자 조건을 통과한 메일만 본문을 가져옵니다.

```text
FETCH <UID> BODY[]
```

    - 본문 조회 후 원본 메일 객체를 생성합니다.

11. 포워딩
    - `forwarder.py`에서 새 메일을 생성합니다.
    - 제목 앞에 `[FWD]`를 붙입니다.
    - 원본 발신자, 원본 날짜, 원본 제목, 본문을 포함합니다.
    - `SMTP_HOST`, `SMTP_PORT`로 SMTP SSL 연결 후 `FORWARD_TO`로 전송합니다.

12. UID 저장
    - 정상 처리 또는 스킵이 끝난 UID를 기준으로 `last_uid`를 갱신합니다.
    - 후보가 없더라도 이번 검색 범위의 마지막 UID까지 확인한 것으로 보고 저장합니다.
    - 포워딩 중 오류가 나면 실패한 UID 직전까지만 저장해 다음 Polling에서 다시 시도합니다.

## Docker 상태 저장

- 배포 워크플로는 Docker named volume인 `email-auto-forwarder-data`를 `/app/data`에 마운트합니다.
- 컨테이너는 `STATE_FILE=data/forwarded_uids.json`에 상태를 저장합니다.
- `docker-entrypoint.sh`는 상태 파일이 들어갈 디렉터리를 컨테이너 시작 시 생성합니다.

## 환경 변수

- `NAVER_ID`: 네이버 메일 계정
- `NAVER_APP_PASSWORD`: 네이버 앱 비밀번호
- `FORWARD_TO`: 포워딩 받을 이메일 주소
- `TARGET_SENDERS`: 허용할 발신자 패턴, 쉼표로 여러 개 지정 가능
- `IMAP_HOST`: IMAP 서버, 기본값 `imap.naver.com`
- `IMAP_MAILBOX`: 확인할 메일함, 기본값 `INBOX`
- `SMTP_HOST`: SMTP 서버, 기본값 `smtp.naver.com`
- `SMTP_PORT`: SMTP SSL 포트, 기본값 `465`
- `STATE_FILE`: 마지막 UID 저장 파일, 기본값 `forwarded_uids.json`
- `POLL_INTERVAL`: 확인 주기, 기본값 `30`
- `RECONNECT_DELAY`: 연결 오류 후 재시도 대기 시간, 기본값 `5`

## 발신자 패턴 예시

`TARGET_SENDERS`는 쉼표로 구분하며 와일드카드를 사용할 수 있습니다.

```env
TARGET_SENDERS=alert@example.com,*@notice.example.com,*@*.example.org
```

정확한 일치가 필요하면 전체 이메일 주소를 입력하고, 여러 하위 도메인을 허용해야 하면 와일드카드를 사용합니다. 실제 운영 값은 `.env`, Docker 환경 변수, GitHub Secrets 등 실행 환경에서 주입합니다.
