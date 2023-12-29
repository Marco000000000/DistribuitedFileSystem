# Fare controller download F
# 	- Produrre la richiesta file in uno o più topic [FATTA]
# 	- Consuma file di ritorno (retain)
# 	- Ritorna i file all'api gateway
# 	- Multithreading
# 	- Fornisce api per richiesta file
#   - Registrazione su NGINX
import json
from confluent_kafka import Producer, Consumer
import base64
import random
import string
import logging
from flask import Flask
import os
import mysql.connector


ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
PARTITION_GRANULARITY=os.getenv("PARTITION_GRANULARITY", default = 1024)


# Configurazione logger
logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename='download_manager.log',
                    filemode='w')
logger = logging.getLogger('download_manager')
logger.setLevel(logging.INFO)


# Connessione al database
try:
    db = mysql.connector.connect(
        host = "localhost",
        database = "ds_filesystem",
        user = "root",
        password = "giovanni",
        port = 3307
    )
except mysql.connector.Error as err:
    print("Errore durante la connessione al database: {}".format(err))
    exit(1)


# Produzione json richiesta topics (topics è una lista di topic)
def produce_request_json(topics, dictionaryData): # dictionaryData dovrebbe essere sempre lo stesso per tutti i topic?
    p = Producer({'bootstrap.servers': 'localhost:9092'})
    m = json.dumps(dictionaryData)
    p.poll(1)
    for topic in topics:
        p.produce(topic, m.encode('utf-8'), callback=receipt)
    
    # In questo caso metto il flush alla fine per assicurarmi che tutti i messaggi siano stati prodotti
    p.flush()
    # Quindi chiudo il producer
    p.close() 


# Consuma json da un consumer di un dato gruppo (retain non so se l'ho fatto giusto)
def consumeJson(topicName, groupID):
    c = Consumer({'bootstrap.servers': 'localhost:9092', 'group.id': groupID, 'auto.offset.reset': 'earliest', 'enable.auto.commit': False})
    c.subscribe([topicName])
    while True:
        msg = c.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            continue
        else:
            return msg.value().decode('utf-8')

    
# callback per la ricezione della richiesta
def receipt(err, msg):
    if err is not None:
        print('Error: {}'.format(err))
    else:
        message = 'Prodotto un messaggio sul topic {} con il valore {}\n'.format(msg.topic(), msg.value().decode('utf-8'))
        logger.info(message)
        print(message)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS