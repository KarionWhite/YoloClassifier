document.addEventListener('DOMContentLoaded', function() {
    Array.from(document.getElementsByClassName("rounded-card"))
        .forEach(function(card) {
            card.addEventListener("click", function() {
                const yolo_project_id = card.getAttribute("data-yolo-model");
                if (yolo_project_id == "new") {
                    window.location.href = "/new_project";
                }
                else{
                    fetch('/api/get_project/' + yolo_project_id)
                    .then(response => response.json())
                    .then(data => {
                        if(data.error) {
                            console.log(data.error);
                            return;
                        }
                        let imageHtml = "";
                        var i = 100;
                        for (const image of data.images) {
                            imageHtml += `<div class="col-10">
                            <img src="` + image + `" class="img-fluid my-img" alt="Responsive image">
                            </div>`;
                            i--;
                            if(i == 0) {
                                break;
                            }
                        }
                        $('#yoloDetails').html(`
                        <div class="container-fluid project-show">
                            <h1 class="protitel">${data.name} 
                                <a href="/project/edit/${data.id}" class="btn btn-sm btn-outline-light">
                                    <i class="bi bi-pencil"></i> Bearbeiten
                                </a>
                            </h1>
                            <p class="prodesc">${data.description}</p>
                            <div class="image-gallery">${imageHtml}</div>
                            <p class="prolabel">Labels: ${data.labels.join(", ")}</p>
                        </div>
                        `);
                    })
                }
            });
        });

        $('#newProjectForm').submit(function(event) {
            event.preventDefault();
            const formData = new FormData(this);
    
            $.ajax({
                url: $(this).attr('action'),
                type: 'POST',
                data: formData,
                processData: false,
                contentType: false,
                success: function(response) {
                    if (response.error) { // Überprüfen auf Fehlermeldung vom Server
                        alert(response.error); // Fehlermeldung anzeigen (oder andere UI-Elemente verwenden)
                    } else {
                        console.log(response);
                        window.location.href = "/project/edit/" + response.id;
                    }
                },
                error: function(error) {
                    console.error(error);
                }
            });
        });
        $('#delete_project').click(function(event) {
            event.preventDefault();
            const url = window.location.pathname;
            const projectIdMatch = url.split('/');
            const projectId = projectIdMatch[projectIdMatch.length - 1];
            if(confirm("Möchten Sie das Projekt wirklich löschen?")) {
                $.ajax({
                    url: '/api/delete_project/' + projectId,
                    type: 'POST',
                    success: function(response) {
                        if (response.error) {
                            alert(response.error);
                            window.location.href = "/";
                        } else {
                            window.location.href = "/";
                        }
                    },
                    error: function(error) {
                        console.error(error);
                        alert("Fehler beim Löschen des Projekts");
                        window.location.href = "/api/edit/" + projectId;
                    },
                    complete: function() {
                        // Ladeanzeige ausblenden und Button wieder aktivieren
                        $('#delete_project').prop('disabled', false).html('Projekt löschen');
                    }
                });
            }
        });


        //weiterer Code
});