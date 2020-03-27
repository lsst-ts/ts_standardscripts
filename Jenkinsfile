pipeline {
    agent any
    environment {
        network_name = "n_${BUILD_ID}_${JENKINS_NODE_COOKIE}"
        container_name = "c_${BUILD_ID}_${JENKINS_NODE_COOKIE}"
        work_branches = "${GIT_BRANCH} ${CHANGE_BRANCH} master"
    }

    stages {
        stage("Pulling docker image") {
            steps {
                script {
                    sh """
                    docker pull lsstts/develop-env:master
                    """
                }
            }
        }
        stage("Preparing environment") {
            steps {
                script {
                    sh """
                    docker network create \${network_name}
                    chmod -R a+rw \${WORKSPACE}
                    container=\$(docker run -v \${WORKSPACE}:/home/saluser/repo/ -td --rm --net \${network_name} --name \${container_name} lsstts/develop-env:master)
                    """
                }
            }
        }
        stage("Checkout sal") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_sal && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }
        stage("Checkout salobj") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_salobj && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }
        stage("Checkout xml") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_xml && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }
        stage("Checkout IDL") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_idl && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }
        stage("Checkout ts_simactuators") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_simactuators && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }

        stage("Checkout ts_scriptqueue") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_scriptqueue && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }


        stage("Checkout ts_ATDomeTrajectory") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_ATDomeTrajectory && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }

        stage("Checkout ts_ATDome") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_ATDome && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }
        stage("Checkout ts_externalscripts") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_externalscripts && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }
        stage("Checkout ts_ATMCSSimulator") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_ATMCSSimulator && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }
        stage("Checkout ts_config_attcs") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_config_attcs && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }
        stage("Build IDL files") {
            steps {
                script {
                    sh """
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build ATAOS; make_idl_files.py ATAOS &> /dev/null || echo FAILED to build ATAOS\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build ATArchiver; make_idl_files.py ATArchiver &> /dev/null || echo FAILED to build ATArchiver\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build ATBuilding; make_idl_files.py ATBuilding &> /dev/null || echo FAILED to build ATBuilding\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build ATCamera; make_idl_files.py ATCamera &> /dev/null || echo FAILED to build ATCamera\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build ATDome; make_idl_files.py ATDome &> /dev/null || echo FAILED to build ATDome\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build ATDomeTrajectory; make_idl_files.py ATDomeTrajectory &> /dev/null || echo FAILED to build ATDomeTrajectory\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build ATHeaderService; make_idl_files.py ATHeaderService &> /dev/null || echo FAILED to build ATHeaderService\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build ATHexapod; make_idl_files.py ATHexapod &> /dev/null || echo FAILED to build ATHexapod\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build ATMCS; make_idl_files.py ATMCS &> /dev/null || echo FAILED to build ATMCS\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build ATMonochromator; make_idl_files.py ATMonochromator &> /dev/null || echo FAILED to build ATMonochromator\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build ATPneumatics; make_idl_files.py ATPneumatics &> /dev/null || echo FAILED to build ATPneumatics\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build ATPtg; make_idl_files.py ATPtg &> /dev/null || echo FAILED to build ATPtg\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build ATSpectrograph; make_idl_files.py ATSpectrograph &> /dev/null || echo FAILED to build ATSpectrograph\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build ATTCS; make_idl_files.py ATTCS &> /dev/null || echo FAILED to build ATTCS\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build ATWhiteLight; make_idl_files.py ATWhiteLight &> /dev/null || echo FAILED to build ATWhiteLight\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build CatchupArchiver; make_idl_files.py CatchupArchiver &> /dev/null || echo FAILED to build CatchupArchiver\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build CBP; make_idl_files.py CBP &> /dev/null || echo FAILED to build CBP\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build CCArchiver; make_idl_files.py CCArchiver &> /dev/null || echo FAILED to build CCArchiver\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build CCCamera; make_idl_files.py CCCamera &> /dev/null || echo FAILED to build CCCamera\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build CCHeaderService; make_idl_files.py CCHeaderService &> /dev/null || echo FAILED to build CCHeaderService\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build DIMM; make_idl_files.py DIMM &> /dev/null || echo FAILED to build DIMM\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build Dome; make_idl_files.py Dome &> /dev/null || echo FAILED to build Dome\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build DSM; make_idl_files.py DSM &> /dev/null || echo FAILED to build DSM\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build EAS; make_idl_files.py EAS &> /dev/null || echo FAILED to build EAS\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build EFD; make_idl_files.py EFD &> /dev/null || echo FAILED to build EFD\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build EFDTransformationServer; make_idl_files.py EFDTransformationServer &> /dev/null || echo FAILED to build EFDTransformationServer\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build Electrometer; make_idl_files.py Electrometer &> /dev/null || echo FAILED to build Electrometer\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build Environment; make_idl_files.py Environment &> /dev/null || echo FAILED to build Environment\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build FiberSpectrograph; make_idl_files.py FiberSpectrograph &> /dev/null || echo FAILED to build FiberSpectrograph\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build GenericCamera; make_idl_files.py GenericCamera &> /dev/null || echo FAILED to build GenericCamera\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build Hexapod; make_idl_files.py Hexapod &> /dev/null || echo FAILED to build Hexapod\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build HVAC; make_idl_files.py HVAC &> /dev/null || echo FAILED to build HVAC\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build IOTA; make_idl_files.py IOTA &> /dev/null || echo FAILED to build IOTA\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build LinearStage; make_idl_files.py LinearStage &> /dev/null || echo FAILED to build LinearStage\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build LOVE; make_idl_files.py LOVE &> /dev/null || echo FAILED to build LOVE\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build MTAlignment; make_idl_files.py MTAlignment &> /dev/null || echo FAILED to build MTAlignment\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build MTAOS; make_idl_files.py MTAOS &> /dev/null || echo FAILED to build MTAOS\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build MTArchiver; make_idl_files.py MTArchiver &> /dev/null || echo FAILED to build MTArchiver\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build MTCamera; make_idl_files.py MTCamera &> /dev/null || echo FAILED to build MTCamera\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build MTDomeTrajectory; make_idl_files.py MTDomeTrajectory &> /dev/null || echo FAILED to build MTDomeTrajectory\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build MTEEC; make_idl_files.py MTEEC &> /dev/null || echo FAILED to build MTEEC\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build MTGuider; make_idl_files.py MTGuider &> /dev/null || echo FAILED to build MTGuider\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build MTHeaderService; make_idl_files.py MTHeaderService &> /dev/null || echo FAILED to build MTHeaderService\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build MTLaserTracker; make_idl_files.py MTLaserTracker &> /dev/null || echo FAILED to build MTLaserTracker\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build MTM1M3; make_idl_files.py MTM1M3 &> /dev/null || echo FAILED to build MTM1M3\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build MTM1M3TS; make_idl_files.py MTM1M3TS &> /dev/null || echo FAILED to build MTM1M3TS\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build MTM2; make_idl_files.py MTM2 &> /dev/null || echo FAILED to build MTM2\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build MTMount; make_idl_files.py MTMount &> /dev/null || echo FAILED to build MTMount\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build MTPtg; make_idl_files.py MTPtg &> /dev/null || echo FAILED to build MTPtg\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build MTTCS; make_idl_files.py MTTCS &> /dev/null || echo FAILED to build MTTCS\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build MTVMS; make_idl_files.py MTVMS &> /dev/null || echo FAILED to build MTVMS\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build NewMTMount; make_idl_files.py NewMTMount &> /dev/null || echo FAILED to build NewMTMount\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build PointingComponent; make_idl_files.py PointingComponent &> /dev/null || echo FAILED to build PointingComponent\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build PromptProcessing; make_idl_files.py PromptProcessing &> /dev/null || echo FAILED to build PromptProcessing\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build Rotator; make_idl_files.py Rotator &> /dev/null || echo FAILED to build Rotator\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build Scheduler; make_idl_files.py Scheduler &> /dev/null || echo FAILED to build Scheduler\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build Script; make_idl_files.py Script &> /dev/null || echo FAILED to build Script\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build ScriptQueue; make_idl_files.py ScriptQueue &> /dev/null || echo FAILED to build ScriptQueue\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build SummitFacility; make_idl_files.py SummitFacility &> /dev/null || echo FAILED to build SummitFacility\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build Test; make_idl_files.py Test &> /dev/null || echo FAILED to build Test\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build TunableLaser; make_idl_files.py TunableLaser &> /dev/null || echo FAILED to build TunableLaser\"
docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && echo Build Watcher; make_idl_files.py Watcher &> /dev/null || echo FAILED to build Watcher\"
                    """
                }
            }
        }
        stage("Running tests") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repo/ && eups declare -r . -t saluser && setup ts_standardscripts -t saluser && export LSST_DDS_IP=192.168.0.1 && printenv LSST_DDS_IP && py.test --junitxml=tests/.tests/junit.xml\"
                    """
                }
            }
        }
    }
    post {
        always {
            // The path of xml needed by JUnit is relative to
            // the workspace.
            junit 'tests/.tests/junit.xml'

            // Publish the HTML report
            publishHTML (target: [
                allowMissing: false,
                alwaysLinkToLastBuild: false,
                keepAll: true,
                reportDir: 'tests/.tests/',
                reportFiles: 'index.html',
                reportName: "Coverage Report"
              ])
        }
        cleanup {
            sh """
                docker exec -u root --privileged \${container_name} sh -c \"chmod -R a+rw /home/saluser/repo/ \"
                docker stop \${container_name} || echo Could not stop container
                docker network rm \${network_name} || echo Could not remove network
            """
            deleteDir()
        }
    }
}
