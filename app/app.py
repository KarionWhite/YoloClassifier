from flask import Flask, render_template, request, jsonify
import json
import os
import torch
import logging


app = Flask(__name__)

def check_cuda():
    cuda_available = torch.cuda.is_available()
    device_count = torch.cuda.device_count() if cuda_available else 0

    if cuda_available:
        logging.info(f"CUDA available with {device_count} device(s)")
        torch.cuda.empty_cache()
    else:
        logging.warning("CUDA is not available. Expect reduced performance.")


def create_app():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    app.config['DEBUG'] = True
    app.config['ENV'] = 'development'
    app.config['WATCH'] = True
    app.config['POJECT_JSON'] = os.path.join(os.getcwd(), 'yolores', 'projects.json')
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg','gif'}
    app.config['port'] = 8222
    from .views import(default,api)
    
    return app

    
    
def main():
    app = create_app()
    check_cuda()
    app.run(port=app.config['port'])
    
if __name__ == "__main__":
    main()