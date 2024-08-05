import RectDrawing from './project_RectDrawing.js';

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
        }
        else if(this.allImagesLoaded){
            //negativer overflow
            if(myIndex < 0){
                this.currentImageIndex = this.cachedImages.length - 1;
                return this.cachedImages[this.currentImageIndex];
            }
            //positiver overflow
            else if(myIndex >= this.cachedImages.length){
                this.currentImageIndex = 0;
                return this.cachedImages[this.currentImageIndex];
            }
        }
        else {
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
            } else if (endpoint === 'next_image' && myIndex < this.maxImages
            ) {
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

    async updateImage(endpoint = 'next_image',caching = false) {
        try {
            let image
            let label
            if(caching){
                let { mylabel, myimage } = await this.fromCache(endpoint);
                image = myimage;
                label = mylabel;
            }
            else{
                let [mylabel, objectURL] = await this.fetchImages(endpoint);
                label = mylabel;
                image = new Image();
                image.src = objectURL;
                await new Promise(resolve => image.onload = resolve);
                URL.revokeObjectURL(objectURL);
                this.currentImageIndex = 0;
                this.cachedImages.push({ label: label, image: image });
                if(endpoint !== 'current_image'){
                    this.cachedImages.shift();
                }
            }
            // Bild auf den Canvas zeichnen
            const ctx = this.canvasElement.getContext('2d');
            this.canvasElement.width = image.width;
            this.canvasElement.height = image.height;
            ctx.drawImage(image, 0, 0);
            
            this.dispatchEvent('image-updated', { label:label,image:image,currentImageIndex: this.currentImageIndex });
            await this.receiveRects();
        } catch (error) {
            console.error('Fehler beim Aktualisieren des Bildes', error);
        }
    }

    async nextImage(){
        await this.postRects();
        await this.updateImage('next_image');
    }

    async previousImage(){
        await this.postRects();
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

    //RectDrawing implementation
    
    deleteLastRect(){
        this.rectDrawing.deleteLastRect();
    }

    setLabel(label){
        this.rectDrawing.setLabel(label);
    }

    //Server RectDrawing implementation
    async postRects(){
        const rects = this.rectDrawing.getRects();
        const myrects = [];
        rects.forEach((element) => {
            if(element.color === 'red'){    //only save red rects because green rects are already saved
                myrects.push(element);
            }
        });
        const response = await fetch(`/api/classify/postrects/${this.projectId}`, {
            method: 'POST',
            cache: 'no-store',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            },
            body: JSON.stringify({ rects: myrects })
        });
        if (!response.ok) {
            console.error("Fehler beim Speichern der Rechtecke");
            console.error(response.status);
        }
        this.rectDrawing.resetRect();
    }

    async receiveRects(){
        const response = await fetch(`/api/classify/receiveRects/${this.projectId}`, {
            method: 'GET',
            cache: 'no-store',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            },
        });
        if (!response.ok) {
            console.error("Fehler beim Laden der Rechtecke");
            console.error(response.status);
        }
        const rects = await response.json();
        if (rects === undefined) {
            this.rectDrawing.draw();
            return;
        }
        if(rects.length === 0){
            this.rectDrawing.draw();
            return;
        }
        this.rectDrawing.setRects(rects, 'green');
        this.rectDrawing.draw();
    }

    async deleteRects(){
        const response = await fetch(`/api/classify/deleteRects/${this.projectId}`, {
            method: 'DELETE',
            cache: 'no-store',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        });
        if (!response.ok) {
            console.error("Fehler beim Löschen der Rechtecke");
            console.error(response.status);
        }
        this.rectDrawing.resetRect();
        this.rectDrawing.clear();
        this.rectDrawing.draw();
    }

}

export default ImageManager;