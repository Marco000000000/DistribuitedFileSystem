from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import Consumer, Producer, KafkaException, KafkaError
import mysql.connector
import sys
import json
from time import sleep
import logging
#Fare gestore dei controller F
#	- Creare topic iniziali (CFirstCall(nome, tipo = download, upload), CFirstCallAck(nome, topics))
#	- Leggere dal db se ci sono topic dati a controller
#	- Dare tutti i topic al controller di upload ( quello di aggiornamento )
#	- Creazione topic di aggiornamento per I controller di upload
#	- Vede se ci sono filesystem con topic senza un controller e glielo ritorna
conf = {'bootstrap.servers': 'kafka-service:9093',
        'group.id': 'manager',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False}

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


def produceJson(topicName,dictionaryData):#funzione per produrre un singolo Json su un topic
    p=Producer({'bootstrap.servers':'kafka-service:9093'})
    m=json.dumps(dictionaryData)
    p.poll(1)
    p.produce(topicName, m.encode('utf-8'),callback=receipt)
    p.flush()
def receipt(err,msg):
    if err is not None:
        print('Error: {}'.format(err))
    else:
        message = 'Prodotto un messaggio sul topic {} con il valore {}\n'.format(msg.topic(), msg.value().decode('utf-8'))
        logger.info(message)
        print(message)


def consumeJson(topicName,groupId):#consuma un singolo json su un topic e in un gruppo
    c=Consumer({'bootstrap.servers':'kafka-service:9093','group.id':groupId,'auto.offset.reset':'earliest', 'enable.auto.commit': False}) # Qui l'enable.auto.commit è settato a True di default, l'ho messo a False
    c.subscribe([topicName])
    while True:
            msg=c.poll(1.0) #timeout
            if msg is None:
                continue
            elif msg.error():
                print('Error: {}'.format(msg.error()))
                continue
            else:
                data=json.loads(msg.value().decode('utf-8'))
                c.commit() # è necessario fare il commit? Perché l'auto commit è settato a True (Non lo capisco io, è una domanda tranquillo Marco xD)
                c.close()
                c.unsubscribe()
                return data
topics=[]
oldTopics=[]         
def register_controller(consumer,oldTopics):
    while True:
        msg = consumer.poll(timeout=1.0)
        if msg is None: 
            data=None
            break  
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                # Evento "end of partition"
                sys.stderr.write('%% %s [%d] reached end at offset %d\n' %
                                (msg.topic(), msg.partition(), msg.offset()))
            elif msg.error():
                raise KafkaException(msg.error())
        else:
            cursor.execute("SELECT DISTINCT topic FROM partitions")
            topics=cursor.fetchall()
            print("tupletopics",topics)
            if len(topics)!=oldTopics:
                produceJson("UpdateTopics",topics)
                oldTopics=len(topics)

            unpacked_list = [item[0] for item in topics]
            topics=unpacked_list
            data = json.loads(msg.value().decode('utf-8'))
            return data
    
            
logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename='producer.log',
                    filemode='w')

logger = logging.getLogger()
logger.setLevel(logging.INFO)
print("consumer")
consumer = Consumer(conf)
logger.info("prima dell'admin consumer creato")
print("admin")
def updateTopics():
    produceJson("UpdateTopics",topics)
    cursor.execute("Select controller_name from controller ;")
    controllers=cursor.fetchall()
    unpacked_list = [item[0] for item in controllers]
    for controller in unpacked_list:
        for i in (topics):
            print(controller+str(i))
            try:
                admin.create_topics([NewTopic(controller+str(i), num_partitions=1, replication_factor=1)],validate_only=False)
            except:
                pass

# Instanziazione dell'oggetto AdminClient per le operazioni di creazione dei topic
admin = AdminClient({'bootstrap.servers': 'kafka-service:9093'})

