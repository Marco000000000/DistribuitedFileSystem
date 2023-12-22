from flask import Flask, flash, request,send_from_directory,current_app ,redirect, url_for
import os
from werkzeug.utils import secure_filename
import json
import base64
app=Flask(__name__)
UPLOAD_FOLDER = 'downloadable'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif','py'}
PARTITION_GRANULARITY=1024
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def download_file(filename,topicNumber):
    topicName="Download"+topicNumber
    if filename is not None and  allowed_file(filename):
        directory = os.path.join(current_app.root_path, app.config['UPLOAD_FOLDER'],filename)
        index=0
        print(directory)
        with open(directory, "rb") as f:
            m=""
            while (byte := f.read(22222222222)):

                data={
                    
                    "data":str(base64.b64encode(byte),"UTF-8"),
                    "a":1 
                    }
                m=m+json.dumps(data)
            with open(os.path.join(current_app.root_path, app.config['UPLOAD_FOLDER'],"aaa"), "a+") as f:
                json.dump(data,f)
            return m


def upload_file(filename,pack):
    directory = os.path.join(current_app.root_path, app.config['UPLOAD_FOLDER'],"aaa")

    with open(directory, "r") as f:
            file=""
            directory = os.path.join(current_app.root_path, app.config['UPLOAD_FOLDER'],"prova.jpg")
            file=json.load(f)
    b=b""
    b = base64.b64decode(file["data"])
    with open(directory, "ab+") as f:
        f.write(b)       
    return "ok"


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
app.register_blueprint
@app.route('/download/<path:filename>', methods=['GET', 'POST'])
def download(filename):
    uploads = os.path.join(current_app.root_path, app.config['UPLOAD_FOLDER'])
    download_file(filename, filename)
    return upload_file(filename, filename)


app.run(debug=True,port=80)