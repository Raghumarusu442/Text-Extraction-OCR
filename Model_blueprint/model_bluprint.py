from flask import Flask,jsonify,request,Blueprint
import logging
import json
from flask_cors import CORS
import os
import re
import pickle
import sklearn
from sklearn.externals import joblib
from datetime import datetime   #To do: use in logs
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer,TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import AdaBoostClassifier
from sklearn.linear_model import SGDClassifier
from sklearn.svm import SVC
from sklearn.metrics import classification_report,confusion_matrix,accuracy_score
import numpy as np
import pandas as import pd  
from datetime import datetime
from nltk.corpus import stopwords
from sklearn.preprocessing import LabelEncoder
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA

def get_time():
    return datetime.now()

#load from config
with open('model_config.json') as f:
    data=json.load(f)
    ROOT_TRAIN=data['model_blueprint']['training_folder']
    MODE_TRAIN_DIR=data['model_blueprint']['model_save_folder']
    TEST_SIZE=data['model_blueprint']['test_size']

USE_MODEL_CODE=0

logging.basicConfig(filename='logs\\model_blueprint.log',filemode='w',format='%(name)s-%(levelname)s-%(message)s',level=logging.INFO)
model_routes=Blueprint("model_routes",__name__)

#########################
#Helper: Preprocess text #
#########################
def preprocess_text(text):
    logging.info(f" [{get_time()}]Preprocessing content..")
    text= text.lower()
    text= " ".join([w for w in text.split() if w not in stopwords.words("english")])
    text=re.sub("\\s+"," ",text)
    text=re.sub("\\W+"," ",text)
    logging.info("Text processed!!")
    return text

#########################
#Helper: Save Latest Model #
#########################
def save_model_sklearn(model,model_name,cvectorizer,tfidf,results:dict):
    logging.info(f"[{ get_time() }]Saving Model..")
    model_name +=".pkl"
    #get folder count from model_save_dir
    num_models=len(os.listdir(MODE_TRAIN_DIR))
    dir_name=str(num_models+ 1)
    logging.info(f"[{ get_time() }] Model SaVE DIR : {dir_name}")
    dir_path=os.path.join(MODE_TRAIN_DIR,dir_name)
    configs_path=os.path.join(dir_path,model_name.replace("_model.pkl","_results.pkl"))
    logging.info(f"[{ get_time() }]Creating Directory..")
    os.mkdir(dir_path)
    logging.info(f"[{ get_time() }]Dumping Model..")
    #save model
    with open(os.path.join(dir_path,model_name),"wb") as t:
        pickle.dump(model,t)
    #save results: train acc, test acc
    logging.info(f"[{ get_time() }]Dumping results..")
    with open(configs_path,"wb") as t:
        pickle.dump(results,t)
    #save countvec
    logging.info(f"[{ get_time() }]Dumping Cvecs..")
    configs_path_countVec=os.path.join(dir_path,model_name.replace("_model.pkl","_countVec.pkl"))
    with open(configs_path_countVec,"wb") as t:
        pickle.dump(cvectorizer,t)
    #save tfidf
    logging.info(f"[{ get_time() }]Dumping Tfidfs..")
    configs_path_tfidf=os.path.join(dir_path,model_name.replace("_model.pkl","_tfidf.pkl"))
    with open(configs_path_tfidf,"wb") as t:
        pickle.dump(tfidf,t)
    #load json for model config
    with open('model_config.json') as f:
        global USE_MODEL_CODE
        data=json.load(f)
        if data['model_config']['use_model_force']=='latest':  #set the global model code to dir_name latest
            USE_MODEL_CODE=dir_name
            logging.info(f" [{get_time() }][model config save] ++ (LATEST)model use {USE_MODEL_CODE}")
        elif data['model_config']['use_model_force']=='None':
            USE_MODEL_CODE=dir_name
            logging.info(f" [{get_time() }][model config save] ++ (LATEST)model use {USE_MODEL_CODE}")
        else: #int model dir
            USE_MODEL_CODE=data['model_config']['use_model_force']
            last_model = USE_MODEL_CODE
            logging.info(f" [{get_time() }][model config save] ++ (FORCED )model use {last_model}")
    #end of load json for model config
    logging.info(f" [{get_time() }]model + config saved, USE_MODEL_CODE set to {USE_MODEL_CODE}!!")

    


    


    