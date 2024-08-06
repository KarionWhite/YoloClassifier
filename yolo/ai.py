from ultralytics import YOLO
from queue import Queue
from threading import Thread, Event
from random import shuffle
import numpy as np
import random
import shutil
import json
import yaml
import os


class YOLOTask:
    status:Queue = Queue()
    task_queue = Queue()
    me:"YOLOTask" = None
    projects_path = os.path.join(os.getcwd(),"yolores","projects")
    
    def __init__(self):
        super().__init__()
        self.train_event = Event()
        self.classify_event = Event()
        self.stop_event = Event()
        self.run_event = Event()
        task_queue = Queue()
        self.task = None
        self.status.put("idle")
        
    
    @classmethod
    def create_train_task(cls,project_id:str):
        if cls.me is None:
            cls.me = cls()
        cls.me.task_queue.put((project_id,"train"))
        cls.me.train_event.set()
        cls.me.run_event.set()
        
    @classmethod
    def create_classify_task(cls,project_id:str,image:np.ndarray):
        if cls.me is None:
            cls.me = cls()
        cls.task_queue.put((project_id,"classify",image))
        cls.me.classify_event.set()
        cls.me.run_event.set()
    
    @classmethod
    def create_stop_task(cls):
        if cls.me is None:
            cls.me = cls()
        cls.task_queue.put(("stop",))
        cls.me.stop_event.set()
        cls.me.run_event.set()

    @classmethod
    def get_instance(cls,train_event:Event,classify_event:Event,stop_event:Event,run_event:Event):
        if cls.me is None:
            cls.me = cls(train_event,classify_event,stop_event,run_event)
        return cls.me
        
    def pather(self,project_id:str,subs:list)->str:
        """
        Creates a path from the project_id and the subs relative to the projects_path

        Args:
            project_id (str): unique identifier of the project
            subs (list): list of subdirectories

        Returns:
            str: the path to the project
        """
        path = os.path.join(self.projects_path,project_id)
        for sub in subs:
            path = os.path.join(path,sub)
        return path
        
    def run(self):
        while self.run_event.is_set():
            try:
                self.task = self.task_queue.get()
                if self.train_event.is_set():
                    self.train()
                elif self.classify_event.is_set():
                    self.classify()
                elif self.stop_event.is_set():
                    self.stop()
                else:
                    self.status.put("waiting")
            except Exception as e:
                self.status.put(str(e))
                
    def train(self):
        self.status.put("prepare Dataset")
        self.create_dataset()
        self.status.put("Start Training")
        self.train_model()
        self.status.put("trained")
        
    
    def create_dataset(self):
        self.status.put("creating dataset")
        self.create_training_dir()
        self.create_test_dir()
        my_sets = self.get_sets_json()
        
        #Create data.yaml file
        self.status.put("creating data.yaml")
        root_path = "./"
        training_path = "training"
        testing_path = "test"
        my_labels = []
        for _, values in my_sets.items():
            for value in values:
                clean_val = value["label"].split(" ")[0:-1]
                clean_val = "_".join(clean_val)
                if clean_val not in my_labels:
                    my_labels.append(clean_val)
        self.create_data_yaml(root_path,training_path,testing_path,my_labels)
        
        #Splitting the images into training and test set
        self.status.put("splitting images")	
        test_keys = list(my_sets.keys())
        training_keys = []
        length = len(test_keys)
        while len(training_keys) < length * 0.8:
            key = random.choice(test_keys)
            test_keys.remove(key)
            training_keys.append(key)
            
        #Copy the images to the training and test directory
        self.status.put("copying images")
        for key in training_keys:
            my_from = self.pather(self.task[0],["images",key])
            my_to = self.pather(self.task[0],["training",key])
            shutil.copy(my_from,my_to)
        for key in test_keys:
            my_from = self.pather(self.task[0],["images",key])
            my_to = self.pather(self.task[0],["test",key])
            shutil.copy(my_from,my_to)
        
        #Create the labels files
        self.status.put("creating labels")
        from_diagonal_to_central = lambda x,y,w,h: (x+w/2,y+h/2,abs(w/2),abs(h/2))
        clean_val = lambda x: "_".join(x.split(" ")[0:-1])
        for key in training_keys:
            classes:list[dict] = my_sets[key]
            txt_lines = []
            for class_ in classes:
                x,y,w,h = from_diagonal_to_central(class_["x"],class_["y"],class_["w"],class_["h"])          
                l = [i for i,label in enumerate(my_labels) if label == clean_val(class_["label"])][0]
                line = f"{l} {x} {y} {w} {h}"
                txt_lines.append(line)
            with open(self.pather(self.task[0],["training",key.replace(".jpg",".txt")]),"w") as f:
                f.write("\n".join(txt_lines))
                
        for key in test_keys:
            classes:list[dict] = my_sets[key]
            txt_lines = []
            for class_ in classes:
                x,y,w,h = from_diagonal_to_central(class_["x"],class_["y"],class_["w"],class_["h"])
                l = [i for i,label in enumerate(my_labels) if label == clean_val(class_["label"])][0]
                line = f"{l} {x} {y} {w} {h}"
                txt_lines.append(line)
            with open(self.pather(self.task[0],["test",key.replace(".jpg",".txt")]),"w") as f:
                f.write("\n".join(txt_lines))
                
                                
        
            
            
    
    def create_training_dir(self):
        """
        Create the training directory for the project
        If the directory already exists, it will be deleted and recreated
        """
        training_path = self.pather(self.task[0],["training"])
        if not os.path.exists(training_path):
            os.makedirs(training_path)
        else:
            shutil.rmtree(training_path,ignore_errors=True)
            os.makedirs(training_path,exist_ok=True)
            
    def create_test_dir(self):
        """
        Create the test directory for the project
        If the directory already exists, it will be deleted and recreated
        """
        test_path = self.pather(self.task[0],["test"])
        if not os.path.exists(test_path):
            os.makedirs(test_path)
        else:
            shutil.rmtree(test_path,ignore_errors=True)
            os.makedirs(test_path,exist_ok=True)
            
    
    def create_data_yaml(self,root_path:str,training_path:str,testing_path:str,labels:list):
        """
        Create the data.yaml file for the project

        Args:
            root_path (str): root path of the project
            training_path (str): path to the training directory
            testing_path (str): path to the test directory
            labels (list): list of labels
        """
        data = {
            "path": ".\\",
            "train": os.path.join(root_path,training_path),
            "val": os.path.join(root_path,testing_path),
            "nc": len(labels),
            "names": labels,
            "task": "detect"
        }
        data_path = self.pather(self.task[0],["data.yaml"])
        with open(data_path,"w") as f:
            yaml.dump(data,f)
    
    def get_sets_json(self):
        sets = {}
        sets_path = self.pather(self.task[0],["annotations","sets.json"])
        if os.path.exists(sets_path):
            with open(sets_path) as f:
                sets = json.load(f)
        return sets
    
    def get_images_json(self):
        images = {}
        images_path = self.pather(self.task[0],"annotations","images.json")
        if os.path.exists(images_path):
            with open(images_path) as f:
                images = json.load(f)
        return images
    
    def train_model(self):
        """
        Train the model
        """
        data_path = self.pather(self.task[0],["data.yaml"])
        self.model = YOLO("yolov8n.pt")
        self.model.train()

    
    def classify(self):
        pass
    
    def stop(self):
        self.run_event.clear()
        self.status.put("stopped")