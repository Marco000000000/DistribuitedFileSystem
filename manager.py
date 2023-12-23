from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import Consumer, Producer, KafkaException, KafkaError
import mysql.connector
import sys
import json
import logging

# Configurazione del producer e instanziazione
conf = {'bootstrap.servers': 'localhost:9092'}

producer = Producer(conf)

# Configurazione del consumer e instanziazione
conf = {'bootstrap.servers': 'localhost:9092',
        'group.id': 'manager',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False}

consumer = Consumer(conf)

# Funzione che elabora il messaggio ricevuto dal consumer
def register_filesystem(consumer, topic):
    try:
        consumer.subscribe(topic)

        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None: continue

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
    finally:
        # Chiude il consumer (non fa il commit se enalbe.auto.commit è settato a False)
        consumer.close()
        return data

# Configurazione del logger
logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename='producer.log',
                    filemode='w')

logger = logging.getLogger()
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
admin = AdminClient({'bootstrap.servers': 'localhost:9092'})

# Creazione "hard-coded" dei topic "FirstCall" e "FirstCallAck
admin.create_topics([NewTopic("FirstCall", num_partitions=1, replication_factor=1), NewTopic("FirstCallAck", num_partitions=1, replication_factor=1)])


# Prima di decommentare questa funzione, bisogna vedere se create topics sovrascrive i topic già esistenti
# ritorna True se il topic esite, False altrimenti
# def topic_exists(admin, topic):
#     metadata = admin.list_topics()
#     for t in iter(metadata.topics.values()):
#         if t.topic == topic:
#             return True
#     return False

if __name__ == "main":
    try:
            # Connessione al database
            db = mysql.connector.connect(
                host = "localhost",
                database = "ds_filesystem",
                user = "root",
                password = "giovanni",
                port = 3307
            )

    except mysql.connector.Error as err:
        print("Failed to connect to database {}".format(err))

    cursor = db.cursor()

    while True:
        # Recupero del numero di partizioni
        cursor.execute("SELECT MAX(topic) FROM partitions")

        max_topic = cursor.fetchone()[0]

        # Richiesta di registrazione da parte del filesystem + inserimento nel database della partizione
        data = register_filesystem(consumer, "FirstCall")

        if not cursor.rowcount:
            # Se non ci sono partizioni assegna il valore 0
            data["Topic"] = 0
        else:
            # Se ci sono partizioni assegna il valore massimo + 1
            data["Topic"] = max_topic + 1
        
        cursor.execute("INSERT INTO partitions (partition_name, used_space, topic) VALUES (%s, %s, %s)", (data["Code"], data["Dim"], data["Topic"]))

        db.commit()

        print("{} record inserted.".format(cursor.rowcount))

        cursor.execute("SELECT MAX(id) FROM partitions WHERE partition_name = %s", (data["Code"],))

        max_id = cursor.fetchone()[0]

        data["id"] = max_id

        producer.poll(1)
        producer.produce('FirstCallAck', json.dumps(data).encode('utf-8'), callback=receipt)

        cursor.close()#può essere sbagliato?
        db.close()