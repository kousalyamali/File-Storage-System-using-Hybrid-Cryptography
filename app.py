import os
from flask import Flask, request, redirect, url_for, render_template, send_file, flash
from werkzeug.utils import secure_filename
import tools
import divider as dv
import encrypter as enc
import decrypter as dec
import restore as rst
from firebase_admin import credentials, initialize_app, storage
import google.api_core.exceptions

# Firebase initialization
cred = credentials.Certificate(r'C:\Users\KOUSALYA\OneDrive\Desktop\Secure-File-Storage-Using-Hybrid-Cryptography-master\file-storage-system-8cd1b-firebase-adminsdk-h4it1-6fe4d280cc.json')
initialize_app(cred, {'storageBucket': 'file-storage-system-8cd1b.appspot.com'})

UPLOAD_FOLDER = './uploads/'
UPLOAD_KEY = './key/'
ENCRYPTED_FOLDER = './encrypted/'
ALLOWED_EXTENSIONS = set(['pem'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['UPLOAD_KEY'] = UPLOAD_KEY

def upload_to_firebase(enc_file_path):
    if not os.path.isfile(enc_file_path):
        raise FileNotFoundError(f"The file {enc_file_path} does not exist.")
    
    bucket = storage.bucket()
    blob = bucket.blob(os.path.basename(enc_file_path))  # Get the filename from the path
    blob.upload_from_filename(enc_file_path)
    blob.make_public()
    return blob.public_url

def download_from_firebase(source_blob_name, destination_file_name):
    bucket = storage.bucket()
    blob = bucket.blob(source_blob_name)
    
    try:
        #blob.download_to_filename(destination_file_name)
        print(f"Downloaded {source_blob_name} to {destination_file_name}")
    except google.api_core.exceptions.NotFound:
        raise FileNotFoundError(f"File {source_blob_name} not found in Firebase.")

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def list_files_in_firebase():
    bucket = storage.bucket()
    blobs = bucket.list_blobs()
    file_names = [blob.name for blob in blobs]
    if not file_names:
        return
    print("Files in Firebase Storage:")
    for file_name in file_names:
        print(file_name)
    return file_names

def start_encryption():
    dv.divide()
    tools.empty_folder('uploads')
    enc.encrypter()
    
    if not os.path.exists(ENCRYPTED_FOLDER):
        os.makedirs(ENCRYPTED_FOLDER)

    encrypted_files = os.listdir(ENCRYPTED_FOLDER)
    if not encrypted_files:
        raise FileNotFoundError("No files found in the 'encrypted/' directory.")

    encrypted_file_path = os.path.join(ENCRYPTED_FOLDER, encrypted_files[0])  # Adjust as needed
    
    firebase_url = upload_to_firebase(encrypted_file_path)
    print("File uploaded to Firebase. URL:", firebase_url)
    
       
    return render_template('success.html', file_url=firebase_url)

def upload_ext_file():
    if not os.path.exists(ENCRYPTED_FOLDER):
        os.makedirs(ENCRYPTED_FOLDER)

    ext_file_name = None
    for file_name in os.listdir(ENCRYPTED_FOLDER):
        if file_name.endswith('.ext'):
            ext_file_name = file_name
            break

    if not ext_file_name:
        raise FileNotFoundError("No .ext file found in the 'encrypted/' directory.")

    ext_file_path = os.path.join(ENCRYPTED_FOLDER, ext_file_name)
    
    firebase_url = upload_to_firebase(ext_file_path)
    print("File uploaded to Firebase. URL:", firebase_url)
    
    return firebase_url

def start_decryption():
    # List all files in Firebase and find the appropriate encrypted file
    firebase_files = list_files_in_firebase()

    # Assume we are looking for a file with a specific extension or pattern
    encrypted_file_name = None
    if not firebase_files:
        print("File not found in Firebase")
        return render_template('file_not_found.html')
    
    for file_name in firebase_files:
        encrypted_file_name = file_name
        break
    
    if not encrypted_file_name:
        return "No encrypted file found in Firebase."

    local_encrypted_path = os.path.join(ENCRYPTED_FOLDER, encrypted_file_name)
    
    if not os.path.exists(ENCRYPTED_FOLDER):
        os.makedirs(ENCRYPTED_FOLDER)
    
    try:
        download_from_firebase(encrypted_file_name, local_encrypted_path)
    except FileNotFoundError as e:
        return str(e)

    dec.decrypter()
    tools.empty_folder('key')
    rst.restore()
    return render_template('restore_success.html')

@app.route('/return-key/My_Key.pem')
def return_key():
    list_directory = tools.list_dir('key')
    filename = './key/' + list_directory[0]
    return send_file(filename, download_name='My_Key.pem')

@app.route('/return-file/')
def return_file():
    list_directory = tools.list_dir('restored_file')
    filename = './restored_file/' + list_directory[0]
    return send_file(filename, download_name=list_directory[0], as_attachment=True)

@app.route('/download/')
def downloads():
    return render_template('download.html')

@app.route('/upload')
def call_page_upload():
    return render_template('upload.html')

@app.route('/home')
def back_home():
    tools.empty_folder('key')
    tools.empty_folder('restored_file')
    return render_template('index.html')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data', methods=['GET', 'POST'])
def upload_file():
    tools.empty_folder('uploads')
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return 'NO FILE SELECTED'
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
            return start_encryption()
        return 'Invalid File Format !'
    
@app.route('/download_data', methods=['GET', 'POST'])
def upload_key():
    tools.empty_folder('key')
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return 'NO FILE SELECTED'
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_KEY'], file.filename))
            return start_decryption()
        return 'Invalid File Format !'

@app.route('/upload_ext')
def upload_ext():
    try:
        firebase_url = upload_ext_file()
        return render_template('success.html', file_url=firebase_url)
    except FileNotFoundError as e:
        return str(e)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)
