#Fare controller upload M
# Fornire api all'api gateway
# Vedere  numero di file system
# Dividere file
# Produrre nei vari topic kafka
#multithreading
from flask import Flask, flash, request,send_from_directory,current_app ,redirect, url_for
from werkzeug.utils import secure_filename
import json
import os
import mysql.connector
from confluent_kafka import Producer
from confluent_kafka import Consumer
import base64
import random
import string
import logging
app=Flask(__name__)
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
PARTITION_GRANULARITY=os.getenv("PARTITION_GRANULARITY", default = 1024)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
topics=[]
db = mysql.connector.connect(#mi servono credenziali con permesso di modifica solo nella tabella file
                host = "localhost",
                database = "ds_filesystem",
                user = "file_manager",
                password = "file",
                port = 3307
            )
cursor = db.cursor()

def produceJson(topicName,dictionaryData):#funzione per produrre un singolo Json su un topic
    p=Producer({'bootstrap.servers':'localhost:9092'})
    m=json.dumps(dictionaryData)
    p.poll(1)
    p.produce(topicName, m.encode('utf-8'),callback=receipt)


def consumeJson(topicName,groupId):#consuma un singolo json su un topic e in un gruppo
    c=Consumer({'bootstrap.servers':'localhost:9092','group.id':groupId,'auto.offset.reset':'earliest'})
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
    code=get_random_string(20)
    data={"Code":code,
          "Type":"upload"}
    produceJson("CFirstCall",data)
    aList=consumeJson("CFirstCallAck",code)
    #format per Federico ->jsonStr = '{"cose":"a caso","topics":[1, 2,3, 4]}'

    return json.loads(aList)["topics"]


@app.route('/upload', methods=['POST'])
def upload_file():#gestione di un file in upload 


        file = request.files['file']
        fileName=secure_filename(file.filename)
        
        if file and allowed_file(fileName):
            
            cursor.execute("SELECT file_name,ready FROM file where file_name= %s",(fileName[:99]))
            
            if cursor.rowcount:
                if(cursor.fetchone()["ready"]==False):
                    return {"error":"File in updating"}
                cursor.execute("delete from file where file_name= %s",(fileName[:99]))
                for topic in topics:
                    data={
                        "fileName": secure_filename(fileName[:99]),
                    }
                    produceJson("Delete"+topic,data)  
            for topic in topics:
                cursor.execute("INSERT INTO file (file_name ,partition_id,ready) VALUES (%s, %s,%s)",(fileName[:99],topic,False))
                #problema possibile di request mentre è ancora in corso l'upload
                db.commit()
            count=0
            fileNotFinished=True

            while fileNotFinished:
                
                for topic in topics:
                    chunk=file.stream.read(PARTITION_GRANULARITY)
                    if len(chunk)== 0:
                        fileNotFinished=False
                        returnTopic=get_random_string(20)
                        data={
                        "fileName": secure_filename(fileName[:99]),
                        "last":True,
                        "returnTopic":returnTopic
                        }
                        produceJson("Upload"+topic,data)  
                        consumeJson(returnTopic,"1")
                        cursor.execute("UPDATE file SET ready = 'true' WHERE file_name= %s",(fileName[:99]))

                        break
                    data={
                    "fileName": secure_filename(fileName[:99]),
                    "data":str(base64.b64encode(chunk),"UTF-8"),
                    "count":count
                    }
                    count+=1
                    produceJson("Upload"+topic,data)  
            
            db.commit()

            return "ok"

        else:
            return {"error":"Incorrect extenction"}
        

if __name__=="__main__":
    topics=first_Call() #ricezione dati necessari per la ricezione
    app.run(debug=False,port=80)



