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
            'host':'localhost',
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

cursor=db.cursor(buffered=True)

# Produzione json su un topic
def produceJson(topic, dictionaryData):
    print("a")
    p = Producer({'bootstrap.servers': 'localhost:9092'})
    
    m = json.dumps(dictionaryData)
    print(m)
    p.poll(1)
    p.produce(topic, m.encode('utf-8'), callback=receipt)
    p.flush() # Serve per attendere la ricezione di tutti i messaggi
    

def consumeJsonFirstCall(topicName,groupId):#consuma un singolo json su un topic e in un gruppo controllando il codice
    c=Consumer({'bootstrap.servers':'localhost:9092','group.id':groupId,'auto.offset.reset':'earliest', 'enable.auto.commit': False}) # Ho settato l'auto commit a False
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

def generate_data(topics,filename,code,consumer):
    # Generazione dati per il download
    
    count=0
    
    
    temp_vet={}
    cond=True
    while cond:
        i=0
        for e in consumer:
            cons=consumer[e]
            print(temp_vet.keys())

            if(i  in temp_vet):
                i=i+1
                continue
            msg=cons.poll(0.001)
            if msg is None:
                continue
            elif msg.error():
                print('Error: {}'.format(msg.error()))
                continue
            else:
                data=json.loads(msg.value().decode('utf-8'))
                if data["filename"] != filename or data["code"] != code:
                    cons.commit()
                    continue
                if data["last"] == True:
                    temp_vet[i]=""
                    cond=False
                    cons.commit()
                else:                    
                    temp_vet[i]=base64.b64decode(data["data"])
                    cons.commit()
                print(temp_vet.keys())
            i=i+1
        if len(temp_vet)==len(topics):
            count=count+1
            for temp in temp_vet:
                print(len(temp_vet[temp]))
                yield temp_vet[temp]
            temp_vet.clear() 
    for topic in topics:
        consumer[str(topic)].unsubscribe() 



# Endpoint per il download di un file (filename è il nome del file)
@app.route("/download/<path:filename>", methods=['GET'])
# Gestione di un file in download
def download_file(filename):
    print(filename)
    if len(filename) > 99:
        # Truncate the filename if it's longer than 99 characters
        filename = filename[:99]
    if not allowed_file(filename):
        return {"error":"File extension not allowed!", "HTTP_status_code:": 400}
    elif filename is None:
        return {"error":"Missing filename!", "HTTP_status_code:": 400}
    else:
        print("dentro")
        # Controllo se il file è presente nel database
        print(filename)
        db.commit()
        cursor.execute("SELECT file_name,ready FROM files where file_name= %s",(filename,))
        cond=False
        try:
            cond=cursor.fetchone()[1]
        except:
            return {"error":"File not found!", "HTTP_status_code:": 400}

        if cond:
            print("dentroif")
            # Se il file è presente nel database, controllo se è pronto per il download
            if cond == False:
                return {"error":"File not ready for download!", "HTTP_status_code:": 400}
            data = {
                "fileName" : secure_filename(filename),
                "returnTopic":returnTopic
            }
            print(data)
            cursor.execute("select distinct topic from partitions join files on partition_id=id where file_name=%s",(filename,))
            topics=cursor.fetchall()
            unpacked_list = [item[0] for item in topics]
            code=get_random_string(10)
            consumer={}
            for topic in unpacked_list:
                data = {
                "fileName" : secure_filename(filename),
                "returnTopic":returnTopic+str(topic),
                "code":code
                }

    
                consumer[str(topic)]=Consumer({'bootstrap.servers': 'localhost:9092', 'group.id': get_random_string(10), 'auto.offset.reset': 'latest', 'enable.auto.commit': False})
                consumer[str(topic)].subscribe([returnTopic+str(topic)])

                sleep(5)
                produceJson("Request" + str(topic), data)

            return Response(generate_data(unpacked_list,data["fileName"],code,consumer), mimetype='application/octet-stream')
        else:
            return {"error":"File not ready for download!", "HTTP_status_code:": 400}


c = Consumer({'bootstrap.servers': 'localhost:9092', 'group.id': 'download', 'auto.offset.reset': 'earliest', 'enable.auto.commit': False})
if __name__ == "__main__":
    # Ricezione topics necessari per il download
    returnTopic = first_Call()
    while returnTopic+"1" not in c.list_topics().topics:
        print("in attesa del manager")
        sleep(0.2)

    hostname = socket.gethostname()
    print(hostname)
    print(socket.gethostbyname_ex(hostname))
    app.run(debug=True,port=80)
    