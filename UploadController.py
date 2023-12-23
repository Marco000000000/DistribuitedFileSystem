#Fare controller upload M
# Fornire api all'api gateway
# Vedere  numero di file system
# Dividere file
# Produrre nei vari topic kafka
#multithreading
from flask import Flask, flash, request,send_from_directory,current_app ,redirect, url_for
from werkzeug.utils import secure_filename
import json
import mysql.connector
from confluent_kafka import Producer
from confluent_kafka import Consumer
import base64
import random
import string
import logging
app=Flask(__name__)
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
PARTITION_GRANULARITY=1024
logger = logging.getLogger()
logger.setLevel(logging.INFO)
topics=[]
db = mysql.connector.connect(
                host = "localhost",
                database = "ds_filesystem",
                user = "root",
                password = "giovanni",
                port = 3307
            )
cursor = db.cursor()

def produceJson(topicName,dictionaryData):
    p=Producer({'bootstrap.servers':'localhost:9092'})
    m=json.dumps(dictionaryData)
    p.poll(1)
    p.produce(topicName, m.encode('utf-8'),callback=receipt)


def consumeJson(topicName,groupId):
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
               
                c.close()
                c.unsubscribe()
                return data

def get_random_string(length):
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


def first_Call():
    data={"Code":get_random_string(20),
          "Type":"upload"}
    produceJson("CFirstCall",data)
    aList=consumeJson("CFirstCallAck",get_random_string(20))
    #format per Federico ->jsonStr = '{"cose":"a caso","topics":[1, 2,3, 4]}'

    return json.loads(aList)["topics"]


@app.route('/upload', methods=['POST'])
def upload_file():

        # check if the post request has the file part
        print(request)

        file = request.files['file']
        fileName=secure_filename(file.filename)
        
        if file and allowed_file(fileName):
            
            cursor.execute("SELECT file_name FROM file where file_name= %s",(fileName[:99]))
            
            if cursor.rowcount:
                cursor.execute("delete from file where file_name= %s",(fileName[:99]))
            for topic in topics:
                cursor.execute("INSERT INTO file (file_name ,partition_id) VALUES (%s, %s)",(fileName,topic))
            count=0
            fileNotFinished=True
            while fileNotFinished:
                
                for topic in topics:
                    chunk=file.stream.read(PARTITION_GRANULARITY)
                    if len(chunk)== 0:
                        fileNotFinished=False
                        break
                    data={
                    "fileName": secure_filename(fileName),
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
    app.run(debug=True,port=80)



