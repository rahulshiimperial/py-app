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

        stage('Install Dependencies') {
            steps {
                sh 'pip install -r requirements.txt'
            }
        }

        stage('Run Tests') {
            steps {
                sh 'pytest' // Ensure you have tests set up
            }
        }

        stage('Deploy to Elastic Beanstalk') {
            steps {
                withAWS(credentials: 'aws-eb-credentials', region: "${AWS_REGION}") {
                    sh """
                        zip -r application.zip . -x '*.git*' 'env/*' '*.venv/*' '__pycache__/*'
                        eb init ${EB_APP_NAME} --region ${AWS_REGION} --platform 'Python 3.7'
                        eb use ${EB_ENV_NAME}
                        eb deploy
                    """
                }
            }
        }
    }
}
