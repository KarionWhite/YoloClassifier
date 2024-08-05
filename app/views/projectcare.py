from collections import deque
from flask import url_for
from ..app import app
import numpy as np
import zipfile
import logging
import shutil
import json
import sys
import cv2
import os

#importiere image_handel
sys.path.append(os.path.join(os.getcwd()))
from imager.analyzer import image_handel


def get_projects()->dict:
    path = os.path.join(app.config['POJECT_JSON'])
    logging.info(f"Loading projects from {path}")
    try:
        with open(path, 'r') as f:
            projects = json.load(f)
    except IOError:
        logging.error(f"File not found: {path}")
        projects = {}
        #erstelle eine leere projects.json
        with open(path, 'w') as f:
            json.dump(projects, f)
    return projects

def get_project_by_id(project_id: str) -> dict:
    projects = get_projects()
    return next((project for project in projects if project['id'] == project_id), {})

def get_project_labels(project_id:str)->list:
    myProject = get_project_by_id(project_id)
    if myProject == {}:
        return []
    path_splitted = myProject['path'].split('/')
    project_path = os.getcwd()
    for path in path_splitted:
        project_path = os.path.join(project_path, path)
    labels_path = os.path.join(project_path, 'annotations', 'labels.json')
    try:
        with open(labels_path, 'r') as f:
            labels = json.load(f)
    except FileNotFoundError:
        logging.error(f"Labels file not found: {labels_path}")
        labels = []
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON file: {labels_path}")
        labels = []
    return labels  
    
def save_projects(projects:dict) -> dict:
    path = os.path.join(app.config['POJECT_JSON'])
    with open(path, 'w') as f:
        json.dump(projects, f, indent=4)
    return {'success': 'Projects saved'}
        
def save_project(project:dict) -> dict:
    projects = get_projects()
    for i, p in enumerate(projects):
        if p['id'] == project['id']:
            projects[i] = project
            save_projects(projects)
            return {'success': 'Project saved'}
    return {'error': 'Project not found'}

def save_labels(project_id:str, labels:str)->dict:
    myProject = get_project_by_id(project_id)
    if myProject == {}:
        return {'error': 'Project not found'}
    path_splitted = myProject['path'].split('/')
    project_path = os.getcwd()
    for path in path_splitted:
        project_path = os.path.join(project_path, path)
    labels_path = os.path.join(project_path, 'annotations', 'labels.json')
    with open(labels_path, 'w') as f:
        labels = labels.split(',')
        labels = [label.strip() for label in labels]
        json.dump(labels, f, indent=4)
    return {'success': 'Labels saved'}

def delete_project_with_id(project_id:str)->dict:
    projects = get_projects()
    for i, project in enumerate(projects):
        if project['id'] == project_id:
            path_splitted = project['path'].split('/')
            project_path = os.getcwd()
            for path in path_splitted:
                project_path = os.path.join(project_path, path)
            try:
                shutil.rmtree(project_path)
            except FileNotFoundError:
                logging.error(f"Project path not found: {project_path}")
                return {'error': 'Project not found'}
            except PermissionError:
                try:
                    #if ubuntu
                    if os.name == 'posix':
                        for root, dirs, files in os.walk(project_path):
                            for file in files:
                                os.chmod(os.path.join(root, file), 0o777)
                            for dir in dirs:
                                os.chmod(os.path.join(root, dir), 0o777)
                        shutil.rmtree(project_path)
                    #if windows
                    elif os.name == 'nt':
                        os.system(f'rd /s /q {project_path}')
                except PermissionError:
                    if os.name == 'nt':
                        import wmi
                        c = wmi.WMI()
                        evil_processes = []
                        for process in c.Win32_Process():
                            try:
                                for file in process.OpenFiles():
                                    if project_path in file.Path:
                                        os.system(f'taskkill /F /PID {process.ProcessId}')
                                        evil_processes.append(process.ProcessId)
                                        break
                            except:
                                pass
                        try:
                            shutil.rmtree(project_path)
                        except:
                            logging.error(f"Permission denied repeated!: {project_path} Taskkill failed! Task:{evil_processes}")
                            return {'error': 'Permission denied Taskkill failed!'}
                    logging.error(f"Permission denied repeated!: {project_path}")
                    return {'error': 'Permission denied'}
                logging.error(f"Permission denied: {project_path}")
                return {'error': 'Permission denied'}
            del projects[i]
            save_projects(projects)
            return {'success': 'Project deleted'}
    return {'error': 'Project not found'}
   
