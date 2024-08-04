import ImageManager from "./project_ImageManager.js";


$(document).ready(function() {
    const projectId = window.location.pathname.split('/')[3];
    const canvasId = "drawing-canvas";
    const imageManager = new ImageManager(canvasId, projectId);
    $('#next-image-btn').click(function(event) {
        event.preventDefault();
        imageManager.nextImage();
    });
    if(imageManager.hasPreviousImage()){
        $('#prev-image-btn').show();
    }
    $('#prev-image-btn').click(function(event) {
        event.preventDefault();
        imageManager.previousImage();
    });
    imageManager.addEventListener('image-updated', (event) => {
        const currentImageIndex = event.detail.currentImageIndex;
        if(currentImageIndex > 0){
            $('#prev-image-btn').show();
        } else {
            $('#prev-image-btn').hide();
        }
    });

    //Eventlistener für Tastatur
    document.addEventListener("keydown", function(event) {
        //Für Rechtshänder
        if(event.key === "d"){
            imageManager.nextImage();
        } else if(event.key === "a"){
            imageManager.previousImage();
        } 
        //Für Linkshänder
        else if(event.key === "ArrowRight"){
            imageManager.nextImage();
        } else if(event.key === "ArrowLeft"){
            imageManager.previousImage();
        }
        //lösche letztes Rechteck
        else if(event.key === "x"){
            imageManager.rectDrawing.deleteLastRect();
        }
        else if(event.key === "Delete"){
            imageManager.rectDrawing.deleteLastRect();
        }
    });

    //Select für Label
    const labelSelect = document.getElementById("label-select");
    imageManager.setLabel(labelSelect.value);   //Setze Label auf das erste in der Liste
    labelSelect.addEventListener("change", function(event){
        imageManager.setLabel(labelSelect.value);
    });
});
