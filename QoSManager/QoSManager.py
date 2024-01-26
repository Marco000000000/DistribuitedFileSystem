from kubernetes import client, config
import random
import string
import time
import logging
from prometheus_api_client import PrometheusConnect
from flask import Flask, jsonify, request

app = Flask(__name__)

# Dizionario per tenere traccia delle regole di QoS
sla_rules = {}

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
    config.load_incluster_config()
    image="distribuitedfilesystem-filesystem1:latest"
    name="filesystem-deployment"
    api_instance = client.AppsV1Api()

    create_deployment(api_instance, name, image, 1)
    print("creato un "+name)
    #logger.info("creato un "+name)

def createDownloadManager():
    config.load_incluster_config()
    image="distribuitedfilesystem-download_controller1:latest"
    name="download-controller-deployment"
    api_instance = client.AppsV1Api()

    create_deployment(api_instance, name, image, 1)
    print("creato un "+name)
    #logger.info("creato un "+name)

def createUploadManager():
    config.load_incluster_config()
    image="distribuitedfilesystem-uploadcontroller:latest"
    name="uploadcontroller-deployment"
    api_instance = client.AppsV1Api()

  # Create the initial deployment
    create_deployment(api_instance, name, image, 1)
    print("creato un "+name)
    #logger.info("creato un "+name)

# Sezione gestione SLA e Prometheus
@app.route('/update_sla_rule', methods=['POST'])
def update_sla_rule(sla_rule, sla_value = 0):
    # Ricevere questi dati non dai richieste http con gli altri nodi del sistema, ma con una lettura al database
    # Inoltre definire una range di valori ammissibili per la metrica ricevuta
    sla_rules[sla_rule]['current_value'] = sla_value
    #sla_rules[sla_rule]['threshold'] = 0 #Aggiungere campo threshold all'api update_sla_rule (dovrebbe essere lui il valore desidereto?)
    return jsonify({"message": "SLA rule updated successfully"}), 200
        

# Queries possibili per il download
# download_file_latency_query = 'download_file_latency_seconds'
# download_file_throughput_query = 'download_file_throughput_bytes'

@app.route('/query', methods=['GET'])
def query_prometheus():
    query = request.args.get('query', '')
    ranged_query = request.args.get('range', 'false').lower() == 'true'
    start_time = request.args.get('start', '1')
    start_time ="now-"+start_time+"h"
    end_time = request.args.get('end', 'now')
    step = request.args.get('step', '15s')
    aggregation = request.args.get('aggregation', '').lower()
    rate_interval = request.args.get('rate_interval', '5m')
    
    allowed_queries = ['download_file_latency_seconds', 'download_file_throughput_bytes']
    allowed_aggregations = ['avg', 'min', 'max', 'sum', 'count', 'stddev', 'stdvar', 'rate', '']
    
    try:
        if ranged_query:
            if query in allowed_queries:
                if aggregation in allowed_aggregations:
                    if aggregation == '':
                        result = prometheus.custom_query_range(query, start=start_time, end=end_time, step=step)
                    elif aggregation != 'rate':
                        result = prometheus.custom_query_range(f'{aggregation}({query})', start=start_time, end=end_time, step=step)
                    else:
                        result = prometheus.custom_query_range(f'{aggregation}({query}[{rate_interval}])', start=start_time, end=end_time, step=step)
                else:
                    return jsonify({"error": "Invalid aggregation"}), 400
            else:
                return jsonify({"error": "Invalid query"}), 400
        else:
            if query in allowed_queries:
                if aggregation in allowed_aggregations:
                    if aggregation == '':
                        result = prometheus.custom_query(query)
                    elif aggregation != 'rate':
                        result = prometheus.custom_query(f'{aggregation}({query})')
                    else:
                        result = prometheus.custom_query(f'{aggregation}({query}[{rate_interval}])')
                else:
                    return jsonify({"error": "Invalid aggregation"}), 400
            else:
                return jsonify({"error": "Invalid query"}), 400
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, threaded=True)
    # time.sleep(100)
    # createDownloadManager()
    # createFileSystem()
    # #createUploadManager()
    # while True:
    #     time.sleep(20)
    
