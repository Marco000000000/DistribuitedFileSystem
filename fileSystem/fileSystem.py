import os
import threading
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
from circuitbreaker import circuit

PARTITION_GRANULARITY=os.getenv("PARTITION_GRANULARITY", default = 131072)
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", default = 'downloadable')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'rar', 'zip', 'mp3'}

def fallback():
    time.sleep(1)
    print("Lissening on open Circuit")
    return None

@circuit(failure_threshold=3, recovery_timeout=5,fallback_function=fallback)
def cir_subscribe(consumer, consumer_topics):
    consumer.subscribe(consumer_topics)

downloadingFiles=[]
mutex = threading.Lock()
uploadingFiles=[]
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
                    p.poll(0.01)
                    p.produce(topicName, m.encode('utf-8'))
                    p.flush()
                else:
                    data={
                        "code":code,
                        "filename":filename,
                        "last":True
                        }
                    m=json.dumps(data)
                    p.poll(0.01)
                    p.produce(topicName, m.encode('utf-8'),callback=receipt)
                    p.flush()
                return
        except FileNotFoundError as e:
                data={"filename":filename,
                        "code":code,

                        "last":True
                        }
                m=json.dumps(data)
                p.poll(0.01)
                p.produce(topicName, m.encode('utf-8'),callback=receipt)
                p.flush()
def produceJson(topicName,dictionaryData):
    p=Producer({'bootstrap.servers':'kafka-service:9093'})
    m=json.dumps(dictionaryData)
    p.poll(0.01)
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
    logger.info(filename)
    logger.info(pack["count"])
    file = base64.b64decode(pack["data"])

    with open(directory, "ab+") as f:
        f.write(file)

#Chiamata per la registrazione nei topic kafka
def first_Call():
    p=Producer({'bootstrap.servers':'kafka-service:9093'})
    data={"Code":gethostname()
          }
    m=json.dumps(data)
    p.poll(0.01)
    p.produce('FirstCall', m.encode('utf-8'),callback=receipt)
    p.flush()
    print(m)
    while True:
        try:
            cir_subscribe(c,['FirstCallAck'])
            break
        except:
            continue
    code=data["Code"]
    while True:
            msg=c.poll(0.01) #timeout
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
    p.poll(0.01)
    p.produce('UpdateRequest', m.encode('utf-8'),callback=receipt)
    p.flush()
    while True:
        msgUpdate=updateConsumer.poll(0.01)

        if msgUpdate is None:
                    pass
        elif msgUpdate.error():
            print('Error: {}'.format(msgUpdate.error()))
            pass
        else:
            data=json.loads(msgUpdate.value().decode('utf-8'))
            if data["id"]!=id:
                continue
            print(data)
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


def deleter(deleteConsumer):
    while True:
        msgDelete=deleteConsumer.poll(0.01)
        if msgDelete is None:
            pass
        elif msgDelete.error():
            print('Error: {}'.format(msgDelete.error()))
        else:
            data=json.loads(msgDelete.value().decode('utf-8'))
            print(data)

            if data["fileName"]!="":
                cond=True

                while cond:
                    mutex.acquire()

                    try:
                        # Access the shared resource
                        if data["fileName"] not in downloadingFiles:
                            cond=False
                            uploadingFiles.append(data["fileName"])
                    finally:
                        # Release the mutex to allow other threads to access the shared resource
                        mutex.release()
                        if (cond):
                            time.sleep(1)
                        
                delete_file(secure_filename(data["fileName"]))
                mutex.acquire()
                try:
                    # Access the shared resource
                    uploadingFiles.remove(data["fileName"])
                finally:
                    # Release the mutex to allow other threads to access the shared resource
                    mutex.release()   
                deleteConsumer.commit()
def downloadThreaded(data):
    cond=True
    while cond:
        mutex.acquire()

        try:
            # Access the shared resource
            if data["fileName"] not in uploadingFiles:
                downloadingFiles.append(data["fileName"])
                cond=False
        finally:
            # Release the mutex to allow other threads to access the shared resource
            mutex.release()
            if (cond):
                time.sleep(1)
        
    download_file(secure_filename(data["fileName"]),data["returnTopic"],data["code"])

    mutex.acquire()

    try:
        downloadingFiles.remove(data["fileName"])
    finally:
        # Release the mutex to allow other threads to access the shared resource
        mutex.release()