def init_project(new_project,labels="")->dict:
    try:
        os.makedirs(new_project['path'])
        os.makedirs(os.path.join(new_project['path'],'images'))
        os.makedirs(os.path.join(new_project['path'],'annotations'))
        with open(os.path.join(new_project['path'],'annotations','labels.json'), 'w') as f:
            labels = labels.split(',')
            labels = [label.strip() for label in labels]
            json.dump(labels, f, indent=4)
        with open(os.path.join(new_project['path'],'annotations','images.json'), 'w') as f:
            """
            images = [
                {
                    "original": "image1.jpg",     ->     Originaler Name des Bildes -> bei Gleichheit wird das neue Bild verglichen
                    "label": "img_001.jpg"        ->     Im Datensatz wird das Bild als img_001.jpg gespeichert   
                    "path": "{images|upload|training|testing}/{label}"  ->     relativer Pfad zum Bild vom Projektordner aus
                    "hash": "hash"                ->     Hash des Bildes für schnellen vergleich
                }
            ]
            """
            json.dump([], f, indent=4)
        os.makedirs(os.path.join(new_project['path'],'uploads'))
        os.makedirs(os.path.join(new_project['path'],'models'))
    except FileExistsError:
        logging.error(f"Project already exists: {new_project['path']}")
        return {'error': 'Project already exists'}
    except PermissionError:
        logging.error(f"Permission denied: {new_project['path']}")
        return {'error': 'Permission denied'}
    return {'success': 'Project initialized'}

