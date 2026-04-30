# EMail_Auto_Fowarder

네이버 메일함을 주기적으로 확인해, 지정한 발신자 패턴과 일치하는 메일만 목표 주소로 자동 포워딩하는 Python 프로그램입니다.

## 동작 방식

1. `POLL_INTERVAL` 초마다 IMAP 서버에 접속해 `IMAP_MAILBOX`를 확인합니다.
2. 저장된 `last_uid` 이후의 메일만 `UID SEARCH`로 검색합니다.
3. `TARGET_SENDERS`를 바탕으로 서버의 `FROM` 검색을 먼저 수행합니다.
4. 후보 메일은 `BODY.PEEK[HEADER]`로 헤더만 가져와 발신자를 최종 확인합니다.
5. 조건에 맞는 메일만 `BODY[]`로 본문을 가져와 `FORWARD_TO`로 전달합니다.
6. 처리가 끝난 마지막 UID를 상태 파일에 저장해 다음 실행 때 이어서 처리합니다.

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

## 발신자 패턴

`TARGET_SENDERS`는 쉼표로 구분하며 와일드카드를 사용할 수 있습니다.

```env
TARGET_SENDERS=<*@*.openai.com>,alert@example.com
```

`<*@*.openai.com>`은 `name@sub.openai.com`처럼 하위 도메인 발신자와 일치합니다. 서버 검색 단계에서는 `openai.com`으로 후보를 줄이고, 헤더 확인 단계에서 실제 와일드카드 매칭을 수행합니다.
