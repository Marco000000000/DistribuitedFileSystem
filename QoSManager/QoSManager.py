from kubernetes import client, config
import yaml

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

def main():
    # Load in-cluster Kubernetes configuration
    config.load_kube_config()

    # Create the Kubernetes API client
    api_instance = client.AppsV1Api()

    # Create the initial deployment
    create_deployment(api_instance, "filesystem", "distribuitedfilesystem-filesystem1:latest", 1)

    print("Parent deployment created.")

if __name__ == "__main__":
    main()
