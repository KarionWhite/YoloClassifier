$(document).ready(function() {
    $('#uploadForm').submit(function(event) {
        event.preventDefault();
        const formData = new FormData(this);
        const projectId = formData.get('project_id');

        // Statusmeldung bei Beginn
        updateStatusMessage('Upload gestartet...', 'info');
        $('#back').prop('disabled', true); 
        $('#classify').prop('disabled', true);
        $('.progress').show(); 

        $.ajax({
            url: $(this).attr('action'),
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            xhr: function() {
                const xhr = new window.XMLHttpRequest();
                xhr.upload.addEventListener('progress', function(e) {
                if (e.lengthComputable) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    updateProgressBar(percentComplete);
                    $('#back').prop('disabled', true);
                    $('#classify').prop('disabled', false);
                    $('.progress').show();
                    }
                }, false);
                return xhr;
            },
            success: function(response) {
                if (response.error) {
                    updateStatusMessage(response.error, 'error');
                } else {
                    pollUploadStatus(projectId); // Start polling for updates
                }
            },
            error: function(error) {
                console.error(error);
                updateStatusMessage('Fehler beim Hochladen.', 'error');
            }
        });
    });

    function pollUploadStatus(projectId) {
        const intervalId = setInterval(() => {
            fetch(`/api/status_upload/${projectId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        updateStatusMessage(data.error, 'error');
                        clearInterval(intervalId);
                    } else {
                        updateProgressBar(data.progress);
                        updateStatusMessage(data.status);
                        if (data.status === 'uploading completed') {
                            clearInterval(intervalId);
                            handleUploadSuccess(data.status, projectId);
                        }
                    }
                })
                .catch(error => {
                    console.error('Fehler beim Abrufen des Fortschritts:', error);
                    clearInterval(intervalId);
                    updateStatusMessage('Fehler beim Hochladen.', 'error');
                });
        }, 1000);
    }

    function handleUploadSuccess(status, projectId) {
        if (status === 'uploading completed') {
            updateStatusMessage('Hochladen abgeschlossen.', 'success');
            $('#back').removeAttr('disabled');
            $('#classify').removeAttr('disabled');
            $('#uploadForm')[0].reset();
            setTimeout(() => {
                $('.progress').hide();
                $('#uploadStatus').html(``);
            }, 5000);
        }
    }

    function updateProgressBar(progress) {
        $('.progress-bar').width(progress + '%');
    }

    function updateStatusMessage(message, type = 'info') {
        $('#uploadStatus').html(`<div class="alert alert-${type}" role="alert">${message}</div>`);
    }
});
