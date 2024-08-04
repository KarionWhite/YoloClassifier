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
        this.labelHistory = [];
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
        this.rect.label = this.labelCreation();
    }

    mouseUp(e){
        this.drag = false;
        if(this.killTosmallRects()){
            this.doubleClick(e);    //Wir wollten eigentlich doppeklick auslösen
            this.rect = {};
        }else{
            this.rects.push(this.rect);
        }
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

    setLabel(label){
        this.labelHistory.push(label);
    }

    labelCreation(){
        let posLabel = this.labelHistory.pop();
        let label = posLabel;
        if(posLabel === undefined){
            label = "Label";
            return this.labelIndexing(label);
        }
        this.labelHistory.push(posLabel);
        return this.labelIndexing(label);
    }

    labelIndexing(label) {
        let biggestIndex = 0;
        const baseLabel = label.trim()
      
        for (const element of this.rects) {
          const splittedLabel = element.label.split(" ");
          const elabel = splittedLabel.slice(0, -1).join(" "); // Basislabel des Elements
          const elIndexStr = splittedLabel[splittedLabel.length - 1];
      
          if (elabel === baseLabel && !isNaN(elIndexStr)) { // Formatierungsprüfung
            const elIndex = parseInt(elIndexStr, 10);
            if (elIndex >= biggestIndex) { // Größerer Index gefunden
              biggestIndex = elIndex + 1;
            }
          }
        }
      
        return `${baseLabel} ${biggestIndex}`;
    }

    draw() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        if (this.image !== null) {
            this.ctx.drawImage(this.image, 0, 0);
        }
        this.ctx.strokeStyle = 'red';
        this.ctx.lineWidth = 2;
        this.rects.forEach((rect, index) => {
            this.ctx.strokeRect(rect.x, rect.y, rect.w, rect.h);

            // Label anzeigen
            const labelText = rect.label;
            const labelWidth = this.ctx.measureText(labelText).width + 10; // Breite des Labels + Padding
            const labelHeight = 20; // Höhe des Labels

            this.ctx.fillStyle = 'rgba(0, 0, 0, 0.5)'; // Hintergrundfarbe mit Transparenz
            this.ctx.fillRect(rect.x, rect.y - labelHeight, labelWidth, labelHeight); // Hintergrund

            this.ctx.fillStyle = 'white';
            this.ctx.font = '12px Arial';
            this.ctx.fillText(labelText, rect.x + 5, rect.y - 5); // Label-Text
        });
        this.ctx.strokeRect(this.rect.x, this.rect.y, this.rect.w, this.rect.h);
    }

    killTosmallRects(){
        let killed = false;
        this.rects.forEach((element,index) => {
            if(Math.abs(element.w) * Math.abs(element.h) < 100){
                this.rects.splice(index,1);
                killed = true;
            }
        });
        return killed;
    }

    deleteLastRect(){
        this.rects.pop();
        this.draw();
    }

    updateCanvasSize(width, height) {
        this.canvas.width = width;
        this.canvas.height = height;
    }

    clear() {
        this.rects = [];
        this.draw();
    }

    setRects(rects){
        this.rects = rects;
    }

    getRects(){
        return this.rects;
    }
}

export default RectDrawing;