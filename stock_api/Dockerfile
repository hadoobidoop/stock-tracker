# 1. 베이스 이미지 선택: JDK 17을 포함한 이미지를 기반으로 시작
FROM amazoncorretto:17-alpine-jdk

# 2. JAR 파일 인자 선언
ARG JAR_FILE=build/libs/*.jar

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 빌드된 JAR 파일을 컨테이너 안으로 복사하고 이름을 app.jar로 변경
COPY ${JAR_FILE} app.jar

# 5. 컨테이너가 시작될 때 실행할 기본 명령어
ENTRYPOINT ["java", "-jar", "app.jar"]

