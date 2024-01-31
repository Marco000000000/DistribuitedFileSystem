import threading
from kubernetes import client, config
import random
import string
import time
import logging
import mysql.connector
from datetime import datetime, timedelta
import json
from prometheus_api_client import PrometheusConnect
from circuitbreaker import circuit
from flask import Flask, jsonify, request
import numpy as np
import scipy.stats
import pickle
import time
import statsmodels
app = Flask(__name__)
limitTopic=2

# Dizionario per tenere traccia delle regole di QoS
sla_rules = {}

prometheus_url = "http://prometheus-service:9090"
prometheus = PrometheusConnect(url=prometheus_url, disable_ssl=True)
max_desired_latency=7
min_desired_throughput=1000000
lastLatency=0
lastThroughput=0
predictionTime=2
MAXLIMITOPIC=5
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
            'password':'password'
            }
def fallback():
    time.sleep(1)
    print("Lissening on open Circuit")
    return None


@circuit(failure_threshold=5, recovery_timeout=30,fallback_function=fallback)
def mysql_custom_connect(conf):
    db = mysql.connector.connect(**conf)

    if db.is_connected():
        print("Connected to MySQL database")
        return db
    

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
@app.route("/limitTopic",methods=['GET'])
def getLimitTopic():
    return jsonify({"limitTopic":limitTopic})
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
                        if query==allowed_queries[0]:
                            print(result)
                            for i in range(len(result)):
                                result[i]["isViolating"]=float(result[i]["value"][1])>max_desired_latency
                                    
                        elif query==allowed_queries[1]:
                            for i in range(len(result)):
                                result[i]["isViolating"]=float(result[i]["value"][1])<min_desired_throughput
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
    elif type=="discover":
        return jsonify({"allowed_queries": allowed_queries}), 200
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
        else:
            return jsonify({"error": "Invalid query"}), 400
        topics_temp=cursor.fetchall()
        unpacked_list_temp=[]
        print(topics_temp)
        for item in topics_temp:
            print(item)
            item=list(item)
            item[3]=str(item[3])
            unpacked_list_temp.append(item)
        print(unpacked_list_temp) 
        return json.dumps(unpacked_list_temp)

    elif type== "violation_probability":
        minute=interval_value
        if query == allowed_queries[0]:
            combined_probability,combined_probability_max,meanValuePredicted=predictLatencyMinute(interval_value,max_desired_latency)
            threshold = 8
            print(f"Probability of exceeding 1 time '{threshold} second' of latency in {minute} minute: {combined_probability*100:.6f}%")
            print(f"Max instant Probability of exceeding {threshold} second of latency in {minute} minute: {combined_probability_max*100:.6f}%")
            print(f"Mean value predicted in {minute} minute: {meanValuePredicted:.2f} s")
            return jsonify({"p_at_least_once": combined_probability,"max_instant_p":combined_probability_max,"mean_value_predicted":meanValuePredicted}), 200
        elif query== allowed_queries[1]:
            
            combined_probability,combined_probability_max,meanValuePredicted=predictThroughputMinute(interval_value,min_desired_throughput)
            threshold = 3
            print(f"Probability of subceeding 1 time '{threshold} MB/s' of throughput in {minute} minute: {combined_probability*100:.6f}%")
            print(f"Max instant Probability of subceeding '{threshold} MB/s' of throughput in {minute} minute: {combined_probability_max*100:.6f}%")
            print(f"Mean value predicted in {minute} minute: {meanValuePredicted/1000000:.2f} MB/s")
            return jsonify({"p_at_least_once": combined_probability,"max_instant_p":combined_probability_max,"mean_value_predicted":meanValuePredicted}), 200

    else:
        return jsonify({"error": "Invalid type"}), 400
    

def predictLatencyMinute(minute,threshold):
    fiveSecondFromMinute=minute*12
    # Make predictions using the loaded model
    prediction_time=int((time.time()-startTime)/5)
    print(prediction_time)
    mutex.acquire()
    try:
        mean_pred = mean_Latency_model.predict(prediction_time,prediction_time+fiveSecondFromMinute)
        std_dev_pred = std_Latency_model.predict(prediction_time, prediction_time+fiveSecondFromMinute)
    finally:
        mutex.release()
    # Define threshold and time interval


    # Calculate cumulative probabilities for each time step within the interval
    cumulative_probabilities = []
    for mean, std_dev in zip(mean_pred[:], std_dev_pred[:]):
        probability = scipy.stats.norm.cdf(threshold, loc=mean, scale=std_dev)
        cumulative_probabilities.append(probability)

    print(cumulative_probabilities)
    cumulative_probabilities=np.array(cumulative_probabilities)
    cumulative_probabilities = cumulative_probabilities[~np.isnan(cumulative_probabilities)]

    # Combine probabilities (e.g., take the maximum)
    combined_probability =1- np.prod(cumulative_probabilities)
    combined_probability_max=np.max(1-cumulative_probabilities)
    meanValuePredicted=np.mean(mean_pred)
    return combined_probability,combined_probability_max,meanValuePredicted
