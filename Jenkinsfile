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
                script {
                    sh 'sudo apt-get update && sudo apt-get install -y python3-venv'
                    sh 'python3 -m venv venv'
                    sh '. venv/bin/activate'
                }
            }
        }

        stage('Install Dependencies') {
            steps {
                script {
                    sh '''
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    pip install pytest
                    '''
                }
            }
        }


        stage('Deploy to Elastic Beanstalk') {
            steps {
                withAWS(credentials: 'aws-eb-credentials', region: "${AWS_REGION}") {
                    script {
                        sh '''
                        . venv/bin/activate
                        aws --version || (echo "AWS CLI not found" && exit 1)
                        zip -r application.zip . -x '*.git*' 'env/*' '*.venv/*' '__pycache__/*'
                        eb init ${EB_APP_NAME} --region ${AWS_REGION} --platform "Docker"
                        eb use ${EB_ENV_NAME}
                        eb deploy
                        '''
                    }
                }
            }
        }
    }
}
