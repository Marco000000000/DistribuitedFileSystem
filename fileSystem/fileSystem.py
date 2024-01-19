import os
from werkzeug.utils import secure_filename
from confluent_kafka import Producer
from confluent_kafka import Consumer
import logging
import json
import base64 #si potrebbe passare a base85
import random
import time
import string
from socket import gethostname

PARTITION_GRANULARITY=os.getenv("PARTITION_GRANULARITY", default = 131072)
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", default = 'downloadable')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'rar', 'zip', 'mp3'}
FILESYSTEM_DIMENSION=os.getenv("FILESYSTEM_DIMENSION", default = 100)#Mb

#creazione di una stringa random 
def get_random_string(length):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str

logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename='producer.log',
                    filemode='w')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)



# Logging e Stampa dei messaggi prodotti (Callback)
def receipt(err,msg):
    if err is not None:
        print('Error: {}'.format(err))
    else:
        message = 'Prodotto un messaggio sul topic {} con il valore {}\n'.format(msg.topic(), msg.value().decode('utf-8'))
        logger.info(message)
        print(message)

#check per le estensioni permesse
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS




#Invio di un file spezzato con la granularità predefinita
def download_file(filename,returnTopic,code):
    #prima coppia di producer-consumer
    p=Producer({'bootstrap.servers':'kafka-service:9093'})
    topicName=returnTopic
    if filename is not None and  allowed_file(filename):
        directory = os.path.join( UPLOAD_FOLDER,filename)
        index=0
        try:
            with open(directory, "rb") as f:
                while (byte := f.read(PARTITION_GRANULARITY)):
                    
                    data={
                    
                    "code":code,
                    "data":str(base64.b64encode(byte),"UTF-8"),
                    "last":False,
                    "count":index,
                    "filename":filename,
                    }
                    m=json.dumps(data)
                    index=index+1
                    p.poll(0.001)
                    p.produce(topicName, m.encode('utf-8'),callback=receipt)
                    p.flush()
                else:
                    data={
                        "code":code,
                        "filename":filename,
                        "last":True
                        }
                    m=json.dumps(data)
                    p.poll(1)
                    p.produce(topicName, m.encode('utf-8'),callback=receipt)
                    p.flush()
                return
        except FileNotFoundError as e:
                data={"filename":filename,
                        "code":code,

                        "last":True
                        }
                m=json.dumps(data)
                p.poll(1)
                p.produce(topicName, m.encode('utf-8'),callback=receipt)
                p.flush()
def produceJson(topicName,dictionaryData):
    p=Producer({'bootstrap.servers':'kafka-service:9093'})
    m=json.dumps(dictionaryData)
    p.poll(1)
    p.produce(topicName, m.encode('utf-8'),callback=receipt)
    p.flush()

def update_file(filename,pack):
    directory = os.path.join( UPLOAD_FOLDER,filename)
    file = base64.b64decode(pack["data"])

    with open(directory, "ab+") as f:
        f.write(file)
#upload di un singolo pacchetto di dati 
def upload_file(filename,pack):
    directory = os.path.join( UPLOAD_FOLDER,filename)
    if(pack["last"]==True):
        data={"commit":True}
        produceJson(pack["returnTopic"],data)
        return

    file = base64.b64decode(pack["data"])

    with open(directory, "ab+") as f:
        f.write(file)

#Chiamata per la registrazione nei topic kafka
def first_Call():
    p=Producer({'bootstrap.servers':'kafka-service:9093'})
    data={"Code":gethostname(),
          "Dim":FILESYSTEM_DIMENSION}
    m=json.dumps(data)
    p.poll(1)
    p.produce('FirstCall', m.encode('utf-8'),callback=receipt)
    p.flush()
    print(m)
    c.subscribe(['FirstCallAck'])
    code=data["Code"]
    while True:
            msg=c.poll(1.0) #timeout
            print(msg)
            if msg is None:
                continue
            elif msg.error():
                print('Error: {}'.format(msg.error()))
                continue
            else:
                data=json.loads(msg.value().decode('utf-8'))
                print(data)
                if(data["Code"]!=code):
                    c.commit()
                    continue
                
                break
    c.commit()        
    
    c.unsubscribe()
    
    return data["id"],data["Topic"]


