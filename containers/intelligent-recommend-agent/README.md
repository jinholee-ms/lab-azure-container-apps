# Intelligent Recommend Agent

컨테이너 기반으로 실행되는 지능형 추천 에이전트 애플리케이션입니다. Azure Container Apps 등 컨테이너 오케스트레이션 환경에 배포되어 상품/콘텐츠/문서 등의 추천 기능을 제공하도록 설계되었습니다.

## 주요 특징
- 에이전트 구조: `agents/`와 `capabilities/` 폴더로 역할과 기능을 분리
- 확장성: `tools/`와 `common.py`를 통해 공통 로직 재사용 및 기능 확장
- 배포 친화: `Dockerfile`, `Makefile`을 이용해 일관된 빌드/배포 파이프라인 지원
- 테스트: `tests/` 폴더에 단위/통합 테스트 포함
- 설정 관리: `.env` 및 `pyproject.toml`, `requirements.txt`를 통한 의존성과 환경변수 관리

## 디렉토리 구조
- `main.py`: 애플리케이션 진입점(서버/CLI 등 실행 로직)
- `common.py`: 로깅, 설정, 유틸 등 공통 모듈
- `agents/`: 추천 에이전트 구현(여러 에이전트 클래스/전략 포함 가능)
- `capabilities/`: 추천에 필요한 기능(예: 랭킹, 필터링, 피처 추출 등)
- `tools/`: 데이터 수집/전처리/운영 스크립트 등 보조 도구
- `assets/`: 테스트/데모용 데이터나 리소스 (로컬 개발용)
- `tests/`: 단위/통합 테스트 코드
- `Dockerfile`: 컨테이너 이미지 빌드 정의
- `Makefile`: 개발/빌드/테스트/배포 자동화 명령
- `pyproject.toml`: 프로젝트 메타/의존성 정의(uv/poetry 등 호환)
- `requirements.txt`: 런타임 의존성 목록(pip)
- `uv.lock`: 의존성 고정(lock 파일)
- `.env.example`: 환경변수 정의 파일(로컬 개발용)
- `.az-release`: Azure 변수 정의 파일

## 사전 요구사항
- Python 3.x (`.python-version` 참고)
- 패키지 매니저: `pip` 또는 `uv`
- 컨테이너 도구: `Docker`(이미지 빌드/실행)
- 선택: Azure CLI 및 Azure Container Apps 배포 권한

## 빠른 시작
### 1) 의존성 설치
`pip` 또는 `uv` 중 하나를 사용하세요.

```zsh
# pip 사용
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# uv 사용(권장)
uv sync
```

### 2) 환경변수 설정
`.env.example`을 복사 후 값 설정:

```zsh
cp .env.example .env
```

### 3) 애플리케이션 실행

```zsh
source .venv/bin/activate  # 가상환경 활성화(uv 사용 시 생략 가능)
python main.py
```

## 개발 워크플로우
- 포맷팅/린트(프로젝트 설정에 따라 다를 수 있음):

```zsh
make fmt   # 코드 포맷팅
make lint  # 린트 검사
```

- 테스트 실행:

```zsh
make test  # 또는
pytest -q
```

## 컨테이너 빌드 및 실행
- 이미지 빌드:

```zsh
docker build -t intelligent-recommend-agent:local .
```

- 로컬 실행(환경변수 파일 적용):

```zsh
docker run --rm -it \
	--env-file .env \
	-p 8080:8080 \
	intelligent-recommend-agent:local
```

## Azure Container Apps 배포(예시)
환경/리소스 그룹/컨테이너 앱 이름 등은 조직 환경에 맞게 변경하세요.

```zsh
# Azure 로그인 및 구독/리소스 그룹 설정
az login
az account set --subscription <SUBSCRIPTION_ID>
az group create -n <RG_NAME> -l <LOCATION>

# 컨테이너 레지스트리 푸시(예: ACR)
az acr create -n <ACR_NAME> -g <RG_NAME> --sku Basic
az acr login --name <ACR_NAME>
docker tag intelligent-recommend-agent:local <ACR_NAME>.azurecr.io/intelligent-recommend-agent:latest
docker push <ACR_NAME>.azurecr.io/intelligent-recommend-agent:latest

# 컨테이너 앱 환경 생성 및 배포
az containerapp env create -n <ENV_NAME> -g <RG_NAME> -l <LOCATION>
az containerapp create \
	-n <APP_NAME> \
	-g <RG_NAME> \
	--environment <ENV_NAME> \
	--image <ACR_NAME>.azurecr.io/intelligent-recommend-agent:latest \
	--registry-server <ACR_NAME>.azurecr.io \
	--ingress external --target-port 8080 \
	--env-vars @.env
```

## 설정 및 환경변수
주요 환경변수(프로젝트에 따라 다를 수 있음):
- `LOG_LEVEL`: 로깅 레벨(`INFO`, `DEBUG` 등)
- `MODEL_NAME`/`ENDPOINT_URL`: 외부 모델/추천 API 연동 시 사용
- `DATA_SOURCE_PATH`: 로컬/원격 데이터 경로
- `CACHE_DIR`: 캐시 폴더

`.env.example`를 참고하여 필요한 값을 채우세요.

## 테스트 전략
- `tests/`에 단위 테스트와 간단한 통합 테스트 포함
- 추천 로직(랭킹/필터링)과 에이전트 인터페이스를 우선 검증
- CI 환경에서 `pytest`와 코드 커버리지 도구 연계 권장

## 라이선스
이 프로젝트의 라이선스는 저장소의 최상위 또는 본 디렉토리의 `LICENSE`를 참고하세요.

## 참고
- Azure 배포와 데이터 모델링에는 Azure Cosmos DB를 활용하기 좋습니다.
	- 파티션 키 설계(예: `userId`, `tenantId`)와 HPK로 쿼리 유연성/스케일 고려
	- SDK 재시도/진단 로깅(429 대응) 권장
- 컨테이너 이미지 사이즈 최적화 및 보안 스캔을 CI에 포함하세요.
