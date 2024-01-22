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
    config.load_kube_config()

    # Create a Kubernetes API client
    apps_api = client.AppsV1Api()

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
