from kubernetes import client, config
import random
import string
import time
import logging
from prometheus_api_client import PrometheusConnect
from flask import Flask, jsonify, request

app = Flask(__name__)

prometheus_url = "http://prometheus-service:9090"
prometheus = PrometheusConnect(url=prometheus_url, disable_ssl=True)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
def get_random_string(length):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str

def create_deployment(api_instance, deployment_name, container_image, replicas):
    # Define the deployment manifest
    for i in range(5):
            
        try:
            deployment_manifest = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": deployment_name+get_random_string(20)},
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
            break
        except:
            time.sleep(2)
            print("Probabilmente ha preso un nome uguale")
            continue
   
            

def createFileSystem():
    # Load in-cluster Kubernetes configuration
    config.load_incluster_config()
    image="distribuitedfilesystem-filesystem1:latest"
    name="filesystem-deployment"
    # Create the Kubernetes API client
    api_instance = client.AppsV1Api()

 # Create the initial deployment
    create_deployment(api_instance, name, image, 1)
    print("creato un "+name)
    #logger.info("creato un "+name)

def createDownloadManager():
    # Load in-cluster Kubernetes configuration
    config.load_incluster_config()
    image="distribuitedfilesystem-download_controller1:latest"
    name="download-controller-deployment"
    # Create the Kubernetes API client
    api_instance = client.AppsV1Api()

    # Create the initial deployment
    create_deployment(api_instance, name, image, 1)
    print("creato un "+name)
    #logger.info("creato un "+name)

def createUploadManager():
    # Load in-cluster Kubernetes configuration
    config.load_incluster_config()
    image="distribuitedfilesystem-uploadcontroller:latest"
    name="uploadcontroller-deployment"
    # Create the Kubernetes API client
    api_instance = client.AppsV1Api()

  # Create the initial deployment
    create_deployment(api_instance, name, image, 1)
    print("creato un "+name)
    #logger.info("creato un "+name)

# Sezione recupero metriche da prometheus

# Queries possibili per il download
# download_file_latency_query = 'download_file_latency_seconds'
# download_file_throughput_query = 'download_file_throughput_bytes'

@app.route('/query', methods=['GET'])
def query_prometheus():
    query = request.args.get('query', '')
    aggregate = request.args.get('aggregate', 'false').lower() == 'true'

    try:
        if aggregate:
            result = prometheus.custom_query_range(query, end_time='now')
        else:
            result = prometheus.custom_query(query)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, threaded=True)
    # time.sleep(100)
    # createDownloadManager()
    # createFileSystem()
    # #createUploadManager()
    # while True:
    #     time.sleep(20)
    