def downloader(requestConsumer):
    while True:
        msg=requestConsumer.poll(0.01)
        if msg is None:
            pass
        elif msg.error():
            print('Error: {}'.format(msg.error()))
            
        else:

            data=json.loads(msg.value().decode('utf-8'))
            if data["fileName"]!="":
                downloadThread = threading.Thread(target=downloadThreaded, args=(data,))
                downloadThread.start()
                requestConsumer.commit()
    
def uploader(uploadConsumer):
    while True:
        msgUpload=uploadConsumer.poll(0.01)
        if msgUpload is None:
            pass
        elif msgUpload.error():
            print('Error: {}'.format(msgUpload.error()))
            
        else:
            data=json.loads(msgUpload.value().decode('utf-8'))
            print(data["fileName"])
            if data["fileName"]!="":
                if not os.path.exists(UPLOAD_FOLDER):
                    os.makedirs(UPLOAD_FOLDER)
                cond=True

                while cond:
                    mutex.acquire()

                    try:
                        # Access the shared resource
                        if data["fileName"] not in downloadingFiles:
                            cond=False
                            uploadingFiles.append(data["fileName"])
                    finally:
                        # Release the mutex to allow other threads to access the shared resource
                        mutex.release()
                        if (cond):
                            time.sleep(1)
                logger.info(data["fileName"])

                upload_file(secure_filename(data["fileName"]),data)
                mutex.acquire()

                try:
                    # Access the shared resource
                    uploadingFiles.remove(data["fileName"])
                finally:
                    # Release the mutex to allow other threads to access the shared resource
                    mutex.release()
                uploadConsumer.commit()

c=Consumer({'bootstrap.servers':'kafka-service:9093','group.id':get_random_string(20),'auto.offset.reset':'latest','enable.auto.commit': False})
updateConsumer=Consumer({'bootstrap.servers':'kafka-service:9093','group.id':get_random_string(20),'auto.offset.reset':'earliest','enable.auto.commit': False})
while True:
        try:
            cir_subscribe(updateConsumer,['UpdateDownload'])
            break
        except:
            continue

if __name__== "__main__":

    while "FirstCall" not in c.list_topics().topics or "FirstCallAck" not in c.list_topics().topics:
        print("in attesa del manager")
        time.sleep(0.2)
    id,topicNumber=first_Call() #ricezione dati necessari per la ricezione
    print(id,topicNumber)


    updateLocalFiles(id,topicNumber)
    
    logger.info("Dopo l'update")

    
    while "Upload"+str(topicNumber) not in c.list_topics().topics:
        print("in attesa del manager")
        time.sleep(0.2)

    uploadConsumer=Consumer({'bootstrap.servers':'kafka-service:9093','group.id':str(id),'auto.offset.reset':'earliest','enable.auto.commit': False})
    while True:
        try:
            cir_subscribe(uploadConsumer,["Upload"+str(topicNumber)])
            break
        except:
            continue
    requestConsumer=Consumer({'bootstrap.servers':'kafka-service:9093','group.id':"000",'auto.offset.reset':'earliest','enable.auto.commit': False})
    while True:
        try:
            cir_subscribe(requestConsumer,["Request"+str(topicNumber)])
            break
        except:
            continue
    deleteConsumer=Consumer({'bootstrap.servers':'kafka-service:9093','group.id':"000",'auto.offset.reset':'earliest','enable.auto.commit': False})
    while True:
        try:
            cir_subscribe(deleteConsumer,["Delete"+str(topicNumber)])
            break
        except:
            continue
    print("ho fatto l'inizio")
    logger.info("ho fatto l'inizio")

    thread1 = threading.Thread(target=uploader, args=(uploadConsumer,))
    thread2 = threading.Thread(target=downloader, args=(requestConsumer,))
    thread3 = threading.Thread(target=deleter, args=(deleteConsumer,))

    # Start the threads
    thread1.start()
    thread2.start()
    thread3.start()

    # Wait for both threads to finish
    thread1.join()
    thread2.join()
    thread3.join()

        


        


        