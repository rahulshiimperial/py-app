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
                    // Install python3-venv if not already installed
                    sh 'sudo apt-get update && sudo apt-get install -y python3-venv'
                    
                    // Create a virtual environment
                    sh 'python3 -m venv venv'
                    
                    // Activate the virtual environment
                    sh '. venv/bin/activate'
                }
            }
        }

        stage('Install Dependencies') {
            steps {
                script {
                    // Activate the virtual environment and install dependencies
                    sh '''
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    '''
                }
            }
        }

        stage('Run Tests') {
            steps {
                script {
                    // Activate the virtual environment and run tests
                    sh '''
                    . venv/bin/activate
                    pytest
                    '''
                }
            }
        }

        stage('Deploy to Elastic Beanstalk') {
            steps {
                withAWS(credentials: 'aws-eb-credentials', region: "${AWS_REGION}") {
                    script {
                        // Activate the virtual environment, zip the application, and deploy
                        sh '''
                        . venv/bin/activate
                        zip -r application.zip . -x '*.git*' 'env/*' '*.venv/*' '__pycache__/*'
                        eb init ${EB_APP_NAME} --region ${AWS_REGION} --platform 'Python 3.7'
                        eb use ${EB_ENV_NAME}
                        eb deploy
                        '''
                    }
                }
            }
        }
    }
}
