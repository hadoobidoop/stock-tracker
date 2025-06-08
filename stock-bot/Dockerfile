# 1. 베이스 이미지 선택: Python 3.11 슬림 버전을 기반으로 시작
FROM python:3.11-slim

# 2. 작업 디렉토리 설정: 컨테이너 안의 /app 폴더를 작업 공간으로 지정
WORKDIR /app

# 3. requirements.txt 파일을 먼저 복사하여 캐싱 활용
# (파일 내용이 변경되지 않으면 이 레이어는 다시 빌드하지 않아 빌드 속도 향상)
COPY requirements.txt .

# 4. 의존성 설치
RUN pip install --no-cache-dir -r requirements.txt

# 5. 나머지 모든 소스 코드를 컨테이너 안으로 복사
COPY . .

# 6. 컨테이너가 시작될 때 실행할 기본 명령어
CMD ["python", "main.py"]
