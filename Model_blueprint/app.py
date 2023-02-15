import json
from flask import Flask
from flask_cors import CORS 
from model_bluprint import model_routes
MegaBytes =1024 * 1024

#load from config
with open('model_config.json') as f:
    data=json.load(f)
    ROOT_UPLOADS= data["app"]["upload_folder"]
    ROOT_SAVES = data['app']["save_folder"]
    MAX_MB =data['app']['max_content']

app=Flask(__name__)
CORS(app=app,support_credentials=True)
app.config['SECRET_KEY']='ashd65ba57asdavd82'
app.config['UPLOAD_FOLDER']=ROOT_UPLOADS
app.config['SAVE_FOLDER']=ROOT_SAVES
app.config["MAX_CONTENT_LENGTH"]=MAX_MB * MegaBytes
app.register_blueprint(model_routes)


