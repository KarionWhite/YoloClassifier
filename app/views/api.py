from ..app import app
from flask import jsonify, abort, url_for, request
from app.views.projectcare import get_projects, get_project_by_id, save_projects, init_project, save_project, save_labels,delete_project_with_id,UPLOADER,ClientImages
import logging
import shutil
import json
import os

@app.route('/api/get_project/<project_id>', methods=['GET', 'POST'])
def get_project(project_id):
    path = os.path.join(app.config['POJECT_JSON'])
    with open(path, 'r') as f:
        projects = json.load(f)
    myProject = {}
    for project in projects:
        if project['id'] == project_id:
            myProject = project
            break
    retProject = {}
    #hohle Projektpath
    path_splitted = myProject['path'].split('/')
    project_path = os.getcwd()
    for path in path_splitted:
        project_path = os.path.join(project_path, path)
    # Teste, ob es den Pfad gibt
    if not os.path.exists(project_path):
        logging.error(f"Project path not found: {project_path}")
        return {'error': 'Project not found'}, 404  # 404 Not Found für fehlende Projekte

    # hole die Bilder
    images_path = os.path.join(project_path, 'images')
    cimages = []
    for image in os.listdir(images_path):
        cimages.append(url_for('serve_project_image', project_id=project_id, image=image))

    # hole die labels
    labels = []
    labels_path = os.path.join(project_path, 'annotations', 'labels.json')
    try:
        with open(labels_path, 'r') as f:
            labels = json.load(f)
    except FileNotFoundError:
        logging.error(f"Labels file not found: {labels_path}")
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON file: {labels_path}")

    retProject['images'] = cimages
    retProject['labels'] = labels
    retProject['description'] = myProject['description']
    retProject['id'] = myProject['id']
    retProject['name'] = myProject['name']
    return retProject
    
    
@app.route('/api/new_project', methods=['GET','POST'])
def new_project():
    projects = get_projects()
    new_project = {}
    new_project['id'] = "project" + str(len(projects)+1)
    new_project['name'] = request.form['name']
    new_project['description'] = request.form['description']
    new_project['path'] = "yolores/projects/" + new_project['id']
    #prüfe, ob es das Projekt schon gibt
    for project in projects:
        if project['name'] == new_project['name']:
            return {'error': 'Project already exists'}, 201 #response ok, aber Projekt schon vorhanden
    projects.append(new_project)
    save_projects(projects)
    init_project(new_project,labels=request.form['labels'])
    return {'id': new_project['id']}, 201

@app.route('/api/edit_project/<project_id>', methods=['GET','POST'])
def edit_project(project_id):
    myProject = get_project_by_id(project_id)
    myProject['name'] = request.form['name']
    myProject['description'] = request.form['description']
    save_project(myProject)
    save_labels(project_id, request.form['labels'])
    return {'id': myProject['id']}, 201

@app.route('/api/delete_project/<project_id>', methods=['GET','POST'])
def delete_project(project_id):
    awns = delete_project_with_id(project_id)
    if 'error' in awns:
        logging.error(awns['error'])
        return awns, 404
    return awns, 201


@app.route('/api/upload_images/<project_id>', methods=['POST'])
def upload_images(project_id):
    UPLOADER(project_id,request)
    return {},201

@app.route('/api/status_upload/<project_id>', methods=['GET'])
def status_upload(project_id):
    status = UPLOADER.get_status(project_id)
    
    errors = [err for err in status if 'error' in err]
    staties = [stat for stat in status if 'status' in stat]
    progress = [prog for prog in status if 'progress' in prog]
    ret = {}
    if len(errors) > 0:
        ret['error'] = errors[-1]['error']
    if len(staties) > 0:
        ret['status'] = staties[-1]['status']
    if progress:
        ret['progress'] = progress[-1]['progress']
    
    return jsonify(ret), 201

@app.route('/api/classify/next_image/<project_id>', methods=['GET'])
def classify_next_image(prohect_id):
    my_image = ClientImages.get_client(prohect_id)
    new_last = my_image.get_image_path()
    new_current = my_image.set_next_image()
    new_next = my_image.get_image_path()
    return {'last': new_last, 'current': new_current, 'next': new_next}, 200

@app.route('/api/classify/last_image/<project_id>', methods=['POST'])
def classify_last_image(project_id):
    my_image = ClientImages.get_client(project_id)
    new_last = my_image.get_image_path()
    new_current = my_image.set_last_image()
    new_next = my_image.get_image_path()
    return {'last': new_last, 'current': new_current, 'next': new_next}, 200