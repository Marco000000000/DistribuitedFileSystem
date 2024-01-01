# Fare controller download F
# 	- Produrre la richiesta file in uno o più topic
# 	- Consuma file di ritorno
# 	- Ritorna i file all'api gateway
# 	- Multithreading
# 	- Fornisce api per richiesta file
#   - Registrazione su NGINX
import json
from confluent_kafka import Producer, Consumer
import base64
import socket
import random
import string
import logging
from flask import Flask, Response
import mysql.connector
from werkzeug.utils import secure_filename

# Variabili globali
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

topics = []


# Instanzio l'applicazione Flask
app = Flask(__name__)


# Configurazione logger
logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename='download_manager.log',
                    filemode='w')
logger = logging.getLogger('download_manager')
logger.setLevel(logging.INFO)


db = mysql.connector.connect(
    host = "db",
    database = "ds_filesystem",
    user = "root",
    password = "giovanni",
    port = 3306
)

cursor=db.cursor()

# Produzione json su un topic
def produceJson(topic, dictionaryData):
    p = Producer({'bootstrap.servers': 'broker:29092'})
    m = json.dumps(dictionaryData)
    p.poll(1)
    p.produce(topic, m.encode('utf-8'), callback=receipt)
    p.flush() # Serve per attendere la ricezione di tutti i messaggi
    


# Consuma json da un consumer di un dato gruppo (solo per first_Call())
def consumeJson(topicName, groupId):
    c = Consumer({'bootstrap.servers': 'broker:29092', 'group.id': groupId, 'auto.offset.reset': 'earliest', 'enable.auto.commit': False})
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
                if data["Host"]!=groupId: # Funziona solo con la funzione first_Call() dato che "Host" coincide con groupId durante la first call di un download controller
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
    name=socket.gethostname()
    data={
          "Host":name,
          "Type":"upload"}
    produceJson("CFirstCall",data)
    aList=consumeJson("CFirstCallAck",name)
    #format per Federico ->jsonStr = '{"cose":"a caso","topics":[1, 2, 3, 4]}'

    return json.loads(aList)["topics"]

def generate_data(topics):
    # Generazione dati per il download
    c = Consumer({'bootstrap.servers': 'broker:29092', 'group.id': 'download', 'auto.offset.reset': 'earliest', 'enable.auto.commit': False})
    c.subscribe(["Download" + topics]) # Topics è solo uno effettivamente (il minimo tra i topics disponibili)
    while True:
            msg=c.poll(1.0)
            if msg is None:
                continue
            elif msg.error():
                print('Error: {}'.format(msg.error()))
                continue
            else:
                data=json.loads(msg.value().decode('utf-8'))
                yield base64.b64decode(data["data"])
                c.commit()
                if data["last"] == True:
                    c.close()
                    c.unsubscribe()
                    break      


# Endpoint per il download di un file (filename è il nome del file)
@app.route("/download/<path:filename>", methods=['GET'])
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
            data = {
                "fileName" : secure_filename(filename[:99]),
            }
            produceJson("Request" + topics, data)
            generate_data(topics)
            return Response(generate_data(topics), mimetype='application/octet-stream')
        else:
            return {"error":"File not found!", "HTTP_status_code:": 400}


if __name__ == "__main__":
    # Ricezione topics necessari per il download
    topics = first_Call()
    app.run(debug=False, port=5000)