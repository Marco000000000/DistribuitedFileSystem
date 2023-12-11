from flask import Flask, flash, request,send_from_directory,current_app ,redirect, url_for
import os
from werkzeug.utils import secure_filename

app=Flask(__name__)
UPLOAD_FOLDER = 'downloadable'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
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
app.register_blueprint
@app.route('/download/<path:filename>', methods=['GET', 'POST'])
def download(filename):
    uploads = os.path.join(current_app.root_path, app.config['UPLOAD_FOLDER'])
    return send_from_directory(uploads, filename)

@app.route('/upload', methods=['GET', 'POST'])
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
