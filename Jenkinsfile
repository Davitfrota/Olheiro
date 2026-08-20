pipeline {
    agent any

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        disableConcurrentBuilds(abortPrevious: true)
    }

    environment {
        COMPOSE_FILE = 'docker-compose.yml'
        COMPOSE_PROJECT_NAME = 'olheiro'
        PUBLIC_URL = 'https://olheiro.lumenscode.com.br'
        WEB_HOST_PORT = '4090'
        API_HOST_PORT = '4091'
    }

    parameters {
        booleanParam(
            name: 'DEPLOY_STACK',
            defaultValue: true,
            description: 'Build + docker compose up (web:4090 + api:4091).'
        )
        booleanParam(
            name: 'BUILD_NO_CACHE',
            defaultValue: false,
            description: 'docker compose build --no-cache --pull.'
        )
        string(
            name: 'GIT_REF',
            defaultValue: 'main',
            trim: true,
            description: 'Branch/tag/SHA a fazer checkout.'
        )
        string(
            name: 'GIT_REPO_URL',
            defaultValue: 'https://github.com/Davitfrota/Olheiro.git',
            trim: true,
            description: 'URL do repositório.'
        )
        string(
            name: 'GIT_CREDENTIAL_ID',
            defaultValue: 'key-github',
            trim: true,
            description: 'CredentialId Jenkins para GitHub.'
        )
        string(
            name: 'ENV_CREDENTIAL_ID',
            defaultValue: 'olheiro-env',
            trim: true,
            description: 'Secret file Jenkins com o .env de produção (Supabase + AbacatePay).'
        )
    }

    stages {
        stage('Contexto') {
            steps {
                script {
                    echo "[olheiro] JOB=${env.JOB_NAME} REF=${params.GIT_REF}"
                    echo "[olheiro] PUBLIC_URL=${env.PUBLIC_URL}"
                    echo "[olheiro] web=127.0.0.1:${env.WEB_HOST_PORT} api=127.0.0.1:${env.API_HOST_PORT}"
                }
            }
        }

        stage('Checkout') {
            steps {
                script {
                    def ref = params.GIT_REF?.trim() ?: 'main'
                    checkout([
                        $class: 'GitSCM',
                        branches: [[name: ref]],
                        userRemoteConfigs: [[
                            url: params.GIT_REPO_URL,
                            credentialsId: params.GIT_CREDENTIAL_ID
                        ]],
                        extensions: [[$class: 'CloneOption', noTags: false, shallow: false, depth: 0]]
                    ])
                }
            }
        }

        stage('Resolver SHA') {
            steps {
                script {
                    env.GIT_SHA = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()
                    env.GIT_SHORT_SHA = sh(returnStdout: true, script: 'git rev-parse --short=12 HEAD').trim()
                    env.IMAGE_TAG = env.GIT_SHORT_SHA
                    currentBuild.description = "sha=${env.GIT_SHORT_SHA}"
                }
            }
        }

        stage('Preparar .env') {
            steps {
                withCredentials([
                    file(credentialsId: params.ENV_CREDENTIAL_ID, variable: 'ENV_FILE')
                ]) {
                    sh '''
                        set -e
                        chmod u+w "$WORKSPACE"
                        rm -f "$WORKSPACE/.env"
                        cp "$ENV_FILE" "$WORKSPACE/.env"
                        echo "[olheiro] .env copiado do credential ${ENV_CREDENTIAL_ID}"
                    '''
                }
            }
        }

        stage('Build imagens') {
            when { expression { return params.DEPLOY_STACK } }
            steps {
                script {
                    def noCache = params.BUILD_NO_CACHE ? '--no-cache --pull' : ''
                    withEnv([
                        "IMAGE_TAG=${env.IMAGE_TAG}",
                        "WEB_HOST_PORT=${env.WEB_HOST_PORT}",
                        "API_HOST_PORT=${env.API_HOST_PORT}",
                        "NO_CACHE_FLAGS=${noCache}",
                    ]) {
                        sh '''
                            set -e
                            docker compose build $NO_CACHE_FLAGS
                            docker tag "olheiro-web:$IMAGE_TAG" olheiro-web:latest
                            docker tag "olheiro-api:$IMAGE_TAG" olheiro-api:latest
                        '''
                    }
                }
            }
        }

        stage('Deploy') {
            when { expression { return params.DEPLOY_STACK } }
            steps {
                script {
                    withEnv([
                        "IMAGE_TAG=${env.IMAGE_TAG}",
                        "WEB_HOST_PORT=${env.WEB_HOST_PORT}",
                        "API_HOST_PORT=${env.API_HOST_PORT}",
                    ]) {
                        sh '''
                            set -e
                            docker compose down --remove-orphans || true
                            docker rm -f olheiro-web olheiro-api || true
                            if command -v ss >/dev/null 2>&1; then
                                if ss -ltn | grep -q ":${WEB_HOST_PORT} "; then
                                    echo "[olheiro] ERRO: porta web $WEB_HOST_PORT em uso"
                                    exit 1
                                fi
                                if ss -ltn | grep -q ":${API_HOST_PORT} "; then
                                    echo "[olheiro] ERRO: porta api $API_HOST_PORT em uso"
                                    exit 1
                                fi
                            fi
                            docker compose up -d --no-build
                            docker compose ps
                            sleep 2
                            curl -fsS "http://127.0.0.1:${API_HOST_PORT}/health" || true
                            curl -fsSI "http://127.0.0.1:${WEB_HOST_PORT}/" | head -n 5 || true
                        '''
                    }
                }
            }
        }
    }

    post {
        success {
            echo "[olheiro] Deploy OK — ${env.PUBLIC_URL}"
            echo "[olheiro] Webhook AbacatePay: ${env.PUBLIC_URL}/v1/billing/webhooks/abacatepay?webhookSecret=..."
        }
        failure {
            echo '[olheiro] Pipeline falhou.'
        }
    }
}