def predictThroughputMinute(minute,threshold):
    fiveSecondFromMinute=minute*12
    # Make predictions using the loaded model
    prediction_time=int((time.time()-startTime)/5)
    print(prediction_time)
    mutex.acquire()
    try:
        mean_pred = mean_Throughput_model.predict(prediction_time,prediction_time+fiveSecondFromMinute)
        std_dev_pred = std_Throughput_model.predict(prediction_time, prediction_time+fiveSecondFromMinute)
    finally:
        mutex.release()
    # Define threshold and time interval


    # Calculate cumulative probabilities for each time step within the interval
    cumulative_probabilities = []
    for mean, std_dev in zip(mean_pred[:], std_dev_pred[:]):
        probability =1- scipy.stats.norm.cdf(threshold, loc=mean, scale=std_dev)
        cumulative_probabilities.append(probability)

    print(cumulative_probabilities)
    cumulative_probabilities=np.array(cumulative_probabilities)
    cumulative_probabilities = cumulative_probabilities[~np.isnan(cumulative_probabilities)]

    # Combine probabilities (e.g., take the maximum)
    combined_probability =1- np.prod(cumulative_probabilities)
    combined_probability_max=np.max(1-cumulative_probabilities)
    meanValuePredicted=np.mean(mean_pred)
    return combined_probability,combined_probability_max,meanValuePredicted


while True:
    try:
        db = mysql_custom_connect(db_conf)
        break
    except:
        continue
mutex = threading.Lock()

cursor=db.cursor()
learningTimer=time.time()

def onlineLearning():
    metrics = ['download_file_latency_seconds', 'download_file_throughput_bytes']

    if  time.time()-learningTimer>3600:


        time_interval = timedelta(hours=1)
        start_time = datetime.utcnow() - time_interval
        cursor.execute("SELECT * from metrics where metric_name = %s and created_at > %s",(metrics[0],start_time))
        data=cursor.fetchall()
        unpacked_list_temp=[]
        print(data)
        for item in data:
            print(item)
            item=list(item)
            item[3]=str(item[3])
            unpacked_list_temp.append(item)
        data=unpacked_list_temp
        finalData=datetime.strptime(data[-1][3], '%Y-%m-%d %H:%M:%S')
        firstData=datetime.strptime(data[0][3], '%Y-%m-%d %H:%M:%S')

        finalSeconds= finalData.total_seconds()
        firstSeconds= firstData.total_seconds()
        #tsr.json
        samples=int((finalSeconds-firstSeconds)/5)
        step=5 #secondi
        index=0
        data1=[]
        print(samples,finalSeconds,firstSeconds)
        for value in range(0, samples*5, 5):
            tempData=datetime.strptime(data[index][3], '%Y-%m-%d %H:%M:%S')
            tempSeconds= tempData.total_seconds()
            data1.append([data[index][2]])
            if(tempSeconds-firstSeconds<=value):
                index+=1

        std=[]
        mean=[]
        times=100
        step=5

        print((len(data1)-times))
        for i in range(len(data1)-times):
            std.append([str(step*i),np.std(data1[i:i+times])])
            mean.append([str(step*i),np.mean(data1[i:i+times])])




        mean_train=np.array(mean)
        std_train=np.array(std)
        temp_mean_Latency=statsmodels.api.tsa.ARIMA(mean_train,order=mean_Latency_model.order())
        temp_std_Latency=statsmodels.api.tsa.ARIMA(std_train,order=std_Latency_model.order())
        temp_mean_Latency.fit()
        temp_std_Latency.fit()
   

        cursor.execute("SELECT * from metrics where metric_name = %s and created_at > %s",(metrics[1],start_time))
        data=cursor.fetchall()
        unpacked_list_temp=[]
        print(data)
        for item in data:
            print(item)
            item=list(item)
            item[3]=str(item[3])
            unpacked_list_temp.append(item)
        data=unpacked_list_temp

        finalData=datetime.strptime(data[-1][3], '%Y-%m-%d %H:%M:%S')
        firstData=datetime.strptime(data[0][3], '%Y-%m-%d %H:%M:%S')

        finalSeconds= finalData.total_seconds()
        firstSeconds= firstData.total_seconds()
        #tsr.json
        samples=int((finalSeconds-firstSeconds)/5)
        step=5 #secondi
        index=0
        data1=[]
        print(samples,finalSeconds,firstSeconds)
        for value in range(0, samples*5, 5):
            tempData=datetime.strptime(data[index][3], '%Y-%m-%d %H:%M:%S')
            tempSeconds= tempData.total_seconds()
            data1.append([data[index][2]])
            if(tempSeconds-firstSeconds<=value):
                index+=1

        std=[]
        mean=[]
        times=100
        step=5

        print((len(data1)-times))
        for i in range(len(data1)-times):
            std.append([str(step*i),np.std(data1[i:i+times])])
            mean.append([str(step*i),np.mean(data1[i:i+times])])




        mean_train=np.array(mean)
        std_train=np.array(std)
        temp_mean_Throughput=statsmodels.api.tsa.ARIMA(mean_train,order=mean_Throughput_model.order())
        temp_std_Throughput=statsmodels.api.tsa.ARIMA(std_train,order=std_Throughput_model.order())
        temp_mean_Throughput.fit()
        temp_std_Throughput.fit()
        
        global startTime
        mutex.acquire()
        try:
            mean_Throughput_model=temp_mean_Throughput
            std_Throughput_model = temp_std_Throughput
            mean_Latency_model = temp_mean_Latency
            std_Latency_model = temp_std_Latency
            startTime=time.time()-(len(data1)-times)*5
        finally:
            mutex.release() 
    
        learningTimer=time.time()
    time.sleep(600)
    
