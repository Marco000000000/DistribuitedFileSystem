from flask import Flask, flash, request,send_from_directory,current_app ,redirect, url_for
import os
from werkzeug.utils import secure_filename
from confluent_kafka import Producer
from confluent_kafka import Consumer
import logging
import json
import subprocess
PARTITION_GRANULARITY=1024
app=Flask(__name__)
UPLOAD_FOLDER = 'downloadable'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
FILESYSTEM_DIMENSION=100#Mb
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

p=Producer({'bootstrap.servers':'localhost:9092'})
c=Consumer({'bootstrap.servers':'localhost:9092','group.id':'python-consumer','auto.offset.reset':'earliest'})

print('Topics disponibili da consumare: ', c.list_topics().topics)
c.subscribe(['FirstCallAck'])

logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename='producer.log',
                    filemode='w')

logger = logging.getLogger()
logger.setLevel(logging.INFO)


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



def download(filename):
    uploads = os.path.join(current_app.root_path, app.config['UPLOAD_FOLDER'])
    return send_from_directory(uploads, filename)

def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        print(request)
        
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file and allowed_file(file.filename):
            file.save( secure_filename(file.filename))
            return "ok"
        else:
            return "Tipo non adatto"
    else:
        return '''
        <!doctype html>
        <title>Upload new File</title>
        <h1>Upload new File</h1>
        <form method=post enctype=multipart/form-data>
        <input type=file name="file">
        <input type=submit value="Upload">
        </form>
        '''

app.run(debug=True,port=80)
def entry_topic():
    bashCommandName = "echo $NAME"

    ContainerName = subprocess.check_output(['bash','-c', bashCommandName]) 

    data={"Name":ContainerName,
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
    download=Consumer.subscribe([data["downloadTopic"]])
    

if __name__== "main":
    entry_topic()
   