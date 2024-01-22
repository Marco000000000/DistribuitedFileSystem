# script.py

import time
from kubernetes import client, config
import requests
def createUploadManager():
    deploymentName="uploadcontroller-deployment"
    namespace="dafault"
    update_replicas(deploymentName,-1,namespace)
    return

def createDownloadManager():
    deploymentName="download-controller-deployment"
    namespace="dafault"
    update_replicas(deploymentName,-1,namespace)
    return


def createFileSystem():
    # deploymentName="filesystem-deployment"
    # namespace="dafault"
    # update_replicas(deploymentName,-1,namespace)
    namespace = "default"
    deployment_name = "filesystem-deployment"
    image = "distribuitedfilesystem-filesystem1:latest"
    replicas = 2
    create_deployment(namespace, deployment_name, image, replicas)
    return
def create_deployment(namespace, deployment_name, image, replicas):
    # Load the Kubernetes configuration
    config.load_incluster_config()  # Load in-cluster config
    configuration = client.Configuration()
    #configuration.assert_hostname = False
    configuration.verify_ssl = False
    configuration.api_key["authorization"] = "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IndYRXlyeGFIV2xBZk14RG5BV2xFdjRBNkpxWUs4RmQ0Y09qTEtXZFdsdTgifQ.eyJhdWQiOlsiaHR0cHM6Ly9rdWJlcm5ldGVzLmRlZmF1bHQuc3ZjLmNsdXN0ZXIubG9jYWwiXSwiZXhwIjoxNzA1OTQ5NTQxLCJpYXQiOjE3MDU5NDU5NDEsImlzcyI6Imh0dHBzOi8va3ViZXJuZXRlcy5kZWZhdWx0LnN2Yy5jbHVzdGVyLmxvY2FsIiwia3ViZXJuZXRlcy5pbyI6eyJuYW1lc3BhY2UiOiJkZWZhdWx0Iiwic2VydmljZWFjY291bnQiOnsibmFtZSI6InNjYWxlciIsInVpZCI6IjAxMDFkOTM0LTkyOWItNDFlOS04YWY5LTNiYzdiZDRiMzBmMyJ9fSwibmJmIjoxNzA1OTQ1OTQxLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6ZGVmYXVsdDpzY2FsZXIifQ.EhSTXz-j-DlaXUDY32qBaHku2sYecskoZj43IW2e95311e5lW4vjX6yBMsCMhT1P23P9noKCC9sChbqrW_2tRHAiwpHb0x6XMTGtZCkc_ZDIQMJ_Ielx6QzNrVSOcfuU1oMBlg1MrXLgaCLHl2hu9Nb6S40y0ZnK7JtbFykalLIK1pD1HnGn0IdSMWQdL2rWyX1uDiD0K238MtY7F4_L4LYNS0W3E_TepQgh7jPy1Ez8IhxqQn8B5gP2r-RzLbRLCPbg7c0HxMVTZgrSXbudDJzZpYDHpnI3Nx4C78GdH9UCnGC2j5ZgkZbec7htlz8DnSuTON4ItedYywZnBsCJzg"

    # Create an instance of the AppsV1Api using the custom Configuration
    apps_api = client.AppsV1Api(client.ApiClient(configuration))

    # Define the deployment spec
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name=deployment_name),
        spec=client.V1DeploymentSpec(
            replicas=replicas,
            selector=client.V1LabelSelector(
                match_labels={"app": deployment_name}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": deployment_name}),
                spec=client.V1PodSpec(
                    containers=[client.V1Container(name=deployment_name, image=image, image_pull_policy="Never")]
                ),
            ),
        ),
    )

    # Create the deployment
    apps_api.create_namespaced_deployment(namespace, deployment)
def update_replicas(deployment_name, new_replica_count, namespace):
    config.load_incluster_config()  # Load in-cluster config

    api_instance = client.AppsV1Api()

    # Get the deployment
    deployment = api_instance.read_namespaced_deployment(
        name=deployment_name,
        namespace=namespace
    )

    # Update the replicas field
    if new_replica_count==-1:
        deployment.spec.replicas=deployment.spec.replicas+1
    else:
        deployment.spec.replicas = new_replica_count

    # Apply the changes
    api_instance.replace_namespaced_deployment(
        name=deployment_name,
        namespace=namespace,
        body=deployment
    )
    print(f"Replicas for '{deployment_name}' set to {new_replica_count}.") 
def update_prometheus_config():
    config.load_incluster_config()

    v1_config_maps = client.CoreV1Api()

    # Update Prometheus ConfigMap
    config_map_prometheus = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": "prometheus-config"},
        "data": {
            "prometheus.yml": "your-updated-prometheus-config",
        }
    }
    v1_config_maps.replace_namespaced_config_map(name="prometheus-config", namespace="default", body=config_map_prometheus)

    # Send a signal to Prometheus to reload configuration
    # This might involve using Prometheus's API or other mechanisms depending on your Prometheus setup
    # Below is a generic example, and you need to adapt it based on your Prometheus deployment

    # Replace 'prometheus-service' and '9090' with your Prometheus service name and port
    prometheus_url = "http://prometheus-service:9090/-/reload"

    try:
        response = requests.post(prometheus_url, timeout=5)
        response.raise_for_status()
        print("Prometheus configuration reloaded successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error reloading Prometheus configuration: {str(e)}")

if __name__ == "__main__":
    time.sleep(10)
    createFileSystem()
    createUploadManager()
    createDownloadManager()
