import time
from kubernetes import client, config
import sys
import docker
import os
import logging
import yaml
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

    # don't stop things that don't belong to us.
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
        logger.warning("tore down nobel deployment with errors " + ','.join(errors))
    else:
        logger.info("successfully tore down nobel deployment")


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

def deploy(
        app_client, core_client
):
    docker_client = docker.from_env()

    for image_name, filename in \
            [(filename[len('Dockerfile'):], filename) for filename in os.listdir('.') if
             filename.startswith('Dockerfile')]:
        logger.info('building docker image: ' + image_name)
        try:
            docker_client.images.build(path='.', dockerfile=filename, tag='nobel-search',nocache=True)
        except Exception as e:
            logger.fatal(f'docker image build for {image_name} failed: {str(e)}')
            return
        logger.info(f'successfully built {image_name}')

    namespace = client.V1Namespace(
        metadata=client.V1ObjectMeta(name='nobel')
    )

    if not 'nobel' in [item.metadata.name for item in core_client.list_namespace().items]:
        core_client.create_namespace(namespace)

    _process_resource_file(app_client, core_client, './secrets.yaml')
    _process_resource_file(app_client, core_client, './persistence.yaml')
    _process_resource_file(app_client, core_client, './deployment.yaml')
    _process_resource_file(app_client, core_client, './service.yaml')
    time.sleep(30)


def forward(core_client):

    pod_list = [
            item.metadata.name for item in core_client.list_namespaced_pod('nobel', label_selector='app=search').items
    ]

    if not len(pod_list) >= 1:
        logger.error('could not find any web service pods')
        return

    logger.info(f'forwarding port on {pod_list[0]}')
    subprocess.run(
        ['sudo', '-E', 'kubectl', 'port-forward', '--address','0.0.0.0', pod_list[0], '80:80', '-n', 'nobel']
    )

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
    console_handler = logging.StreamHandler()
    console_handler.setLevel('INFO')
    logger.addHandler(console_handler)

    args = set(map(lambda arg: arg.lower(), sys.argv[1:]))

    if 'clean' in args:
        clean(app_client, core_client)

    if 'deploy' in args:
        deploy(app_client, core_client)

    if 'forward' in args:
        forward(core_client)
