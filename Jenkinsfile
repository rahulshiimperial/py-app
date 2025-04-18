pipeline {
    agent any

    environment {
        AWS_CREDENTIALS = credentials('aws-eb-credentials')
        AWS_REGION = 'us-west-2'
        EB_APP_NAME = 'my-flask-app'
        EB_ENV_NAME = 'flask-env'
    }

    stages {

        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/rahulshiimperial/py-app.git'
            }
        }

        stage('Set Up Python Environment') {
            steps {
                sh '''
                sudo apt-get update && sudo apt-get install -y python3-venv
                python3 -m venv venv
                '''
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                . venv/bin/activate
                pip install --upgrade pip
                pip install -r requirements.txt
                pip install pytest awsebcli
                '''
            }
        }

        stage('Install System Tools') {
            steps {
                sh '''
                while sudo fuser /var/lib/apt/lists/lock >/dev/null 2>&1; do
                    echo "Waiting for apt lock to be released..."
                    sleep 5
                done

                sudo apt-get update
                sudo apt-get install -y zip unzip curl
                '''
            }
        }

        stage('Package App') {
            steps {
                sh 'zip -r application.zip . -x "*.git*" "venv/*" "__pycache__/*"'
            }
        }

        stage('Deploy to Elastic Beanstalk') {
            steps {
                withAWS(credentials: 'aws-eb-credentials', region: "${AWS_REGION}") {
                    sh '''
                    . venv/bin/activate
                    aws --version || (echo "AWS CLI not found" && exit 1)
                    eb init ${EB_APP_NAME} --region ${AWS_REGION} --platform "Docker" --debug
                    eb use ${EB_ENV_NAME}
                    eb deploy --staged --debug
                    '''
                }
            }
        }
    }
}
