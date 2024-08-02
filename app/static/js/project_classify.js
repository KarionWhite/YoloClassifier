//Hohle die links für die Bilder. last und next als lazy loading und current als load now
const projectId = window.location.pathname.split('/')[3];
let currentImageIndex = 0;

const json_Image = [];
let maxImages = 6;
let min_cache_index = 0;
let max_cache_index = 0;
let all_Images_loaded = false;


$(document).ready(function() {
    const imageContainer = document.getElementById("myImage");
    maxImages = parseInt(imageContainer.dataset.maxImages, 10); 


    updateImage('current_image');
    $('#next-image-btn').click(function(event) {
        event.preventDefault();
        updateImage('next_image');
    });
    if(currentImageIndex > 0){
        $('#prev-image-btn').show();
    }
    $('#prev-image-btn').click(function(event) {
        event.preventDefault();
        updateImage('last_image');
    });
});

async function fetchImages(endpoint) {
    if(endpoint !== "current_image"){
        postCurrentLabel();
    } 
    const response = await fetch(`/api/classify/${endpoint}/${projectId}`, {
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

async function fromcache(endpoint){
    let myIndex = currentImageIndex;
    let myimageBlob = null;
    if(endpoint === 'next_image'){
        myIndex++;
    }
    else if(endpoint === 'last_image'){
        myIndex--;
    }
    else{
        //current_image
        myIndex = 0;
        let [label,imageBlob] = await fetchImages('current_image');
        json_Image.push({label: label, imageBlob: imageBlob});
        myimageBlob = imageBlob;
        return myimageBlob;
    }
    if(myIndex < json_Image.length && myIndex >= 0){
        //Bild ist bereits geladen
        currentImageIndex = myIndex;
        myimageBlob = json_Image[myIndex].imageBlob;
    }
    else if(myIndex < 0 && !all_Images_loaded){
        //-1 bedeutet, dass wir ein neu geladenes Bild haben durch zurück gehen
        min_cache_index++;
        let [label,imageBlob] = await fetchImages('last_image');
        json_Image.unshift({label: label, imageBlob: imageBlob});
        currentImageIndex = 0;  //wir haben ein neues Bild, also ist der Index 0
        myimageBlob = imageBlob;
    }
    else if(myIndex < 0 && all_Images_loaded){
        currentImageIndex = json_Image.length-1
        myimageBlob = json_Image[currentImageIndex].imageBlob;
    }
    else if(myIndex < maxImages){
        max_cache_index++;
        let [label,imageBlob] = await fetchImages('next_image');
        json_Image.push({label: label, imageBlob: imageBlob});
        currentImageIndex = myIndex;
        myimageBlob = imageBlob;
    }
    else{
        //Wir haben alle Bilder und müssen nun zu 0 zurückkehren
        currentImageIndex = 0;
        all_Images_loaded = true;
        myimageBlob = json_Image[0].imageBlob;
    }
    if (max_cache_index + min_cache_index >= maxImages-1){
        //wir haben alle Bilder geladen
        all_Images_loaded = true;
    }
    return myimageBlob;
}

function finddouble(label){
    let count = 0;
    for(let i = 0; i < json_Image.length; i++){
        if(json_Image[i].label === label){
            count++;
        }
    }
    return count;
}

function findLabel(label){
    for(let i = 0; i < json_Image.length; i++){
        if(json_Image[i].label === label){
            return i;
        }
    }
    return -1;
}

async function postCurrentLabel(){
    const label = json_Image[currentImageIndex].label;
    const response = await fetch(`/api/classify/currentLabel/${projectId}`, {
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

async function updateImage(endpoint = 'next_image'){
    try{
        let imageURL = await fromcache(endpoint);
        image_container = document.getElementById("image-display");
        image_container.src = imageURL;
        image_container.alt = json_Image[currentImageIndex].label;
    }catch(error){
        console.error('Fehler beim Aufrufen des Bildes',error);
    }
    if(currentImageIndex > 0){
        $('#prev-image-btn').show();
    }   
}

async function resetImages(){
    json_Image.forEach((element) => {
        URL.revokeObjectURL(element.imageBlob);
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

    json_Image.length = 0;
    currentImageIndex = 0;
}

window.addEventListener("beforeunload", async function (e) {
    resetImages();
});

window.addEventListener("unload", async function (e) {
    resetImages();
});

window.addEventListener("reset", async function (e) {
    resetImages();
});