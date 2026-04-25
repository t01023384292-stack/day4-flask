# Flask + SQLite(Render) 배포 설계서

## 1) 목표
현재 `board_flask_sqlite` Flask 앱을 Render에 배포하고, SQLite를 유지한 채 데이터 영속성을 확보한다.

요구사항:
- 배포 플랫폼: Render
- DB: SQLite 유지
- 도메인: Render 기본 도메인 사용
- 데이터: 재시작/재배포 후에도 유지

## 2) 배포 아키텍처
- Render Web Service 1개 구성
- Python 런타임에서 `gunicorn`으로 Flask 앱 실행
- SQLite 파일은 Render Persistent Disk 마운트 경로에 저장
- 앱은 환경변수(`DATABASE_PATH`)를 통해 SQLite 파일 경로를 결정
- 로컬 개발은 기존 기본 경로(`board.db`)로 계속 동작

## 3) 코드/파일 변경 범위
### 3.1 `app.py`
- DB 경로를 하드코딩하지 않고 `DATABASE_PATH` 환경변수 우선 사용
- 값이 없으면 로컬 기본값(`board.db`) 사용
- 기존 `init_db()` 로직 유지(테이블 생성 + 빈 테이블이면 샘플 데이터 삽입)

### 3.2 `requirements.txt` 추가
- `flask`
- `gunicorn`

### 3.3 `.gitignore` 점검
- `board.db` 추적 제외 유지
- 파이썬 캐시 파일 제외 유지

### 3.4 `README.md` (선택)
- 로컬 실행 방법
- Render 설정값(빌드/시작 명령, 환경변수, 디스크 경로)
- 기본 검증 시나리오

## 4) Render 서비스 설정
- **Root Directory:** `board_flask_sqlite`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn -b 0.0.0.0:$PORT app:app`
- **Environment Variable:**
  - `DATABASE_PATH=/var/data/board.db`
- **Persistent Disk:**
  - Mount Path: `/var/data`

SQLite 실제 파일은 `/var/data/board.db`에 생성/사용된다.

## 5) 데이터 초기화/영속성 설계
- 첫 배포 시 DB 파일이 없으면 앱 시작 시 생성
- `posts`가 비어 있을 때만 샘플 데이터 삽입
- 재배포/재시작 시 Persistent Disk 재마운트로 기존 DB 재사용
- 따라서 작성된 게시글은 유지되고 샘플 중복 삽입은 발생하지 않음

## 6) 검증 시나리오
배포 후 아래를 순서대로 확인한다.
1. Render 로그에서 build/start 성공
2. 기본 도메인(`/`) 접속 200
3. 글 작성 → 상세 페이지 이동 정상
4. Render 서비스 재시작 후 작성 글이 유지되는지 확인
5. `/posts/999999` 접근 시 404 확인

## 7) 범위 밖(이번 단계 제외)
- SQLite → PostgreSQL 마이그레이션
- 커스텀 도메인 설정
- 인증/권한/관리자 기능
- 다중 인스턴스 확장 대응

## 8) 완료 기준
아래를 만족하면 이번 배포 준비를 완료로 본다.
- Render 배포 설정값이 코드와 일치
- `gunicorn` 기반 기동 성공
- `DATABASE_PATH` 적용으로 Persistent Disk에 DB 저장
- 재시작 후 데이터 유지 확인
