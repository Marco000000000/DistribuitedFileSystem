from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import Consumer, Producer, KafkaException, KafkaError
import mysql.connector
from circuitbreaker import circuit
import sys
import json
import logging
from time import sleep
import string
import random
import logging
import requests 
# Configurazione del producer e instanziazione
prod_conf = {'bootstrap.servers': 'kafka-service:9093'}
# Configurazione logger
logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename='log.log',
                    filemode='w')
logger = logging.getLogger('download_manager')
logger.setLevel(logging.INFO)
producer = Producer(prod_conf)
def get_random_string(length):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str
# Configurazione del consumer e instanziazione
cons_conf = {'bootstrap.servers': 'kafka-service:9093',
        'group.id': get_random_string(4),
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False}

consumer = Consumer(cons_conf)
consumerIntermediate= Consumer(cons_conf)
limitTopic=3
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
        sleep(5)
def produceJson(topic, dictionaryData):
    print("a")
    p = Producer({'bootstrap.servers': 'kafka-service:9093'})
    
    m = json.dumps(dictionaryData)
    print(m)
    p.poll(0.01)
    p.produce(topic, m.encode('utf-8'), callback=receipt)
    p.flush() 

def discover(id,topic):
    db = mysql_custom_connect(db_conf)
    cursor=db.cursor(buffered=True)
    mysql_query = "SELECT distinct file_name FROM files WHERE ready=true;"
    cursor.execute(mysql_query)
    files=cursor.fetchall()
    print(files)
    if cursor.rowcount>0:
        unpacked_list = [item[0] for item in files]
        files={}
        for i in range(len(unpacked_list)):
            files[i]=unpacked_list[i]
        for i in files:
            code=get_random_string(10)
            control=files[i].split(".")
            if len(control)!=2:
                continue
            data={
                "fileName":files[i],
                "returnTopic":"UpdateIntermediate",
                "code":code
                }     
            produceJson(topic,data)
            count=0
            while True:
                msg=consumerIntermediate.poll(0.01)
                if msg is None:
                    continue
                elif msg.error():
                    print('Error: {}'.format(msg.error()))
                    continue
                else:
                    data=json.loads(msg.value().decode('utf-8'))
                    if data["filename"] != files[i] or data["code"] != code:
                        consumerIntermediate.commit()
                        continue
                    if data["last"] == True:
                        
                        consumerIntermediate.commit()
                        break
                    else:
                        data={
                        "fileName": files[i],
                        "data":data["data"],
                        "last":False, 
                        "count":count,
                        "id":id
                        }                    
                        count=count+1
                        produceJson("UpdateDownload",data)
                        consumerIntermediate.commit()
    data={
        
        "last":True, 
        "id":id
        }
    logger.info(data) 
    produceJson("UpdateDownload",data)
    cursor.close()
    db.close()    

@circuit(failure_threshold=5, recovery_timeout=30,fallback_function=discover)
def get_filenames(id, topic):
    try:
        logger.info("get_filenames")
        host="download-controller-service"
        response=requests.get("http://"+host+"/discover", timeout=5)
        logger.info("response")
        return response.json()
    except Exception as e:
        logging.info(f"Exception in get_filenames: {e}")
        raise e
# Funzione che elabora il messaggio ricevuto dal consumer
def UpdateFileOnTopic(id,topic):
    try:
        json_data = get_filenames(id, topic)
    except:
        discover(id,topic)
        return
    for i in json_data:
        code=get_random_string(10)
        control=json_data[i].split(".")
        if len(control)!=2:
            continue
        data={
            "fileName":json_data[i],
            "returnTopic":"UpdateIntermediate",
            "code":code
            }     
        produceJson(topic,data)
        count=0
        while True:
            msg=consumerIntermediate.poll(0.01)
            if msg is None:
                continue
            elif msg.error():
                print('Error: {}'.format(msg.error()))
                continue
            else:
                data=json.loads(msg.value().decode('utf-8'))
                if data["filename"] != json_data[i] or data["code"] != code:
                    consumerIntermediate.commit()
                    continue
                if data["last"] == True:
                    
                    consumerIntermediate.commit()
                    break
                else:
                    data={
                    "fileName": json_data[i],
                    "data":data["data"],
                    "last":False, 
                    "count":count,
                    "id":id
                    }                    
                    count=count+1
                    produceJson("UpdateDownload",data)
                    consumerIntermediate.commit()
    data={
            
            "last":True, 
            "id":id
            } 
    produceJson("UpdateDownload",data)




# Configurazione del logger
logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename='producer.log',
                    filemode='w')

logger = logging.getLogger('producer')
logger.setLevel(logging.INFO)

# Logging e Stampa dei messaggi prodotti (Callback)
def receipt(err,msg):
    if err is not None:
        print('Error: {}'.format(err))
    else:
        message = 'Prodotto un messaggio sul topic {} con il valore {}\n'.format(msg.topic(), msg.value().decode('utf-8'))
        logger.info(message)
        print(message)


# Instanziazione dell'oggetto AdminClient per le operazioni di creazione dei topic
admin = AdminClient({'bootstrap.servers': 'kafka-service:9093'})

# Creazione "hardcoded" dei topic "UpdateRequest" e "UpdateDownload"
hardcoded_topics = [NewTopic("UpdateRequest", num_partitions=1, replication_factor=1), NewTopic("UpdateDownload", num_partitions=1, replication_factor=1), NewTopic("UpdateIntermediate", num_partitions=1, replication_factor=1)]
admin.create_topics(hardcoded_topics)


# Prima di decommentare questa funzione, bisogna vedere se create topics sovrascrive i topic già esistenti
# ritorna True se il topic esite, False altrimenti
# def topic_exists(admin, topic):
#     metadata = admin.list_topics()
#     for t in iter(metadata.topics.values()):
#         if t.topic == topic:
#             return True
#     return False

if __name__ == "__main__":
    

    consumer.subscribe(["UpdateRequest"])
    consumerIntermediate.subscribe(["UpdateIntermediate"])
    while True:
        msg = consumer.poll(0.01)
        if msg is None: continue

        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                # Evento "end of partition"
                sys.stderr.write('%% %s [%d] ha raggiunto la fine dell\'offset %d\n' %
                                    (msg.topic(), msg.partition(), msg.offset()))
            elif msg.error():
                raise KafkaException(msg.error())
        else:
            data = json.loads(msg.value().decode('utf-8'))
            
            UpdateFileOnTopic(data["id"],"Request"+str(data["topic"]))
            consumer.commit()


   
 