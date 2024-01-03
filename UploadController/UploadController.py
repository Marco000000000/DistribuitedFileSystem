#Fare controller upload M
# Fornire api all'api gateway
# Vedere  numero di file system
# Dividere file
# Produrre nei vari topic kafka
#multithreading
from flask import Flask, request
from werkzeug.utils import secure_filename
import json
import socket
import os
import mysql.connector
from confluent_kafka import Producer
from confluent_kafka import Consumer
import base64
import random
import string
from time import sleep
import logging
app=Flask(__name__)
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
PARTITION_GRANULARITY=os.getenv("PARTITION_GRANULARITY", default = 131072)
print("aaa")
logger = logging.getLogger()
logger.setLevel(logging.INFO)
topics=[]
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

cursor=db.cursor(buffered=True)

def produceJson(topicName,dictionaryData):#funzione per produrre un singolo Json su un topic
    p=Producer({'bootstrap.servers':'kafka:9093'})
    m=json.dumps(dictionaryData)
    p.poll(0.001)
    p.produce(topicName, m.encode('utf-8'),callback=receipt)
    p.flush()


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
                while c.list_topics().topics[groupId] is None:
                    print("in attesa del manager")
                    sleep(0.2)
                c.commit()
                c.unsubscribe()
                return data
            

def consumeJson(topicName,groupId):#consuma un singolo json su un topic e in un gruppo
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
                c.commit()
                c.unsubscribe()
                c.close()
                return data
            

def get_random_string(length):#creazione stringa random 
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


def receipt(err,msg):
    if err is not None:
        print('Error: {}'.format(err))
    else:
        message = 'Prodotto un messaggio sul topic {} con il valore {}\n'.format(msg.topic(), msg.value().decode('utf-8'))
        logger.info(message)
        print(message)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def first_Call():#funzione per la ricezione di topic iniziali
    name=socket.gethostname()
    data={
          "Host":name,
          "Type":"Upload"}
    print(data)
    produceJson("CFirstCall",data)
    aList=consumeJsonFirstCall("CFirstCallAck",name)
    #format per Federico ->jsonStr = '{"cose":"a caso","topics":[1, 2,3, 4]}'
    print(aList)
    return aList["topics"]


@app.route('/upload', methods=['POST'])
def upload_file():#gestione di un file in upload 


        file = request.files['file']
        fileName=secure_filename(file.filename)

        if file and allowed_file(fileName):
            db.commit()

            cursor.execute("SELECT file_name,ready FROM files where file_name= %s",(fileName[:99],))
            
            if cursor.rowcount>0:
                fetch=cursor.fetchone()
                print(fetch)
                if(fetch[1]==False):
                    return {"error":"File in updating"}
                cursor.execute("delete from files where file_name= %s",(fileName[:99],))
                for topic in topics:
                    data={
                        "fileName": secure_filename(fileName[:99]),
                    }
                    produceJson("Delete"+str(topic),data)  
            for topic in topics:
                print("asds32432432?")
                cursor.execute("INSERT INTO files (file_name ,partition_id,ready) VALUES (%s, %s,%s)",(fileName[:99],1,False))
                #problema possibile di request mentre è ancora in corso l'upload
                db.commit()
            count=0
            fileNotFinished=True
            p=Producer({'bootstrap.servers':'kafka:9093'})

            while fileNotFinished:

                for topic in topics:
                    print(topic)
                    chunk=file.stream.read(PARTITION_GRANULARITY)
                    if len(chunk)== 0:
                        fileNotFinished=False
                        returnTopic=socket.gethostname()
                        p.flush()
                        data={
                        "fileName": secure_filename(fileName[:99]),
                        "last":True,
                        "returnTopic":returnTopic
                        }
                        produceJson("Upload"+str(topic),data)  
                        consumeJson(returnTopic,"1")
                        cursor.execute("UPDATE files SET ready = true WHERE file_name= %s",(fileName[:99],))

                        break
                    data={
                    "fileName": secure_filename(fileName[:99]),
                    "data":str(base64.b64encode(chunk),"UTF-8"),
                    "last":False, # è utile oppure non ha senso?
                    "count":count
                    }
                    print(data)
                    count+=1
                    m=json.dumps(data)
                    p.poll(0.001)
                    p.produce("Upload"+str(topic), m.encode('utf-8'),callback=receipt)
                    
                
            db.commit()

            return "ok"

        else:
            return {"error":"Incorrect extenction"}
        

if __name__=="__main__":
    topics=first_Call() #ricezione dati necessari per la ricezione
    hostname = socket.getfqdn()
    print(socket.gethostbyname_ex(hostname))

    app.run(debug=False,host=socket.gethostbyname_ex(hostname)[2][0],port=80)



