# script.py

from kubernetes import client, config
import requests
def createUploadManager():
    return
def create_pod_and_service():
    config.load_incluster_config()

    v1 = client.CoreV1Api()
    v1_services = client.CoreV1Api()
    v1_config_maps = client.CoreV1Api()

    # Create Pod
    pod_manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "my-pod"},
        "spec": {
            "containers": [
                {
                    "name": "nginx-container",
                    "image": "nginx",
                    "volumeMounts": [
                        {
                            "name": "nginx-config",
                            "mountPath": "/etc/nginx/conf.d",
                        }
                    ]
                }
            ],
            "volumes": [
                {
                    "name": "nginx-config",
                    "configMap": {
                        "name": "nginx-config-map",
                    }
                }
            ]
        },
    }
    v1.create_namespaced_pod(body=pod_manifest, namespace="default")

    # Create Service
    service_manifest = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": "my-service"},
        "spec": {
            "selector": {"app": "my-pod"},
            "ports": [{"protocol": "TCP", "port": 80, "targetPort": 80}]
        },
    }
    v1_services.create_namespaced_service(body=service_manifest, namespace="default")

    # Update Nginx ConfigMap
    config_map_nginx = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": "nginx-config-map"},
        "data": {
            "nginx.conf": "your-updated-nginx-config",
        }
    }
    v1_config_maps.replace_namespaced_config_map(name="nginx-config-map", namespace="default", body=config_map_nginx)

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
    create_pod_and_service()
    update_prometheus_config()
