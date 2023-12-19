import os
from werkzeug.utils import secure_filename
from confluent_kafka import Producer
from confluent_kafka import Consumer
import logging
import json
import subprocess
import base64
import random
import string

PARTITION_GRANULARITY=1024
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", default = 'downloadable')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
FILESYSTEM_DIMENSION=os.getenv("FILESYSTEM_DIMENSION", default = 100)#Mb
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
def get_random_string(length):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    print("Random string of length", length, "is:", result_str)

p=Producer({'bootstrap.servers':'localhost:9092'})
c=Consumer({'bootstrap.servers':'localhost:9092','group.id':get_random_string(20),'auto.offset.reset':'earliest'})

logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename='producer.log',
                    filemode='w')

logger = logging.getLogger()
logger.setLevel(logging.INFO)




print('Topics disponibili da consumare: ', c.list_topics().topics)
c.subscribe(['FirstCallAck'])
# Logging e Stampa dei messaggi prodotti
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


@app.route("/", methods=["GET"])
def init():

    dir1=os.listdir( app.config['UPLOAD_FOLDER'])#dir1=uos.ilistdir("/sd")
    output=" "
    output="<html> <head></head><body> "
    for file in dir1:
        output+=" "
        output += "<a href=\"download/"
        output += file#str(file[0])
        output += "\">"
        output += "<br>"
        output +=file[0:]#str(file)
        output += "</a>"
    output+="</body> </html>"
    return output


#mettere funzione che da un solo pacchetto
def download_file(filename,topicNumber):
    topicName="Download"+topicNumber
    if filename is not None and  allowed_file(filename):
        directory = os.path.join(current_app.root_path, app.config['UPLOAD_FOLDER'],filename)
        index=0
        with open(directory, "rb") as f:
            while (byte := f.read(PARTITION_GRANULARITY)):
                data={
                    
                    "data":base64.b64encode(byte)
                    }
                m=json.dumps(data)
                p.poll(1)
                p.produce(topicName, m.encode('utf-8'),callback=receipt)
                p.flush()
                return 
        
def upload_file(filename,pack):
    directory = os.path.join(current_app.root_path, app.config['UPLOAD_FOLDER'],filename)

    file = base64.b64decode(pack["data"])

    with open(directory, "ab+") as f:
        f.write(file)
    

app.run(debug=True,port=80)
def first_Call():
    data={"Name":get_random_string(20),
          "Dim":FILESYSTEM_DIMENSION}
    m=json.dumps(data)
    p.poll(1)
    p.produce('FirstCall', m.encode('utf-8'),callback=receipt)
    p.flush()
    while True:
            msg=c.poll(1.0) #timeout
            if msg is None:
                continue
            elif msg.error():
                print('Error: {}'.format(msg.error()))
                continue
            else:
                data=msg.value().decode('utf-8')
                print(data)
                break
    c.close()
    c.unsubscribe()

    return data["id"],data["topic"]

def delete_file(filename):
    if os.path.exists(filename):
        os.remove(filename)

if __name__== "main":
    id,topicNumber=first_Call()
    uploadConsumer=Consumer({'bootstrap.servers':'localhost:9092','group.id':str(id),'auto.offset.reset':'earliest'})
    uploadConsumer.subscribe("Upload"+topicNumber)
    requestConsumer=Consumer({'bootstrap.servers':'localhost:9092','group.id':"000",'auto.offset.reset':'earliest'})
    requestConsumer.subscribe("Request"+topicNumber)
    deleteConsumer=Consumer({'bootstrap.servers':'localhost:9092','group.id':"000",'auto.offset.reset':'earliest'})
    deleteConsumer.subscribe("Delete"+topicNumber)
    while True:
        msg=requestConsumer.poll(0.1)
        msgUpload=uploadConsumer.poll(0.1)
        msgDelete=deleteConsumer.poll(0.1)

        if msg is None:
            continue
        elif msg.error():
            print('Error: {}'.format(msg.error()))
            continue
        else:
            data=msg.value().decode('utf-8')
            if data["fileName"]!="":
                download_file(secure_filename(data["fileName"]),topicNumber)

        if msgUpload is None:
            continue
        elif msgUpload.error():
            print('Error: {}'.format(msg.error()))
            continue
        else:
            data=msgUpload.value().decode('utf-8')
            if data["fileName"]!="":
                upload_file(secure_filename(data["fileName"]),data)
                
        if msgDelete is None:
            continue
        elif msgDelete.error():
            print('Error: {}'.format(msg.error()))
            continue
        else:
            data=msgDelete.value().decode('utf-8')
            if data["fileName"]!="":
                delete_file(secure_filename(data["fileName"]))                
                
            