def updateLocalFiles(id,topicNumber):
    p=Producer({'bootstrap.servers':'kafka-service:9093'})
    data={"id":id,
          "topic":topicNumber}
    m=json.dumps(data)
    p.poll(1)
    p.produce('UpdateRequest', m.encode('utf-8'),callback=receipt)
    p.flush()
    while True:
        msgUpdate=updateConsumer.poll(0.001)

        if msgUpdate is None:
                    pass
        elif msgUpdate.error():
            print('Error: {}'.format(msg.error()))
            pass
        else:
            data=json.loads(msgUpdate.value().decode('utf-8'))
            if data["id"]!=id:
                continue
            print(data["fileName"])
            if data["last"]==True:
                updateConsumer.commit()

                break
            if data["fileName"]!="":
                if not os.path.exists(UPLOAD_FOLDER):
                    os.makedirs(UPLOAD_FOLDER)
                update_file(secure_filename(data["fileName"]),data)
                updateConsumer.commit()
            
             
    
    updateConsumer.unsubscribe()
#eliminazione file 
def delete_file(filename):
    if os.path.exists(os.path.join( UPLOAD_FOLDER,filename)):
        os.remove(os.path.join( UPLOAD_FOLDER,filename))

c=Consumer({'bootstrap.servers':'kafka-service:9093','group.id':get_random_string(20),'auto.offset.reset':'latest','enable.auto.commit': False})
updateConsumer=Consumer({'bootstrap.servers':'kafka-service:9093','group.id':"1",'auto.offset.reset':'latest','enable.auto.commit': False})
updateConsumer.subscribe(["UpdateDownload"])
if __name__== "__main__":

    while "FirstCall" not in c.list_topics().topics or "FirstCallAck" not in c.list_topics().topics:
        print("in attesa del manager")
        time.sleep(0.2)
    id,topicNumber=first_Call() #ricezione dati necessari per la ricezione
    print(id,topicNumber)
    
    updateLocalFiles(id,topicNumber)
    
    
    
    while "Upload"+str(topicNumber) not in c.list_topics().topics:
        print("in attesa del manager")
        time.sleep(0.2)

    uploadConsumer=Consumer({'bootstrap.servers':'kafka-service:9093','group.id':str(id),'auto.offset.reset':'earliest','enable.auto.commit': False})

    uploadConsumer.subscribe(["Upload"+str(topicNumber)])
    requestConsumer=Consumer({'bootstrap.servers':'kafka-service:9093','group.id':"000",'auto.offset.reset':'earliest','enable.auto.commit': False})
    requestConsumer.subscribe(["Request"+str(topicNumber)])#forse il commit deve essere fatto dopo ma attenzione ai messaggi ripetuti
    deleteConsumer=Consumer({'bootstrap.servers':'kafka-service:9093','group.id':"000",'auto.offset.reset':'earliest','enable.auto.commit': False})
    deleteConsumer.subscribe(["Delete"+str(topicNumber)])
    print("ho fatto l'inizio")


    while True:
        msg=requestConsumer.poll(0.001)
        msgUpload=uploadConsumer.poll(0.001)
        msgDelete=deleteConsumer.poll(0.001)
        if msg is None:
            pass
        elif msg.error():
            print('Error: {}'.format(msg.error()))
            pass
        else:

            data=json.loads(msg.value().decode('utf-8'))
            if data["fileName"]!="":
                download_file(secure_filename(data["fileName"]),data["returnTopic"],data["code"])
                requestConsumer.commit()


        if msgUpload is None:
            pass
        elif msgUpload.error():
            print('Error: {}'.format(msg.error()))
            pass
        else:
            data=json.loads(msgUpload.value().decode('utf-8'))
            print(data["fileName"])
            if data["fileName"]!="":
                if not os.path.exists(UPLOAD_FOLDER):
                    os.makedirs(UPLOAD_FOLDER)
                upload_file(secure_filename(data["fileName"]),data)
                uploadConsumer.commit()


        if msgDelete is None:
            continue
        elif msgDelete.error():
            print('Error: {}'.format(msg.error()))
            continue
        else:
            data=json.loads(msgDelete.value().decode('utf-8'))
            print(data)

            if data["fileName"]!="":
                delete_file(secure_filename(data["fileName"]))   
                deleteConsumer.commit()