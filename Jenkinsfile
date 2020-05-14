pipeline {
    agent any
    options {
        disableConcurrentBuilds()
    }

    stages {

        stage('Build') {
            steps {
                script {
                    // Setup virtual env
                    sh "rm -rf .venv || true"
                    sh "virtualenv .venv"

                    // Run build
                    sh "rm -rf dist build || true"
                    wd = pwd()
                    docker.image("quay.io/pypa/manylinux2010_x86_64").inside("-v ${wd}:/io -u root") {
                          sh '/io/build-manylinux.sh'
                          sh "rm /io/py_desmume.egg-info -rf"
                    }
                }
            }
            post {
                always {
                    archiveArtifacts allowEmptyArchive: true, artifacts: 'dist/*whl', fingerprint: true
                }
            }
        }

        stage('Deploy to PyPI') {
            when {
                branch "release"
            }
            environment {
                TWINE    = credentials('parakoopa-twine-username-password')
            }
            steps {
                sh 'twine upload -u "$TWINE_USR" -p "$TWINE_PSW" dist/*manylinux2010*'
            }
        }

    }

}
