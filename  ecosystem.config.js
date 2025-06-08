module.exports = {
    /**
     * 애플리케이션 설정
     * apps 배열 안에, pm2로 관리할 각 애플리케이션의 설정을 객체 형태로 추가합니다.
     */
    apps: [
        // --------------------------------------------------
        // 1. 파이썬 분석 워커 (Python Analysis Worker)
        // --------------------------------------------------
        {
            // --- 필수 설정 ---
            name: 'stock-bot-worker',       // pm2가 이 앱을 식별할 때 사용할 이름 (pm2 list, pm2 restart 등에 사용)
            script: './stock-bot/main.py',  // 이 앱을 실행할 스크립트 파일의 경로

            // --- 파이썬 관련 설정 ---
            interpreter: './stock-bot/venv/bin/python3',      // 사용할 파이썬 인터프리터. 가상환경을 쓴다면 venv/bin/python3 와 같이 지정도 가능합니다.

            // --- 실행 관련 옵션 ---
            exec_mode: 'fork',              // 단일 프로세스로 실행 (파이썬 스케줄러는 보통 fork 모드를 사용)
            instances: 1,                   // 1개의 프로세스만 실행

            // --- 자동 재시작 관련 설정 ---
            autorestart: true,              // 앱이 예상치 못하게 종료되었을 때 자동으로 재시작할지 여부 (강력 추천)
            watch: false,                   // 파일이 변경될 때 자동으로 재시작할지 여부 (개발 환경에서는 유용하나, 운영 환경에서는 보통 false로 설정)

            // --- 성능 및 자원 관련 설정 ---
            max_memory_restart: '500M',     // 메모리 사용량이 500MB를 초과하면 자동으로 재시작 (메모리 누수 방지)

            // --- 로그 관련 설정 ---
            output: './logs/bot-out.log',   // 일반 로그 파일 경로
            error: './logs/bot-error.log',  // 에러 로그 파일 경로
            log_date_format: 'YYYY-MM-DD HH:mm:ss', // 로그의 타임스탬프 형식

        },

        // --------------------------------------------------
        // 2. 스프링 부트 API 서버 (Spring Boot API Server)
        // --------------------------------------------------
        // {
        //     // --- 필수 설정 ---
        //     name: 'stock-api-server',       // pm2가 식별할 이름
        //     script: 'java',                 // 실행할 명령어 (java)
        //
        //     // --- 실행 인자(Argument) 설정 ---
        //     args: [
        //         '-jar',                                     // java 명령어의 -jar 옵션
        //         './stock-api/build/libs/stock-api-0.0.1-SNAPSHOT.jar', // 실행할 JAR 파일의 경로. 버전명은 실제 파일에 맞게 수정해야 합니다.
        //         '--spring.profiles.active=prod'             // 스프링 부트의 'prod' 프로파일 활성화
        //     ],
        //
        //     // --- 실행 관련 옵션 ---
        //     exec_mode: 'fork',
        //     instances: 1,
        //
        //     // --- 자동 재시작 및 성능 설정 ---
        //     autorestart: true,
        //     watch: false,
        //     max_memory_restart: '800M',     // 스프링 서버에 더 많은 메모리 할당
        //
        //     // --- 로그 관련 설정 ---
        //     output: './logs/api-out.log',
        //     error: './logs/api-error.log',
        //     log_date_format: 'YYYY-MM-DD HH:mm:ss',
        //
        //     // --- 환경 변수 설정 ---
        //     env: {
        //         NODE_ENV: 'production',
        //         // 스프링 부트 애플리케이션에서 사용할 환경 변수 설정
        //         // application-prod.properties 또는 yml 파일에서 이 변수들을 참조할 수 있습니다.
        //         // 예: DB_USER, DB_PASSWORD, JWT_SECRET 등
        //     },
        // }
    ]
}