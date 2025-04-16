pipeline {
    agent {
        docker {
            image 'docker:20.10.24-dind'
            args '-v /var/run/docker.sock:/var/run/docker.sock'
        }
    }

    environment {
        AWS_REGION = 'us-west-2'                 // ✔️ Update this if your region is different
        EB_APP_NAME = 'my-flask-app'             // ✔️ Your actual Elastic Beanstalk App Name
        EB_ENV_NAME = 'flask-env'                // ✔️ Your actual EB Environment Name
        DOCKER_IMAGE = 'flask-eb-image'          // Optional custom image name
    }

    stages {
        stage('Build Docker Image') {
            steps {
                sh 'docker build -t $DOCKER_IMAGE .'
            }
        }

        stage('Deploy to Elastic Beanstalk') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'my-aws-access']]) {
                    sh '''
                        echo "Initializing EB CLI..."
                        eb init "$EB_APP_NAME" --region "$AWS_REGION" --platform "Docker" --quiet

                        echo "Setting EB environment..."
                        eb use "$EB_ENV_NAME"

                        echo "Deploying application..."
                        eb deploy "$EB_ENV_NAME" --staged --verbose
                    '''
                }
            }
        }
    }
}
