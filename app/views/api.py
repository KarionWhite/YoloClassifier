from ..app import app
from flask import jsonify, abort, send_from_directory, url_for, request
from app.views.projectcare import get_projects, get_project_by_id, save_projects, init_project, save_project, save_labels,delete_project_with_id,UPLOADER,ClientImages
from app.views.Rectcare import Rectcare
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

@app.route('/api/classify/current_image/<project_id>', methods=['GET'])
def classify_current_image(project_id):
    ClientImages.delete_client(project_id)
    my_image = ClientImages.get_client(project_id)
    current_image_path = my_image.get_current_image_path()
    directory, filename = os.path.split(current_image_path)
    response = send_from_directory(directory, filename)
    response.headers['Cache-Control'] = 'no store'
    return response, 200, {'label': filename}
    

@app.route('/api/classify/next_image/<project_id>', methods=['GET'])
def classify_next_image(project_id):
    my_image = ClientImages.get_client(project_id)
    next_image_path = my_image.get_next_image_path()
    directory, filename = os.path.split(next_image_path)
    my_image.set_next_image()
    response = send_from_directory(directory, filename)
    response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache für 1 Tag
    return response, 200, {'label': filename}

@app.route('/api/classify/last_image/<project_id>', methods=['GET'])
def classify_last_image(project_id):
    my_image = ClientImages.get_client(project_id)
    last_image_path = my_image.get_last_image_path()
    directory, filename = os.path.split(last_image_path)
    my_image.set_last_image()
    response = send_from_directory(directory, filename)
    response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache für 1 Tag
    return response, 200, {'label': filename}
    
@app.route('/api/classify/max/<project_id>', methods=['GET'])
def get_max(project_id):
    my_image = ClientImages.get_client(project_id)
    mymax = my_image.getmax()
    return jsonify({"max":mymax}), 201

@app.route('/api/classify/reset/<project_id>', methods=['DELETE'])
def reset(project_id):
    deleted = ClientImages.delete_client(project_id)
    if deleted:
        return {}, 201
    else:
        return {}, 422
    
@app.route('/api/classify/currentLabel/<project_id>', methods=['POST'])
def sync_label(project_id):
    my_image = ClientImages.get_client(project_id)
    byte_data = request.data
    json_str = byte_data.decode('utf-8')
    data_dict = json.loads(json_str)
    #my_image.set_current_label(data_dict['label'])
    return {}, 201

@app.route('/api/classify/postrects/<project_id>', methods=['POST'])
def post_rects(project_id):
    my_image = ClientImages.get_client(project_id)
    byte_data = request.data
    json_str = byte_data.decode('utf-8')
    data_dict = json.loads(json_str)
    current_image = my_image.get_image_labels()[1]
    if not 'rects' in data_dict:
        logging.error(f"No rects in data_dict for image {current_image}")
        return {}, 422
    if data_dict['rects'] == []:     # wenn keine Rechtecke, dann nichts tun
        return {}, 201
    my_rectcare = Rectcare.get_client(project_id)
    my_rectcare.save_rects(current_image, data_dict)
    ClientImages.set_current_as_classified_image(project_id)
    return {}, 201

@app.route('/api/classify/receiveRects/<project_id>', methods=['GET'])
def receive_rects(project_id):
    my_image = ClientImages.get_client(project_id)
    current_image = my_image.get_image_labels()[1]
    my_rectcare = Rectcare.get_client(project_id)
    rects = my_rectcare.get_current_rects(current_image)
    return jsonify(rects), 201

@app.route('/api/classify/deleteRects/<project_id>', methods=['DELETE'])
def delete_rects(project_id):
    my_image = ClientImages.get_client(project_id)
    current_image = my_image.get_image_labels()[1]
    my_rectcare = Rectcare.get_client(project_id)
    my_rectcare.delete_rects(current_image)
    return {}, 201