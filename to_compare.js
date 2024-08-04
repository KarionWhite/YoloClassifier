
$(document).ready(function() {
    const projectId = window.location.pathname.split('/')[3];
    const canvasId = "drawing-canvas";
    const projectClassify = new ProjectClassify(canvasId, projectId);
    $('#next-image-btn').click(function(event) {
        event.preventDefault();
        projectClassify.nextImage();
    });
    if(projectClassify.hasPreviousImage()){
        $('#prev-image-btn').show();
    }
    $('#prev-image-btn').click(function(event) {
        event.preventDefault();
        projectClassify.previousImage();
    });
    projectClassify.addEventListener('image-updated', (event) => {
        const currentImageIndex = event.detail.currentImageIndex;
        if(currentImageIndex > 0){
            $('#prev-image-btn').show();
        } else {
            $('#prev-image-btn').hide();
        }
    });
});

class ImageManager {
    constructor(canvas_id, projectId) {
        this.canvasId = canvas_id;
        this.projectId = projectId;

        //get canvas element
        this.canvasElement = document.getElementById(this.canvasId);

        this.currentImageIndex = 0;
        this.cachedImages = [];
        this.maxImages = parseInt(this.canvasElement.dataset.maxImages, 10);
        this.minCacheIndex = 0;
        this.maxCacheIndex = 0;
        this.allImagesLoaded = false;
        this.myRect = null;

        this.updateImage('current_image');
        window.addEventListener("beforeunload", this.postCurrentLabel.bind(this));
        window.addEventListener("unload", this.postCurrentLabel.bind(this));
        window.addEventListener("reset", this.postCurrentLabel.bind(this));
        
        this._listeners = {};

        //RectDrawing implementation
        this.rectDrawing = new RectDrawing(this.canvasId);
        
        this.addEventListener('image-updated', (event) => {
            this.rectDrawing.clear();
            const { image } = event.detail;
            this.rectDrawing.updateCanvasSize(image.width, image.height);
            this.rectDrawing.setBackGroundImage(image);
            this.rectDrawing.draw();
        });
    }

    addEventListener(eventName, listener) {
        if (!this._listeners[eventName]) {
            this._listeners[eventName] = [];
        }
        this._listeners[eventName].push(listener);
    }

    removeEventListener(eventName, listener) {
        const listeners = this._listeners[eventName];
        if (listeners) {
            const index = listeners.indexOf(listener);
            if (index > -1) {
                listeners.splice(index, 1);
            }
        }
    }

    dispatchEvent(eventName, detail) {
        const listeners = this._listeners[eventName];
        if (listeners) {
            for (const listener of listeners) {
                listener({ type: eventName, detail });
            }
        }
    }

    async fetchImages(endpoint) {
        if(endpoint !== "current_image"){
            await this.postCurrentLabel();
        } 
        const response = await fetch(`/api/classify/${endpoint}/${this.projectId}`, {
            cache: 'no-store', // Cache deaktivieren
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate', // Cache-Header setzen
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        });
        if (!response.ok) {
            console.error("Fehler beim Laden der Bilder");
            console.error(response.status);
        }
        const blob = await response.blob();
        const objectURL = URL.createObjectURL(blob);
    
        const label = response.headers.get("label");
        return [label,objectURL];
    }

    async fromCache(endpoint) {
        let myIndex = this.currentImageIndex;

        if (endpoint === 'next_image') {
            myIndex++;
        } else if (endpoint === 'last_image') {
            myIndex--;
        }

        // Bild aus dem Cache laden, falls vorhanden
        if (myIndex >= 0 && myIndex < this.cachedImages.length) {
            this.currentImageIndex = myIndex;
            return this.cachedImages[myIndex]; // Bilddaten direkt zurückgeben
        } else {
            // Bild von der API laden, falls nicht im Cache
            let [label, objectURL] = await this.fetchImages(endpoint);
            if (label === null) {
                console.error('Fehler beim Laden des Labels');
            }
            const img = new Image();
            img.src = objectURL;

            // Warten, bis das Bild geladen ist
            await new Promise(resolve => img.onload = resolve);

            const imageData = {
                label: label,
                image: img
            };

            if (endpoint === 'current_image') {
                this.cachedImages.push(imageData);
            } else if (endpoint === 'next_image' && myIndex < this.maxImages) {
                this.cachedImages.push(imageData);
                this.maxCacheIndex++;
            } else if (endpoint === 'last_image') {
                this.cachedImages.unshift(imageData);
                this.minCacheIndex++;
            }

            this.currentImageIndex = myIndex < 0 ? 0 : myIndex;

            if (this.maxCacheIndex + this.minCacheIndex >= this.maxImages - 1) {
                this.allImagesLoaded = true;
            }
            URL.revokeObjectURL(objectURL);

            return imageData;
        }
    }

