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
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
FILESYSTEM_DIMENSION=os.getenv("FILESYSTEM_DIMENSION", default = 100)#Mb

#creazione di una stringa random 
def get_random_string(length):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str
#prima coppia di producer-consumer
p=Producer({'bootstrap.servers':'kafka:9093'})
c=Consumer({'bootstrap.servers':'kafka:9093','group.id':get_random_string(20),'auto.offset.reset':'latest','enable.auto.commit': False})

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
def download_file(filename,topicNumber):
    topicName="Download"+str(topicNumber)
    if filename is not None and  allowed_file(filename):
        directory = os.path.join( UPLOAD_FOLDER,filename)
        index=0
        with open(directory, "rb") as f:
            while (byte := f.read(PARTITION_GRANULARITY)):
                
                data={
                
                "data":str(base64.b64encode(byte),"UTF-8"),
                "last":False
                }
                m=json.dumps(data)
                p.poll(1)
                p.produce(topicName, m.encode('utf-8'),callback=receipt)
            else:
                data={
                    "last":True
                    }
                m=json.dumps(data)
                p.poll(1)
                p.produce(topicName, m.encode('utf-8'),callback=receipt)
                p.flush()
            return
def produceJson(topicName,dictionaryData):
    p=Producer({'bootstrap.servers':'kafka:9093'})
    m=json.dumps(dictionaryData)
    p.poll(1)
    p.produce(topicName, m.encode('utf-8'),callback=receipt)
    p.flush()

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
    data={"Code":gethostname(),
          "Dim":FILESYSTEM_DIMENSION}
    m=json.dumps(data)
    p.poll(1)
    p.produce('FirstCall', m.encode('utf-8'),callback=receipt)
    print(m)
    code=data["Code"]
    while True:
            msg=c.poll(1.0) #timeout
            if msg is None:
                continue
            elif msg.error():
                print('Error: {}'.format(msg.error()))
                continue
            else:
                data=json.loads(msg.value().decode('utf-8'))
                if(data["Code"]!=code):
                    c.commit()
                    continue
                
                break
    c.commit()        
    
    c.unsubscribe()
    
    return data["id"],data["Topic"]
#eliminazione file 
def delete_file(filename):
    if os.path.exists(filename):
        os.remove(filename)

if __name__== "__main__":
    while "FirstCall" not in c.list_topics().topics or "FirstCallAck" not in c.list_topics().topics:
        print("in attesa del manager")
        time.sleep(0.2)
    c.subscribe(['FirstCallAck'])
    id,topicNumber=first_Call() #ricezione dati necessari per la ricezione
    print(id,topicNumber)
    while "Upload"+str(topicNumber) not in c.list_topics().topics:
        print("in attesa del manager")
        time.sleep(0.2)
        

    uploadConsumer=Consumer({'bootstrap.servers':'kafka:9093','group.id':str(id),'auto.offset.reset':'earliest','enable.auto.commit': False})

    uploadConsumer.subscribe(["Upload"+str(topicNumber)])
    requestConsumer=Consumer({'bootstrap.servers':'kafka:9093','group.id':"000",'auto.offset.reset':'earliest','enable.auto.commit': False})
    requestConsumer.subscribe(["Request"+str(topicNumber)])
    deleteConsumer=Consumer({'bootstrap.servers':'kafka:9093','group.id':"000",'auto.offset.reset':'earliest','enable.auto.commit': False})
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
                download_file(secure_filename(data["fileName"]),topicNumber)
                requestConsumer.commit()


        if msgUpload is None:
            pass
        elif msgUpload.error():
            print('Error: {}'.format(msg.error()))
            pass
        else:
            data=json.loads(msgUpload.value().decode('utf-8'))
            print(data)
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
            if data["fileName"]!="":
                delete_file(secure_filename(data["fileName"]))   
                deleteConsumer.commit()