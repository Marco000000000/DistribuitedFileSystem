from kubernetes import client, config
import random
import string
import time
import logging
import mysql.connector
from datetime import datetime, timedelta
import json
from prometheus_api_client import PrometheusConnect
from flask import Flask, jsonify, request

app = Flask(__name__)

# Dizionario per tenere traccia delle regole di QoS
sla_rules = {}

prometheus_url = "http://prometheus-service:9090"
prometheus = PrometheusConnect(url=prometheus_url, disable_ssl=True)
max_desired_latency=4.5
min_desired_throughput=5000000
lastLatency=0
lastThroughput=0
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
   
db_conf = {
            'host':'db',
            'port':3306,
            'database':'ds_filesystem',
            'user':'root',
            'password':'giovanni'
            }

def mysql_custom_connect(conf):
    while True:
        try:

            db = mysql.connector.connect(**conf)

            if db.is_connected():
                print("Connected to MySQL database")
                return db
        except mysql.connector.Error as err:
            print("Something went wrong: {}".format(err))
        
        print("Trying again...")
        time.sleep(5)           

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
        
def valueQuery(query,allowed_queries,ranged_query,aggregation,start_time,end_time,step,rate_interval):
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
# Queries possibili per il download
# download_file_latency_query = 'download_file_latency_seconds'
# download_file_throughput_query = 'download_file_throughput_bytes'

@app.route('/query', methods=['GET'])
def query_prometheus():
    type = request.args.get('type', '')

    query = request.args.get('query', '')
    ranged_query = request.args.get('range', 'false').lower() == 'true'
    start_time = request.args.get('start', '1')
    interval_value=int(start_time)
    start_time ="now-"+start_time+"h"
    end_time = request.args.get('end', 'now')
    step = request.args.get('step', '15s')
    aggregation = request.args.get('aggregation', '').lower()
    rate_interval = request.args.get('rate_interval', '5m')
    
    allowed_queries = ['download_file_latency_seconds', 'download_file_throughput_bytes']
    
    if type=="value":
        return valueQuery(query,allowed_queries,ranged_query,aggregation,start_time,end_time,step,rate_interval)

    elif type=="desired_value":
        if query == allowed_queries[0]:
            return jsonify({"desidered_"+query: max_desired_latency}), 200
        elif query== allowed_queries[1]:
            return jsonify({"desidered_"+query: min_desired_throughput}), 200

    elif type== "violation":

        time_interval = timedelta(hours=interval_value)
        start_time = datetime.utcnow() - time_interval
        

        if query == allowed_queries[0]:
            if interval_value <=0:
                return jsonify({"is_violating": lastLatency>max_desired_latency}), 200
            cursor.execute("SELECT count(id_metric) from metrics where metric_name = %s and metric_value > %s and created_at > %s",(query,max_desired_latency,start_time)) 
        elif query== allowed_queries[1]:
            if interval_value <=0:
                return jsonify({"is_violating": lastThroughput>min_desired_throughput}), 200
            cursor.execute("SELECT count(id_metric) from metrics where metric_name = %s and metric_value < %s and created_at > %s",(query,min_desired_throughput,start_time)) 
        else:
            return jsonify({"error": "Invalid query"}), 400

        count=cursor.fetchone()[0]

        return jsonify({"violations": count}), 200
    elif type=="all_data":
        if query == allowed_queries[0]:
            cursor.execute("SELECT * from metrics where metric_name = %s",(query,))
    
        elif query== allowed_queries[1]:
            cursor.execute("SELECT * from metrics where metric_name = %s",(query,))

        topics_temp=cursor.fetchall()
        unpacked_list_temp = [item[0] for item in topics_temp] 
        return json.dumps(unpacked_list_temp)

    elif type== "violation_probability":
        pass
    else:
        return jsonify({"error": "Invalid type"}), 400
    

def predictLatencyMinute(current_latency,minute):
    return False
def predictThroughputMinute(current_throughput,minute):
    return False

db = mysql_custom_connect(db_conf)

cursor=db.cursor()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, threaded=True)
    # time.sleep(100)
    # createDownloadManager()
    # createFileSystem()
    # #createUploadManager()
    # while True:
    #     time.sleep(20)
    while True:
        current_throughput=10000000000000
        current_latency=0
        throughputList = prometheus.custom_query("download_file_throughput_bytes")
        latencyList = prometheus.custom_query("download_file_latency_seconds")
        for i in range (latencyList):

            tempThroughput=throughputList[i]["value"][1]
            tempLatency=throughputList[i]["value"][1]
            if tempLatency>current_latency:
                current_latency=tempLatency
            if tempThroughput<current_throughput:
                current_throughput=tempThroughput

        if lastLatency!= current_latency:
            cursor.execute("INSERT INTO metrics (metric_name, metric_value) VALUES (%s,  %s)", ("download_file_latency_seconds", current_latency))
            lastLatency=current_latency
            db.commit()
            if current_latency<max_desired_latency and predictLatencyMinute(current_latency,1):
                createDownloadManager()
        if lastThroughput!= current_throughput:
            cursor.execute("INSERT INTO metrics (metric_name, metric_value) VALUES (%s,  %s)", ("download_file_latency_seconds", current_latency))
            lastThroughput=current_throughput
            db.commit()
            if current_throughput<min_desired_throughput and predictThroughputMinute(current_throughput,1):
                createFileSystem()#Sarebbe anche necessario aggiornare il limite al numero di partizioni

        time.sleep(1)    
