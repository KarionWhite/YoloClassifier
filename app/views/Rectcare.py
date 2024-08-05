from typing import TypedDict
import json
import os


class LabelRect(TypedDict):
    x: int
    y: int
    w: int
    h: int
    label: str
    
class Rectcare:
    myClients = {}
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.__init_Rectcare()
        
    @classmethod
    def get_client(cls, project_id:str)->"Rectcare":
        if project_id in cls.myClients:
            return cls.myClients[project_id]
        return cls(project_id)
    
    @classmethod
    def delete_client(cls, project_id:str)->bool:
        if project_id in cls.myClients:
            del cls.myClients[project_id]
            return True
        return False
    
    """
    sets.json: 
    {
        "image_name":[
            {
                "x": 0,
                "y": 0,
                "w": 0,
                "h": 0,
                "label": "label"
            }
        ]
    }   
    """
    
    def __init_Rectcare(self):
        self.json_file = os.path.join(os.getcwd(),'yolores' ,'projects', self.project_id, 'annotations', 'sets.json')
        if not os.path.exists(self.json_file):
            with open(self.json_file, 'w') as f:
                json.dump({}, f)
        with open(self.json_file, 'r') as f:
            self.rects = json.load(f)
            
    def get_current_rects(self, image_name:str)->list[LabelRect]:
        if image_name in self.rects:
            return self.rects[image_name]
        return []
    
    def delete_rects(self, image_name:str)->bool:
        if image_name in self.rects:
            del self.rects[image_name]
            with open(self.json_file, 'w') as f:
                json.dump(self.rects, f, indent=4)
            return True
        return False
    
    def save_rects(self, image_name:str, rects:list[LabelRect])->bool:
        myrects:list[LabelRect] = []
        if image_name in self.rects:
            myrects = self.rects[image_name]
        for rect in rects['rects']:
            if all(key in rect for key in ['x', 'y', 'w', 'h', 'label']):
                myrect = {
                    "x": rect['x'],
                    "y": rect['y'],
                    "w": rect['w'],
                    "h": rect['h'],
                    "label": rect['label']
                }
                #prevent duplicates
                if myrect in myrects:
                    continue
                myrects.append(myrect)
        self.rects[image_name] = myrects
        with open(self.json_file, 'w') as f:
            json.dump(self.rects, f, indent=4)
        return True        