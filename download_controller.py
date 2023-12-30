# Fare controller download F
# 	- Produrre la richiesta file in uno o più topic
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
from flask import Flask, request
import os
import mysql.connector
import threading
import time
from werkzeug.utils import secure_filename

# Variabili globali
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
PARTITION_GRANULARITY=os.getenv("PARTITION_GRANULARITY", default = 1024)

topics = []
codes = []
retained_messages = []
threads = []


# Instanzio l'applicazione Flask
app = Flask(__name__)


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
finally:
    cursor = db.cursor()


# Produzione json su un topic
def produceJson(topic, dictionaryData):
    p = Producer({'bootstrap.servers': 'localhost:9092'})
    m = json.dumps(dictionaryData)
    p.poll(1)
    p.produce(topic, m.encode('utf-8'), callback=receipt)
    p.flush() # Serve per attendere la ricezione di tutti i messaggi
    p.close() 


# Consuma json da un consumer di un dato gruppo
def consumeJson(topicName, groupId):
    c = Consumer({'bootstrap.servers': 'localhost:9092', 'group.id': groupId, 'auto.offset.reset': 'earliest', 'enable.auto.commit': False})
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
                if data["Code"]!=groupId:
                    continue
                c.commit()
                c.close()
                c.unsubscribe()
                return data


# Creazione stringa random
def get_random_string(length): 
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


# Callback per la ricezione della richiesta
def receipt(err, msg):
    if err is not None:
        print('Error: {}'.format(err))
    else:
        message = 'Prodotto un messaggio sul topic {} con il valore {}\n'.format(msg.topic(), msg.value().decode('utf-8'))
        logger.info(message)
        print(message)

# Funzione per controllo estensioni file permesse
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def first_Call():#funzione per la ricezione di topic iniziali
    code=get_random_string(20)
    data={"Code":code,
          "Type":"upload"}
    produceJson("CFirstCall",data)
    aList=consumeJson("CFirstCallAck",code)
    #format per Federico ->jsonStr = '{"cose":"a caso","topics":[1, 2, 3, 4]}'

    return json.loads(aList)["topics"], json.loads(aList)["codes"]


# Endpoint per il download di un file (filename è il nome del file)
@app.route("/download/<path:filename>", methods=['GET'])
def start_download(filename):
    download_thread = threading.Thread(target=download_file, args=(filename,))
    threads.append(download_thread)
    
    download_thread.start()
    
    for thread in threads:
        thread.join()
    
# Gestione di un file in download
def download_file(filename):
    if allowed_file(filename) == False:
        return {"error":"File extension not allowed!", "HTTP_status_code:": 400}
    elif filename is None:
        return {"error":"Missing filename!", "HTTP_status_code:": 400}
    else:
        # Controllo se il file è presente nel database
        cursor.execute("SELECT file_name,ready FROM file where file_name= %s",(filename[:99]))
        if cursor.rowcount:
            # Se il file è presente nel database, controllo se è pronto per il download
            if cursor.fetchone()["ready"] == False:
                return {"error":"File not ready for download!", "HTTP_status_code:": 400}
            for topic, code in zip(topics, codes): # Per ogni topic e code
                data = {
                    "fileName" : secure_filename(filename[:99]),
                }
                produceJson("Request" + topic, data)
                retained_messages.append(consumeJson("Download" + topic, code)) # è giusto? Sia per il code che per l'append alla lista per ottenere il retain dei messaggi consumati
            return {"file":retained_messages, "HTTP_status_code:": 200}
        else:
            return {"error":"File not found!", "HTTP_status_code:": 400}


if __name__ == "__main__":
    # Ricezione dati necessari per il download
    topics, codes = first_Call()
    # TO-DO: Settare a True il parametro debug
    # TO-DO: Multithreading (Mi sembra che l'ho fatto totalmente)
    app.run(debug=True, port=5000)