def mysql_updater():
    global lastThroughput
    global lastLatency
    

    while True:
        cursor=db.cursor()
        current_throughput=10000000000000
        current_latency=0
        throughputList = prometheus.custom_query("download_file_throughput_bytes")
        latencyList = prometheus.custom_query("download_file_latency_seconds")
        print(throughputList)
        print(latencyList)
        logger.info(throughputList)
        logger.info(latencyList)
        for i in range (len(throughputList)):
            tempThroughput=float(throughputList[i]["value"][1])
            if tempThroughput<current_throughput or current_throughput==0:
                current_throughput=tempThroughput
        for i in range(len(latencyList)):
            tempLatency=float(latencyList[i]["value"][1])
            if tempLatency>current_latency:
                current_latency=tempLatency
            
        print(lastThroughput)
        print(current_throughput)
        if lastLatency!= current_latency:
            if(current_latency<=0 or current_latency>30):
                time.sleep(1)
                continue
            cursor.execute("INSERT INTO metrics (metric_name, metric_value) VALUES (%s,  %s)", ("download_file_latency_seconds", current_latency))
            lastLatency=current_latency
            db.commit()
            if predictLatencyMinute(predictionTime,max_desired_latency)[2]>max_desired_latency and False:#inibita per mancanza di risorse locali
                if time.time()-latencyTime>600:
                    createDownloadManager()
                    latencyTime=time.time()
        if lastThroughput!= current_throughput:
            if(current_latency<=0 ):
                time.sleep(1)
                continue
            cursor.execute("INSERT INTO metrics (metric_name, metric_value) VALUES (%s,  %s)", ("download_file_throughput_bytes", current_throughput))
            lastThroughput=current_throughput
            db.commit()
            if predictThroughputMinute(predictionTime,min_desired_throughput)[2]<min_desired_throughput and False:#inibita per mancanza di risorse locali
                if time.time()-throughputTime>600:
                    if predictThroughputMinute(10,min_desired_throughput)[2]<min_desired_throughput and limitTopic<MAXLIMITOPIC:
                        limitTopic+=1
                    for i in range(limitTopic):
                        createFileSystem()
                    throughputTime=time.time()
        time.sleep(1)    
        cursor.close

startTime=time.time()
latencyTime=startTime
throughputTime=startTime
with open('mean_Throughput_model.pkl', 'rb') as file:
    mean_Throughput_model = pickle.load(file)
with open('std_Throughput_model.pkl', 'rb') as file:
    std_Throughput_model = pickle.load(file)
with open('mean_Latency_model.pkl', 'rb') as file:
    mean_Latency_model = pickle.load(file)
with open('std_Latency_model.pkl', 'rb') as file:
    std_Latency_model = pickle.load(file)
if __name__ == "__main__":
    thread1 = threading.Thread(target=mysql_updater)
    thread1.start()
    thread2= threading.Thread(target=onlineLearning)
    thread2.start()

    app.run(host='0.0.0.0', port=80, threaded=True)



