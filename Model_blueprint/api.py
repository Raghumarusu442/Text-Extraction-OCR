# -*- coding: utf-8 -*-
"""
Created on Thu Jan 16 23:57:13 2020

@author: Raghavendra marusu
"""

import logging
import os
import urllib.request 
from app import app
from flask import Flask,request,jsonify,redirect,url_for
import uuid
import textract
import pytesseract
from PIL import Image
import zipfile
import json
import requests
from datetime import datetime
from tika import parser


logging.basicConfig(filename='app.log',filemode='w',format='%(name)s - %(levelname)s - %(message)s',level=logging.INFO)

# ALLOWED_EXTENSIONS = set(['txt','pdf','png','jpg','jpeg','xlsx','xlx','zip','pptx','tif','docx'])
# ZIPPED_EXTENSIONS = set(["zip"])

def get_time():
    return datetime.now()

with open('model_config.json') as f:
    data=json.load(f)
    ALLOWED_EXTENSIONS=set(data["api"]["allowed_extensions"])
    ZIPPED_EXTENSIONS=set(data['api']["zipped_extensions"])
    TIKA_EXTENSIONS=set(data['api']['for_tika'])

#FInd file extension

def find_extension(filename:str):
    extension=filename.rsplit(".",maxsplit=1)[-1].lower()
    logging.info(f" [{get_time()}]Extension for File {filename}:{extension}")
    return extension

#Find format response
def return_resp(message,status_Code:int):
    logging.info(f"[{get_time()}]Formating Response")
    resp = jsonify({"message" : message})
    resp.status_code=status_code
    return resp

#Extract and iterate through files in zip
def ziphandler(guid,filepath, extractdir):
    zipped=zipfile.ZipFile(filepath)
    zipinfos=zipped.infolist()
    #iterate through each file
    for zipinfo in zipinfos:
        zipinfo.filename=guid + zipinfo.filename
        zipped.extract(zipinfo,extractdir)
    zipped.close()
    for file in zipped.filelist:
        file_cls=DocumentHandler(guid=guid,file=file)
        file_Cls.preprocess()
        global file_info_dict
        file_info_dict[file_cls.filename]=file_cls.fileInfo()

###############################
# CLlass: Document Handler #
###############################
  
class DocumentHandler():
    def __init__(self,guid=None,file=None):
        self.guid=guid
        self.file=file
        self.filename=file.filename
        self.upload_path = app.config['UPLOAD_FOLDER']  #holds path for upload directory
        self.save_path = app.config['SAVE_FOLDER']      #holds path for save directory

        try:
            self.filetype=file.content_type
        except:
            self.filetype=None
            self.filesize=None
            self.guid_filename=None
            self.file_upload_path=None    #holds path to file
            self.file_save_path=None      #holds path to file
            self.extracted_feature=None
            self.extracted_filename=None
        
    def extractFeature(self):
        # check for file  extension & call extraction methods accordingly
        if self.file_extension in TIKA_EXTENSIONS:
            if self.filesize==0:
                return "File invalid/corrupt!!"
            else:
                #headers = { 'X-TIKA-PDFextractInlineImages': 'true'}
                rawText = parser.from_file(self.file_upload_path)
                text_content=rawText['content']
                if str(text_content).strip()=="None":
                    logging.info(f" [{get_time()}] None content from Tika...")
                return str(text_content)
    
    def preprocess(self):
        if self.filetype!=None:
            #assign guid to filename
            self.guid_filename =self.guid + self.filename
            #define upload path
            self.file_upload_path=os.path.join(self.upload_path,self.guid_filename)
            self.file.save(self.file_upload_path)
        else:
            #since,guid is already assigned to main file,skip reassignment
            self.guid_filename=self.filename
            #define to upload path
            self.file_upload_path=os.path.join(self.upload_path,self.filename)
            self.filetype='application/'+self.file_extension
        #get size of file
        self.filesize=os.path.getsize(self.file_upload_path)
        #define file saving path and format for individual and zip files
        #for individual file as input
        if self.file_extension not in ZIPPED_EXTENSIONS:
            self.extracted_filename=self.guid_filename.replace("."+self.file_extension,"")+".txt"
            self.file_save_path=os.path.join(self.save_path,self.extracted_filename)
            #update extracted_feature
            self.extracted_feature=self.extractFeature()
            #write to file_save_path location
            with open(self.file_save_path,'wt',encoding="utf-8") as w:
                if self.extracted_feature==None:
                    w.write("Nothing extracted")
                else:
                    w.write(self.extracted_feature)
        else:
            pass
            # handle at ziphandler
            #ziphandler(self.guid,self.file_upload_path,self.upload_path)
    
    def fileInfo(self):
        return  {"File Name": self.filename,"GUUID": self.guid,"File Type": self.filetype,"file Size":self.filesize,"Extracted File Name": self.extracted_filename}

##############################
#output Dict for final response #
##############################
file_info_dict=dict()

#####################################
# FIle upload for Prediction : POST #
#####################################
@app.route("/file-upload",methods=['GET',"POST"])
def upload_file():
    if request.method== "POST":
        #if file in request
        if "file" in request.files:
            global file_info_dict
            file_info_dict.clear()
            #get file/files(s) from request
            file_list=request.files.getlist("file")
            #files of allowed file extensions
            allowed_files= [file for file in file_list if find_extension(file.filename) in ALLOWED_EXTENSIONS]
            #file names of skipped files
            skipped_files_names=[file.filename for file in file_list if  file not in allowed_files]
            for file in allowed_files:
                #create uid
                guid=str(uuid.uuid4().hex)
                file_cls=DocumentHandler(guid=guid,file=file)
                file_cls.preprocess()
                file_info_dict[file_cls.filename]=file_cls.fileInfo()
            try:
                return redirect(url_for('model_routes.predict',
                                floc=file_cls.file_save_path,
                                main_file=file_cls.file_upload_path,
                                files_processed_list=list(file_info_dict.keys()),
                                files_skipped_count=len(list(file_info_dict.keys())),
                                files_skipped_list=skipped_files_names,
                                file_guid=file_cls.guid,
                                status="success"
                                ))
            except:
                return return_resp({"Files processed":file_info_dict,"Files_skipped":skipped_files_names, 
                "Files Processed Count":len(file_info_dict),"Files skipped Count":len(skipped_files_names),"status":"File Upload error"},400)
        #if file NOT in request
        else:
            return return_resp("NO files in request",400)
   
    if request.method=="GET":
        #get  all files from save folder directory
        saved_files_with_sizes=[(f,os.path.getsize(os.path.join(app.config["SAVE_FOLDER"],f))) for f in os.listdir(app.config['SAVE_FOLDER'])]
        response_dict=dict()
        #if no files
        if len(saved_files_with_sizes)==0:
            return return_resp("NO files in save folder!",200)
        #if files
        for f,s in saved_files_with_sizes:
            response_dict[f]= {"File Name":f,"File Size":s,"File Type":find_extension(f),
            "Info": "use request method as POST for Training Model"}
        return return_resp(response_dict,200)

#############
# MAIN ######
#############

if __name__="__main__":
    app.run(host="127.0.0.1",port=5002,debug=True)


        

   
    
    
    