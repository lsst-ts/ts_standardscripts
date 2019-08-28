pipeline {
    agent any
    environment {
        network_name = "n_${BUILD_ID}_${JENKINS_NODE_COOKIE}"
        container_name = "c_${BUILD_ID}_${JENKINS_NODE_COOKIE}"
    }

    stages {
        stage("Running tests") {
            steps {
                script {
                    sh """
                    docker network create \${network_name}
                    chmod -R a+rw \${WORKSPACE}
                    container=\$(docker run -v \${WORKSPACE}:/home/saluser/repo/ -td --rm --net \${network_name} --name \${container_name} lsstts/develop-env:salobj4_b30)
                    docker exec -u saluser \${container} sh -c \"source ~/.setup.sh && make_idl_files.py ATMCS ATPtg ATAOS ATPneumatics ATHexapod ATDome ATDomeTrajectory && cd repo && eups declare -r . -t saluser && setup ts_standardscripts -t saluser && scons\"
                    """
                }
            }
        }
    }
    post {
        always {
            // The path of xml needed by JUnit is relative to
            // the workspace.
            junit 'tests/.tests/*.xml'

            // Publish the HTML report
            publishHTML (target: [
                allowMissing: false,
                alwaysLinkToLastBuild: false,
                keepAll: true,
                reportDir: 'tests/.tests/pytest-ts_standardscripts.xml-htmlcov',
                reportFiles: 'index.html',
                reportName: "Coverage Report"
              ])
        }
        cleanup {
            sh """
                docker stop \${container_name} || echo Could not stop container
                docker network rm \${network_name} || echo Could not remove network
                container=\$(docker run -v \${WORKSPACE}:/home/saluser/repo/ -td --rm lsstts/salobj:master)
                docker exec -u root --privileged \${container} sh -c \"chmod -R a+rw /home/saluser/repo/ \"
                docker stop \${container}
            """
            deleteDir()
        }
    }
}
