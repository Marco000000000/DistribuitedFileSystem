from kubernetes import client, config

def create_deployment(api_instance, deployment_name, container_image, replicas):
    # Define the deployment manifest
    deployment_manifest = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": deployment_name},
        "spec": {
            "replicas": replicas,
            "selector": {
                "matchLabels": {"app": deployment_name}
            },
            "template": {
                "metadata": {"labels": {"app": deployment_name}},
                "spec": {
                    "containers": [
                        {
                            "name": deployment_name,
                            "image": container_image,
                            "imagePullPolicy": "Never"
                        }
                    ]
                }
            }
        }
    }

    # Create the deployment
    api_instance.create_namespaced_deployment(
        body=deployment_manifest,
        namespace="default"
    )
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
    deploymentName="filesystem-deployment"
    namespace="dafault"
    update_replicas(deploymentName,-1,namespace)
    return

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

def main():
    # Load in-cluster Kubernetes configuration
    createFileSystem()
    config.load_incluster_config()

    # Create the Kubernetes API client
    api_instance = client.AppsV1Api()

    # Create the initial deployment
    create_deployment(api_instance, "filesystem22", "distribuitedfilesystem-filesystem1:latest", 1)
    while True:
        print("CREATOOOOOOOOOOOOOOOO!")

    print("Parent deployment created.")

if __name__ == "__main__":
    main()
