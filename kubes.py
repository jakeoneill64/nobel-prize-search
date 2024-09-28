import time
from kubernetes import client, config
import sys
import docker
import os
import logging
import yaml
import string
import secrets
import base64
import subprocess

def clean(app_client, core_client):
    deployment_names = [item.metadata.name for item in app_client.list_namespaced_deployment(namespace='nobel').items]
    services_names = [item.metadata.name for item in core_client.list_namespaced_service(namespace='nobel').items]
    persistent_volume_names = [item.metadata.name for item in core_client.list_persistent_volume().items]
    persistent_volume_claims = [item.metadata.name for item in
                                core_client.list_namespaced_persistent_volume_claim(namespace='nobel').items]
    secret_names = [item.metadata.name for item in core_client.list_namespaced_secret(namespace='nobel').items]

    errors = []

    for deployment in deployment_names:
        try:
            app_client.delete_namespaced_deployment(deployment, 'nobel')
        except Exception as e:
            errors.append(str(e))

    for service in services_names:
        try:
            core_client.delete_namespaced_service(service, 'nobel')
        except Exception as e:
            errors.append(str(e))

    for pv in persistent_volume_names:
        try:
            core_client.delete_persistent_volume(pv)
        except Exception as e:
            errors.append(str(e))

    for pvc in persistent_volume_claims:
        try:
            core_client.delete_namespaced_persistent_volume_claim(pvc, 'nobel')
        except Exception as e:
            errors.append(str(e))

    for secret in secret_names:
        try:
            core_client.delete_namespaced_secret(secret, 'nobel')
        except Exception as e:
            errors.append(str(e))

    if len(errors) > 0:
        logger.warning("tore down nobel app deployment with errors " + ','.join(errors))
    else:
        logger.info("successfully tore down nobel app deployment")


def _process_resource_file(
        app_client, core_client, resource_file, **kwargs
):
    with open(resource_file, 'r') as file:
        resource_definitions = yaml.safe_load_all(file)
        for definition in resource_definitions:
            definition_kind = definition['kind'].lower()
            definition_name = definition['metadata']['name']
            try:
                match definition_kind:
                    case 'deployment':
                        app_client.create_namespaced_deployment(namespace='nobel', body=definition)
                    case 'service':
                        core_client.create_namespaced_service(namespace='nobel', body=definition)
                    case 'persistentvolume':
                        core_client.create_persistent_volume(body=definition)
                    case 'persistentvolumeclaim':
                        core_client.create_namespaced_persistent_volume_claim(namespace='nobel', body=definition)
                    case 'secret':
                        core_client.create_namespaced_secret(namespace='nobel', body=definition)
            except Exception as e:
                logger.error(f'could not create object from definition {str(e)}')
            logger.info(f'successfully created {definition_kind} {definition_name}')


def _update_env_values(file_path, replacements):
    env_dict = {}
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_dict[key.strip()] = value.strip()

    for key, value in replacements.items():
        env_dict[key] = value

    with open(file_path, 'w') as file:
        for key, value in env_dict.items():
            file.write(f"{key}={value}\n")


def deploy(
        app_client, core_client
):
    password_chars = string.ascii_letters + string.digits + string.punctuation
    db_root_password = ''.join(secrets.choice(password_chars) for _ in range(20))

    _update_env_values(
        './devops-test-api/.env',
        {
            'DB_HOST': 'mysql-service',
            'REDIS_HOST': 'redis-service',
            'DB_USERNAME': 'root',
            'DB_PASSWORD': db_root_password,
            'APP_URL': 'http://api-service'
        }
    )

    _update_env_values(
        './devops-test-web/.env',
        {
            'REDIS_HOST': 'redis-service',
            'APP_URL': 'http://web-service',
            'API_APP_URL': 'http://api-service'
        }
    )

    docker_client = docker.from_env()

    for image_name, filename in \
            [(filename[len('Dockerfile.'):], filename) for filename in os.listdir('.') if
             filename.startswith('Dockerfile.')]:
        logger.info('building docker image: ' + image_name)
        try:
            docker_client.images.build(path='.', dockerfile=filename, tag=image_name)
        except Exception as e:
            logger.fatal(f'docker image build for {image_name} failed: {str(e)}')
            return
        logger.info(f'successfully built {image_name}')

    namespace = client.V1Namespace(
        metadata=client.V1ObjectMeta(name='nobel')
    )

    if not 'nobel' in [item.metadata.name for item in core_client.list_namespace().items]:
        core_client.create_namespace(namespace)

    secret_data = {
        'root-password': base64.b64encode(db_root_password.encode('utf-8')).decode('utf-8')
    }

    core_client.create_namespaced_secret(
        namespace='nobel',
        body=client.V1Secret(
            api_version='v1',
            kind='Secret',
            metadata=client.V1ObjectMeta(name='nobel-secrets'),
            data=secret_data
        )
    )
    _process_resource_file(app_client, core_client, './persistence.yaml')
    time.sleep(30)
    _process_resource_file(app_client, core_client, './deployment.yaml')

    def is_mysql_ready():

        pod_conditions = [
            item.status.conditions for item in core_client.list_namespaced_pod('nobel', label_selector='app=mysql').items
        ]

        if pod_conditions is None or len(pod_conditions) == 0:
            return False

        for condition in pod_conditions[0]:
            if condition.type == 'Ready' and condition.status == 'True':
                return True

    wait_time = 2
    while not is_mysql_ready():
        if wait_time > 256:
            logger.error('mysql took too long to initialise, exiting')

        # would be better to use asycio for more complex setups.
        time.sleep(wait_time)
        wait_time *= 2
        logger.info('polling mysql...')

    logger.info('mysql ready, deploying api server')
    _process_resource_file(app_client, core_client, './api-deployment.yaml')
    _process_resource_file(app_client, core_client, './service.yaml')



def configure_submodules():
    subprocess.run(['git', 'submodule', 'init'])
    subprocess.run(['git', 'submodule', 'foreach', 'git', 'pull'])
    subprocess.run(['git', 'submodule', 'update', '--init'])
    subprocess.run(['git', 'submodule', 'foreach', 'git', 'clean', '-df'])
    subprocess.run(['git', 'submodule', 'foreach', 'git', 'reset', 'HEAD', '--hard'])

if __name__ == '__main__':

    config.load_kube_config()
    app_client = client.AppsV1Api()
    core_client = client.CoreV1Api()

    configure_submodules()
    os.makedirs('./log', exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel('INFO')
    file_handler = logging.FileHandler('log/nobel-task.log')
    console_handler = logging.StreamHandler()
    console_handler.setLevel('INFO')
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.info(os.environ)

    args = set(map(lambda arg: arg.lower(), sys.argv[1:]))

    if 'clean' in args:
        clean(app_client, core_client)

    if 'deploy' in args:
        deploy(app_client, core_client)
