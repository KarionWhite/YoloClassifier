from app.views.projectcare import get_projects, get_project_by_id, get_project_labels, ClientImages
from flask import render_template,send_from_directory, abort
from ..app import app
import logging
import json
import os


@app.route('/')
def home():
    yolo_projects = get_projects()
    return render_template('index.html', yolo_projects=yolo_projects)

@app.route('/upload')
def upload():
    return render_template('upload.html')

@app.route('/upload_image/<project_id>')
def upload_image(project_id):
    myProject = get_project_by_id(project_id)
    if myProject == {}:
        abort(404)
    return render_template('project_upload_images.html', project=myProject)

@app.route('/classify')
def classify():
    return render_template('classify.html')

@app.route('/images/<project_id>/<image>')
def serve_project_image(project_id, image):
    myProject = get_project_by_id(project_id)
    if myProject == {}:
        abort(404)  # Projekt nicht gefunden
    path_splitted = myProject['path'].split('/')
    project_path = os.getcwd()
    for path in path_splitted:
        project_path = os.path.join(project_path, path)
    images_path = os.path.join(project_path, 'images')
    if not os.path.exists(os.path.join(images_path, image)):
        abort(404)  # Bild nicht gefunden
    response = send_from_directory(images_path, image)
    response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache für 1 Tag
    return response

@app.route('/new_project')
def new_project_form():
    return render_template('new_project.html')


@app.route('/project/edit/<project_id>')
def edit_project_form(project_id):
    myProject = get_project_by_id(project_id)
    if myProject == {}:
        abort(404)  # Projekt nicht gefunden
    labels = get_project_labels(project_id)
    labels = ', '.join(labels)
    myProject['labels'] = labels
    return render_template('project_edit.html', project=myProject)

@app.route('/project/classify/<project_id>')
def classify_project_form(project_id):
    myProject = get_project_by_id(project_id)
    if myProject == {}:
        abort(404)
    myclient_images = ClientImages.get_client(project_id)
    max_images = myclient_images.getmax()
    my_labels = get_project_labels(project_id)
    return render_template('project_classify.html', project=myProject, max_images=max_images, labels=my_labels)