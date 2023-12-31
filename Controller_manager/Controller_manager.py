from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import Consumer, Producer, KafkaException, KafkaError
import mysql.connector
import sys
import json
import logging
#Fare gestore dei controller F
#	- Creare topic iniziali (CFirstCall(nome, tipo = download, upload), CFirstCallAck(nome, topics))
#	- Leggere dal db se ci sono topic dati a controller
#	- Dare tutti i topic al controller di upload ( quello di aggiornamento )
#	- Creazione topic di aggiornamento per I controller di upload
#	- Vede se ci sono filesystem con topic senza un controller e glielo ritorna
conf = {'bootstrap.servers': 'kafka:9092',
        'group.id': 'manager',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False}

consumer = Consumer(conf)

def produceJson(topicName,dictionaryData):#funzione per produrre un singolo Json su un topic
    p=Producer({'bootstrap.servers':'kafka:9092'})
    m=json.dumps(dictionaryData)
    p.poll(1)
    p.produce(topicName, m.encode('utf-8'),callback=receipt)

def receipt(err,msg):
    if err is not None:
        print('Error: {}'.format(err))
    else:
        message = 'Prodotto un messaggio sul topic {} con il valore {}\n'.format(msg.topic(), msg.value().decode('utf-8'))
        logger.info(message)
        print(message)


def consumeJson(topicName,groupId):#consuma un singolo json su un topic e in un gruppo
    c=Consumer({'bootstrap.servers':'kafka:9092','group.id':groupId,'auto.offset.reset':'earliest', 'enable.auto.commit': False}) # Qui l'enable.auto.commit è settato a True di default, l'ho messo a False
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
            
def register_controller(consumer):
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
            data = json.loads(msg)
            break
    return data
            
logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename='producer.log',
                    filemode='w')

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Instanziazione dell'oggetto AdminClient per le operazioni di creazione dei topic
admin = AdminClient({'bootstrap.servers': 'kafka:9092'})

# Creazione "hard-coded" dei topic "CFirstCall" e "CFirstCallAck
admin.create_topics([NewTopic("CFirstCall", num_partitions=1, replication_factor=1), NewTopic("CFirstCallAck", num_partitions=1, replication_factor=1),NewTopic("UpdateTopics", num_partitions=1, replication_factor=1)])

if __name__ == "main":
    try:
            # Connessione al database
            db = mysql.connector.connect(
                host = "mysql",
                database = "ds_filesystem",
                user = "root",
                password = "giovanni",
                port = 3307
            )

    except mysql.connector.Error as err:
        print("Failed to connect to database {}".format(err))
        exit(1)
    cursor = db.cursor()
    topics=[]
    oldTopics=[]
    while len(topics)==0:
        cursor.execute("SELECT DISTINCT topic FROM partitions")
        topics=cursor.fetchall()
        oldTopics=len(topics)
    consumer.subscribe("CFirstCall")
    while True:
        
        cursor.execute("SELECT DISTINCT topic FROM partitions")
        topics=cursor.fetchall()
        
        if len(topics)!=oldTopics:
             produceJson("UpdateTopics",topics)
        
        
        data = register_controller(consumer)
        if data is None:
            continue
        if data["type"]=="Upload":
            cursor.execute("INSERT INTO controller (controller_name, type) VALUES (%s, %s)", (data["Host"], data["Type"]))
            cursor.execute("select id_controller FROM controller where controller_name=%s and type=%s",(data["Host"], data["Type"]))
            id=cursor.fetchone()[0]
            for topic in topics:
                cursor.execute("INSERT INTO controllertopic (id_controller, topic) VALUES (%s, %s)", (id, topic))
            produceJson("CFirstCallAck",{"id":id, "Host":data["Host"],"topics":topics})
            db.commit()
            consumer.commit()
            continue
        elif data["type"]=="Download":
            # Recupero topic per download
            cursor.execute("SELECT min(topic) FROM partitions where topic not in (Select topic from controllertopic)")

            min_topic = cursor.fetchone()[0]
            if not cursor.rowcount:
                # Se non ci sono partizioni assegna il valore 0
                cursor.execute("SELECT MIN(mycount) FROM (SELECT topic,COUNT(topic) as mycount FROM controllertopic GROUP BY topic);")
                min_topic=cursor.fetchone()[0]

            cursor.execute("INSERT INTO controller (controller_name, type) VALUES (%s, %s)", (data["Host"], data["Type"]))
            cursor.execute("select id_controller from controller where controller_name=%s and type=%s",(data["Host"], data["Type"]))
            id=cursor.fetchone()[0]
            cursor.execute("INSERT INTO controllertopic (id_controller, topic) VALUES (%s, %s)", (id, min_topic))

            produceJson("CFirstCallAck",{"id":id, "Host":data["Host"],"topics":min_topic})
            db.commit()
            consumer.commit()