    async postCurrentLabel(){
        const label = this.cachedImages[this.currentImageIndex].label;
        const response = await fetch(`/api/classify/currentLabel/${this.projectId}`, {
            method: 'POST',
            cache: 'no-store',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            },
            body: JSON.stringify({ label: label })
        });
        if (!response.ok) {
            console.error("Fehler beim Speichern des Labels");
            console.error(response.status);
        }
    }

    async updateImage(endpoint = 'next_image') {
        try {
            const { label, image } = await this.fromCache(endpoint);

            // Bild auf den Canvas zeichnen
            const ctx = this.canvasElement.getContext('2d');
            this.canvasElement.width = image.width;
            this.canvasElement.height = image.height;
            ctx.drawImage(image, 0, 0);
            
            this.dispatchEvent('image-updated', { label:label,image:image,currentImageIndex: this.currentImageIndex });

        } catch (error) {
            console.error('Fehler beim Aktualisieren des Bildes', error);
        }
    }

    async nextImage(){
        await this.updateImage('next_image');
    }

    async previousImage(){
        await this.updateImage('last_image');
    }

    async resetImages(){
        this.cachedImages.forEach((element) => {
            URL.revokeObjectURL(element.objectURL);
        });
        const response = await fetch(`/api/classify/reset/${projectId}`, {
            method: 'DELETE',
            cache: 'no-store',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        });
        if (!response.ok) {
            console.error("Fehler beim Zurücksetzen der Bilder");
            console.error(response.status);
        }
    
        this.cachedImages.length = 0;
        this.currentImageIndex = 0;
    }

    hasPreviousImage(){
        return this.currentImageIndex > 0;
    }
}


class RectDrawing{
    constructor(canvas_id){
        this.canvas = document.getElementById(canvas_id);
        if (this.canvas === null){
            console.log("Canvas not found!");
        }
        this.ctx = this.canvas.getContext("2d");
        this.rect = {};
        this.drag = false;
        this.startX = 0;
        this.startY = 0;
        this.rects = [];
        this.image = null;
        this.canvas.addEventListener('mousedown', this.mouseDown.bind(this));
        this.canvas.addEventListener('mouseup', this.mouseUp.bind(this));
        this.canvas.addEventListener('mousemove', this.mouseMove.bind(this));
        this.canvas.addEventListener('dblclick', this.doubleClick.bind(this));
    }

    mouseDown(e){
        this.drag = true;
        this.startX = e.offsetX;
        this.startY = e.offsetY;
        this.rect = {};
    }

    mouseUp(e){
        this.drag = false;
        this.rects.push(this.rect);
        this.draw();
    }

    mouseMove(e){
        if(this.drag){
            this.rect.w = e.offsetX - this.startX;
            this.rect.h = e.offsetY - this.startY;
            this.rect.x = this.startX;
            this.rect.y = this.startY;
            this.draw();
        }
    }

    doubleClick(e){
        this.rects.forEach((element,index) => {
            if(e.offsetX >= element.x && e.offsetX <= element.x + element.w && e.offsetY >= element.y && e.offsetY <= element.y + element.h){
                this.rects.splice(index,1);
            }
        });
        this.draw();
    }

    setBackGroundImage(image){
        this.image = image;
    }

    draw(){
        this.ctx.clearRect(0,0,this.canvas.width,this.canvas.height);
        if(this.image !== null){
            this.ctx.drawImage(this.image,0,0);
        }
        this.ctx.strokeStyle = 'red';
        this.ctx.lineWidth = 2;
        this.rects.forEach((element) => {
            this.ctx.strokeRect(element.x,element.y,element.w,element.h);
        });
    }

    updateCanvasSize(width, height) {
        this.canvas.width = width;
        this.canvas.height = height;
    }

    clear() {
        this.rects = [];
        this.draw();
    }
}