# Creazione "hard-coded" dei topic "CFirstCall" e "CFirstCallAck
admin.create_topics([NewTopic("CFirstCall", num_partitions=1, replication_factor=1), NewTopic("CFirstCallAck", num_partitions=1, replication_factor=1),NewTopic("UpdateTopics", num_partitions=1, replication_factor=1)])

if __name__ == "__main__":
    print("main")

    db_conf = {
            'host':'db',
            'port':3306,
            'database':'ds_filesystem',
            'user':'root',
            'password':'giovanni'
            }

    db = mysql_custom_connect(db_conf)

    cursor=db.cursor(buffered=True)

    while len(topics)==0:
        db.commit()
        cursor.execute("SELECT DISTINCT topic FROM partitions")
        fetch=cursor.fetchall()
        if len(fetch) > 0:
            topics=fetch[0]
            print("topics",topics)
            oldTopics=len(topics)
        sleep(1)
    consumer.subscribe(["CFirstCall"])
    while True:
        db.commit()
        cursor.execute("SELECT DISTINCT topic FROM partitions")
        topics=cursor.fetchall()
        print("tupletopics",topics)
        if len(topics)!=oldTopics:
            updateTopics()
            oldTopics=len(topics)

        unpacked_list = [item[0] for item in topics]
        topics=unpacked_list
        print("listtopics",topics)
        
        data = register_controller(consumer,oldTopics)
        if data is None:
            continue
        print(data["Host"])
        #restituisce i topic dati all'host
        
        if data["Type"]=="Upload":
            cursor.execute("SELECT Distinct topic from controllertopic join controller on (controller.id_controller=controllertopic.id_controller) where controller_name=%s ;",(data["Host"],))
            topics_temp=cursor.fetchall()
            print(topics_temp)
            unpacked_list_temp = [item[0] for item in topics_temp]
            topics_temp=unpacked_list_temp
            print(topics_temp)

            if len(topics_temp)>0:
                cursor.execute("select id_controller FROM controller where controller_name=%s ;",(data["Host"],))
                id=cursor.fetchone()[0] 
                produceJson("CFirstCallAck",{"id":id, "Host":data["Host"],"topics":topics_temp})
                if len(topics_temp) != len(topics):
                    updateTopics()
                continue
            admin.create_topics([NewTopic(data["Host"], num_partitions=1, replication_factor=1)],validate_only=False)

            
            cursor.execute("INSERT INTO controller (controller_name, cType) VALUES (%s, %s)", (data["Host"], data["Type"]))
            cursor.execute("select id_controller FROM controller where controller_name=%s and cType=%s",(data["Host"], data["Type"]))
            id=cursor.fetchone()[0]

            for num in unpacked_list:
                print(num)
                cursor.execute("INSERT INTO controllertopic (id_controller, topic) VALUES (%s, %s)", (id, num))
            

            produceJson("CFirstCallAck",{"id":id, "Host":data["Host"],"topics":topics})
            db.commit()
            consumer.commit()
            continue
        elif data["Type"]=="Download":

            cursor.execute("SELECT id_controller from controller where controller_name=%s ;",(data["Host"],))
            
            if cursor.rowcount:
                id=cursor.fetchone()[0]
                updateTopics()
                pass
            else:
                # Recupero topic per download
                for i in (topics):
                    data["Host"]+str(i)
                    try:
                        print(data["Host"]+str(i))
                        admin.create_topics([NewTopic(data["Host"]+str(i), num_partitions=1, replication_factor=3)],validate_only=False)
                    except:
                        pass
                cursor.execute("INSERT INTO controller (controller_name, cType) VALUES (%s, %s)", (data["Host"], data["Type"]))
                cursor.execute("select id_controller from controller where controller_name=%s and cType=%s",(data["Host"], data["Type"]))
                id=cursor.fetchone()[0]
            
            produceJson("CFirstCallAck",{"id":id, "Host":data["Host"]})
            db.commit()
            consumer.commit()