class UPLOADER:
    
    uploaders = {}
    
    def __init__(self, project_id:str, request:dict):
        self.status_log = deque(maxlen=1000)
        self.myProject = get_project_by_id(project_id)
        if self.myProject == {}:
            self.update_status({'error': 'Project not found'})
            return
        self.myRequest = request
        self.__class__.uploaders[project_id] = self
        self.update_status({'status': 'pending'})
        self.pending()
    
    def update_status(self, status:dict):
        self.status_log.append(status)
        if 'error' in status:
            logging.error(status['error'])
        else:
            logging.info(status)
        
    def get_status_log(self):
        return list(self.status_log)
        
    def pending(self):
        if hasattr(self, 'myProject') and hasattr(self.myRequest,'files'):
            uploaded_files = self.myRequest.files
        else:
            self.update_status({'error': 'Project or files not found'})
            return
        #test auf images
        if 'images' in uploaded_files:
            self.upload_images()
        #test auf zip-file
        elif 'zip_file' in uploaded_files:
            self.upload_zip() 
        #test auf file
        elif 'file' in uploaded_files:
            self.upload_file()
        else:
            self.update_status({'error': 'No supported files found'})
            
    
    def upload_images(self):
        self.update_status({'status': 'uploading'})
        self.update_status({'progress': 0})
        uploaded_files = self.myRequest.files
        images = uploaded_files.getlist('images')
        total_images = len(images)
        uploaded_count = 0

        for image in images:
            if image and UPLOADER.allowed_file(image.filename):
                byte_stream = image.read()
                nparr = np.frombuffer(byte_stream, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                self.save_image(img, image.filename)
                uploaded_count += 1
                self.update_status({'progress':str(int((uploaded_count / total_images) * 100))})
            else:
                self.update_status({'error': f'skip file {image.filename} because of invalid file type'})
        self.update_status({'status': 'uploading completed'})
        
        
    
    def upload_file(self):
        self.update_status({'status': 'uploading'})
        pass
    
    def upload_zip(self):
        self.update_status({'status': 'uploading'})
        #wir downloaden erstmal das zip-file
        zip_file = self.myRequest.files['zip_file']
        zip_path = os.path.join(self.myProject['path'], 'uploads', "temp.zip")
        zip_file.save(zip_path)
        #entpacken
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(os.path.join(self.myProject['path'], 'temp'))
        except zipfile.BadZipFile:
            self.update_status({'error': 'Bad Zip File'})
            return
        except zipfile.LargeZipFile:
            self.update_status({'error': 'Large Zip File'})
            return
        except IOError:
            self.update_status({'error': 'Error extracting Zip File'})
            return
        #lösche zip-file
        shutil.rmtree(zip_path)
        #test auf images
        path_images = []
        for root, dirs, files in os.walk(os.path.join(self.myProject['path'], 'temp')):
            for file in files:
                if UPLOADER.allowed_file(file):
                    path_images.append(os.path.join(root, file))
        total_images = len(path_images)
        uploaded_count = 0
        self.update_status({'progress': uploaded_count})
        for path in path_images:
            try:
                img = cv2.imread(path)
            except IOError:
                self.update_status({'error': f"Error reading image {path}"})
                continue
            self.save_image(img, path.split('/')[-1])
            uploaded_count += 1
            self.update_status({'progress': int((uploaded_count / total_images) * 100)})
        #lösche temp
        shutil.rmtree(os.path.join(self.myProject['path'], 'temp'))
        self.update_status({'status': 'uploading completed'})
        
        
    
    def allowed_file(filename:str)->bool:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    
    def save_image(self, image,image_name:str,fool:bool=True)->dict:
        img = image
        imaging = self.safe_image_name(image_name)
        #vergleiche verdächtige images
        my_handel = image_handel.from_cv2_image(img)
        my_hash = my_handel.hash_image()
        if imaging['proof']:
            for proofing in imaging['proof']:
                if not proofing[1]['hash']:
                    pro_path = os.path.join(self.myProject['path'],proofing['path'])
                    pro_handel = image_handel(pro_path)
                    proofing[1]['hash'] = pro_handel.hash_image()
                    #speichere hash in images.json
                    self.change_images_json(proofing[0], proofing[1])
                    del images_json
                if my_hash == proofing[1]['hash']:
                    self.update_status({'error': f"Image {image_name} already exists"})
                    return
        #lasst uns es dumm sicher machen!
        if fool and self.compare_hashes(my_hash):
            return
        #ok keine doppelten mehr =)
        
        #save object to images.json
        imaging['image']['hash'] = my_hash
        self.add_to_images_json(imaging['image'])
        #save image
        path_to_save = os.path.join(self.myProject['path'], imaging['image']['path'])
        try:
            cv2.imwrite(path_to_save, img)
        except IOError:
            self.update_status({'error': f"Error saving image {image_name}"})
            return
        self.update_status({'status': f'Image {image_name} saved'})
        
        
                
                    
    def compare_hashes(self, my_hash:str)->bool:
        with open(os.path.join(self.myProject['path'],'annotations','images.json'), 'r') as f:
            images_json = json.load(f)
        for i, image in enumerate(images_json):
            if not image['hash']:
                pro_path = os.path.join(self.myProject['path'],image['path'])
                pro_handel = image_handel(pro_path)
                images_json[i]['hash'] = pro_handel.hash_image()
                #speichere hash in images.json
                self.change_images_json(i, images_json[i])
                del images_json
            if my_hash == image['hash']:
                self.update_status({'error': f"Image {image.filename} already exists"})
                return True
        self.update_status({'status': 'compare with other Images completed->no dublicate found'})
        return False                  
                    
    def change_images_json(self, number:int, image:dict):
        with open(os.path.join(self.myProject['path'],'annotations','images.json'), 'r') as f:
            images_json = json.load(f)
        images_json[number] = image
        with open(os.path.join(self.myProject['path'],'annotations','images.json'), 'w') as f:
            json.dump(images_json, f, indent=4)               
                
    def add_to_images_json(self, image:dict):
        with open(os.path.join(self.myProject['path'],'annotations','images.json'), 'r') as f:
            images_json = json.load(f)
        images_json.append(image)
        with open(os.path.join(self.myProject['path'],'annotations','images.json'), 'w') as f:
            json.dump(images_json, f, indent=4)
    
    def safe_image_name(self, image_name:str)->dict:
        images_json = os.path.join(self.myProject['path'], 'annotations', 'images.json')
        #test auf existenz
        if not os.path.exists(images_json):
            with open(images_json, 'w') as f:
                json.dump([], f)
        with open(images_json, 'r') as f:
            images = json.load(f)
        images_to_compare = []
        last_label = 0
        for i,image in enumerate(images):
            if image['original'] == image_name:
                images_to_compare.append((i,image))
            label = int(image['label'].split('.')[0].split('_')[1])
            if label > last_label:
                last_label = label
        last_label += 1
        new_image_name = f"img_{last_label}.jpg"
        imaging = {}
        imaging['image'] = {'original': image_name, 'label': new_image_name, 'path': f"uploads/{new_image_name}"}
        imaging['proof'] = images_to_compare
        return imaging
            
    
    @classmethod
    def get_status(cls, project_id:str)->list[dict[str:str]]:
        if project_id in cls.uploaders:
            return cls.uploaders[project_id].get_status_log()
        return [{'error': 'Project not found'}]

class ClientImages:
    
    myClients:dict[str,"ClientImages"] = {}
    
    def __init__(self,project_id) -> None:
        self.project_id = project_id
        self.myProject = get_project_by_id(project_id)
        if self.myProject == {}:
            self.init_error_images()
        else:
            self.init_images()
        self.current = 0
        self.__class__.myClients[project_id] = self
    
    @classmethod
    def get_client(cls, project_id:str)->"ClientImages":
        if project_id in cls.myClients:
            return cls.myClients[project_id]
        return cls(project_id)
    
    @classmethod
    def has_client(cls, project_id:str)->bool:
        return project_id in cls.myClients
    
    @classmethod
    def delete_client(cls, project_id:str)->bool:
        if project_id in cls.myClients:
            del cls.myClients[project_id]
            return True
        return False
    
    @classmethod
    def set_current_as_classified_image(self,project_id:str)->bool:
        if project_id in self.myClients:
            my_image = self.myClients[project_id]
            current_image_path = my_image.get_current_image_path()
            try:
                shutil.move(current_image_path, os.path.join(my_image.myProject['path'],'images',my_image.image_paths[my_image.current]['label']))
                for img in my_image.image_paths:
                    if img['label'] == my_image.image_paths[my_image.current]['label']:
                        img['path'] = 'images/' + img['label']
                        my_image.save_images()
                        break
                my_image.init_images()
            except FileNotFoundError:
                logging.error(f"Image not found: {current_image_path}")
                return False
            except PermissionError:
                logging.error(f"Permission denied: {current_image_path}")
                return False
            return True
        
    def init_images(self):
        images = self.load_images()
        new_uploads = [upload for upload in images if 'uploads' in upload['path']]
        new_uploads.sort(key=lambda x: int(x['label'].split('.')[0].split('_')[1]))
        my_images = [image for image in images if 'images' in image['path']]
        my_images.sort(key=lambda x: int(x['label'].split('.')[0].split('_')[1]))
        self.image_paths = new_uploads + my_images
        if len(self.image_paths) == 0:
            self.image_paths = [{"path":os.path.join(os.getcwd(),"app","static","img","no_images.jpg"),"label":"no_images.jpg"}]
            
    def init_error_images(self):
        self.image_paths = [{"path":os.path.join(os.getcwd(),"app","static","img","no_project.jpg"),"label":"no_project.jpg"}]
    
    def load_images(self)->list:
        self.images_json = os.path.join(self.myProject['path'], 'annotations', 'images.json')
        with open(self.images_json, 'r') as f:
            images:list = json.load(f)
        return images
    
    def save_images(self):
        with open(self.images_json, 'w') as f:
            json.dump(self.image_paths, f, indent=4)
    
    def get_image_path(self):
        return self.get_absolute_path(self.image_paths[self.current]['path'])
    
    def get_image_labels(self)->list[str,str,str]:
        current = self.current
        last = self.current-1   #wenn current = 0 dann ist last = -1 -> letztes Bild ergo negatives overflow kann nicht passieren
        next = self.current+1
        if next >= len(self.image_paths):
            next = 0
        return [
            self.image_paths[last]['label'],
            self.image_paths[current]['label'],
            self.image_paths[next]['label']
        ]
    
    def get_current_image_path(self)->str:
        return self.get_absolute_path(self.image_paths[self.current]['path'])
    
    def get_next_image_path(self)->str:
        if self.current+1 >= len(self.image_paths):
            return self.get_absolute_path(self.image_paths[0]['path'])
        return self.get_absolute_path(self.image_paths[self.current+1]['path'])
        
    def get_last_image_path(self)->str:
        if self.current-1 < 0:
            return self.get_absolute_path(self.image_paths[-1]['path'])
        return self.get_absolute_path(self.image_paths[self.current-1]['path'])
    
    def set_next_image(self):
        self.current += 1
        if self.current >= len(self.image_paths):
            self.current = 0
        return self.get_image_labels()
    
    def set_last_image(self):
        self.current -= 1
        if self.current < 0:
            self.current = len(self.image_paths)-1
        return self.get_image_labels()
    
    def set_current_label(self, label:str):
        for i, image in enumerate(self.image_paths):
            if image['label'] == label:
                self.current = i
                return self.get_image_labels()
    
    def get_absolute_path(self, path: str) -> str:
        if "static" in path or os.path.isabs(path):  # Überprüfen, ob der Pfad absolut ist
            return path
        my_path = path.split('/')
        path_splitted = self.myProject['path'].split('/')
        path_splitted = path_splitted + my_path
        project_path = os.getcwd()
        for path in path_splitted:
            project_path = os.path.join(project_path, path)
        if not os.path.exists(project_path):
            return self.return_error_image()
        return project_path
    
    def return_error_image(self)->str:
        return os.path.join(os.getcwd(),"app","static","img","image_not_found.jpg")
    
    def getmax(self)->int:
        return len(self.image_paths)

    def get_project_ai_labels(self)->list[str]:
        return get_project_labels(self.project_id)
    
        
    