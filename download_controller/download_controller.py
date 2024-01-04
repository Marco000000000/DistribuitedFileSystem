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
from time import sleep
import logging
from flask import Flask, Response
import mysql.connector
from werkzeug.utils import secure_filename

# Variabili globali
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'rar', 'zip', 'mp3'}



returnTopic=""
# Instanzio l'applicazione Flask
app = Flask(__name__)


# Configurazione logger
logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename='download_manager.log',
                    filemode='w')
logger = logging.getLogger('download_manager')
logger.setLevel(logging.INFO)


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

db = mysql_custom_connect(db_conf)

cursor=db.cursor()

# Produzione json su un topic
def produceJson(topic, dictionaryData):
    print("a")
    p = Producer({'bootstrap.servers': 'kafka:9093'})
    
    m = json.dumps(dictionaryData)
    print(m)
    p.poll(1)
    p.produce(topic, m.encode('utf-8'), callback=receipt)
    p.flush() # Serve per attendere la ricezione di tutti i messaggi
    

def consumeJsonFirstCall(topicName,groupId):#consuma un singolo json su un topic e in un gruppo controllando il codice
    c=Consumer({'bootstrap.servers':'kafka:9093','group.id':groupId,'auto.offset.reset':'earliest', 'enable.auto.commit': False}) # Ho settato l'auto commit a False
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
                if data["Host"]!=groupId:
                    continue
                c.commit()
                c.unsubscribe()
                return data
            
# Consuma json da un consumer di un dato gruppo (solo per first_Call())
def consumeJson(topicName, groupId):
    c = Consumer({'bootstrap.servers': 'kafka:9093', 'group.id': groupId, 'auto.offset.reset': 'earliest', 'enable.auto.commit': False})
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
                c.unsubscribe()
                c.close()
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
          "Type":"Download"}
    print(data)
    produceJson("CFirstCall",data)
    aList=consumeJsonFirstCall("CFirstCallAck",name)
    #format per Federico ->jsonStr = '{"cose":"a caso","topics":[1, 2,3, 4]}'
    return name

def generate_data(topics,filename):
    # Generazione dati per il download
    
    count=0
    consumer=[]
    i=0
    for topic in topics:
        consumer[i]=Consumer({'bootstrap.servers': 'kafka:9093', 'group.id': 'download', 'auto.offset.reset': 'earliest', 'enable.auto.commit': False})
        consumer[i].subscribe([returnTopic+str(topic)])
        i=i+1
    
    temp_vet={}
    cond=True
    while cond:
        i=0
        for cons in consumer:
            if(temp_vet.has_key(i)):
                continue
            msg=cons.poll(1.0)
            if msg is None:
                continue
            elif msg.error():
                print('Error: {}'.format(msg.error()))
                continue
            else:
                data=json.loads(msg.value().decode('utf-8'))
                print(data)
                if data["filename"] != filename:
                    cons.commit()
                    continue
                if data["count"]!=count:
                    cons.commit()
                    continue
                if data["last"] == True:
                    for temp in temp_vet:
                        yield temp
                    cond=False
                temp_vet[i]=base64.b64decode(data["data"])
                cons.commit()
            i=i+1
        if len(temp_vet)==len(topics):
            count=count+1
            for temp in temp_vet:
                yield temp
            temp_vet.clear() 
    for topic in topics:
        consumer[i].unsubscribe()           



# Endpoint per il download di un file (filename è il nome del file)
@app.route("/download/<path:filename>", methods=['GET'])
# Gestione di un file in download
def download_file(filename):
    print(filename[:99])
    if not allowed_file(filename):
        return {"error":"File extension not allowed!", "HTTP_status_code:": 400}
    elif filename is None:
        return {"error":"Missing filename!", "HTTP_status_code:": 400}
    else:
        print("dentro")
        # Controllo se il file è presente nel database
        
        cursor.execute("SELECT file_name,ready FROM files where file_name= %s",(filename[:99],))
        
        if cursor.rowcount:
            print("dentroif")
            # Se il file è presente nel database, controllo se è pronto per il download
            if cursor.fetchone()[1] == False:
                return {"error":"File not ready for download!", "HTTP_status_code:": 400}
            data = {
                "fileName" : secure_filename(filename[:99]),
                "returnTopic":returnTopic
            }
            print(data)
            cursor.execute("select distinct topic from partitions join files on partition_id=id where file_name=%s",(filename[:99],))
            topics=cursor.fetchall()
            unpacked_list = [item[0] for item in topics]
            for topic in unpacked_list:
                produceJson("Request" + str(topic), data)

            return Response(generate_data(unpacked_list,data["fileName"]), mimetype='application/octet-stream')
        else:
            return {"error":"File not found!", "HTTP_status_code:": 400}

c = Consumer({'bootstrap.servers': 'kafka:9093', 'group.id': 'download', 'auto.offset.reset': 'earliest', 'enable.auto.commit': False})
if __name__ == "__main__":
    # Ricezione topics necessari per il download
    returnTopic = first_Call()
    while returnTopic+str(1) not in c.list_topics().topics:
        print("in attesa del manager")
        sleep(0.2)

    hostname = socket.getfqdn()
    print(socket.gethostbyname_ex(hostname))
    app.run(debug=False,host=socket.gethostbyname_ex(hostname)[2][0],port=80)
    