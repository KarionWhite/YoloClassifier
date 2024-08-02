//Hohle die links für die Bilder. last und next als lazy loading und current als load now
const projectId = window.location.pathname.split('/')[3];
let currentImageIndex = 0;

const json_Image = [
    {
        label: "{label1}",
        imageBlob: ""
    }
];


$(document).ready(function() {
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
    const response = await fetch(`/api/classify/${endpoint}/${projectId}`);
    if (!response.ok) {
        console.error("Fehler beim Laden der Bilder");
        console.error(response.status);
    }
    const blob = await response.blob();
    const objectURL = URL.createObjectURL(blob);

    const label = response.headers.get("label");
    json_Image.push({ label: label, imageBlob: objectURL });
    return objectURL;
}

async function fromcache(endpoint){
    myIndex = currentImageIndex;
    if(endpoint === 'next_image'){
        myIndex += 1;
    }
    else if(endpoint === 'last_image'){
        myIndex -= 1;
        if(myIndex < 0){
            myIndex = 0;
        }
    }
    if(myIndex < json_Image.length){
        currentImageIndex = myIndex;
        return json_Image[myIndex].imageBlob;
    }
    return null;
}

async function updateImage(endpoint = 'next_image'){
    try{
        let imageURL = await fromcache(endpoint);
        if(imageURL === null){
            imageURL = await fetchImages(endpoint);
            currentImageIndex = json_Image.length - 1;  //es wird immer nur das 1. oder das nächste Bild geladen, alles anderen sind im cache
        }
        image_container = document.getElementById("image-display");
        image_container.src = imageURL;
        image_container.alt = json_Image[currentImageIndex].label;
    }catch(error){
        console.error('Fehler beim Aufrufen des Bildes',error);
    }
}