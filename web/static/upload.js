function _(el) {
  return document.getElementById(el);
}

function uploadFile() {
  _("progressBar").style.display = "block";
  var file = _("file").files[0];
  var formdata = new FormData();
  formdata.append("file", file);
  var xhr = new XMLHttpRequest();
  xhr.upload.addEventListener("progress", progressHandler, false);
  xhr.addEventListener("load", (event) => completeHandler(event, xhr), false);
  xhr.addEventListener("error", errorHandler, false);
  xhr.addEventListener("abort", abortHandler, false);
  xhr.open("POST", "/");
  xhr.send(formdata);
}

function progressHandler(event) {
  var percent = (event.loaded / event.total) * 100;
  _("progressBar").value = Math.round(percent);
}

function completeHandler(event, xhr) {
    if (xhr.readyState === xhr.DONE && xhr.status === 200) {
      var type = xhr.responseText.includes("error") ? "danger" : "success";
      appendAlert(xhr.responseText, type);
    } else {
      appendAlert('Unknown error.', 'danger');
    }
    _("progressBar").value = 0;
    _("progressBar").style.display = "none";
}

function errorHandler(event) {
  appendAlert('Upload failed.', 'danger');
}

function abortHandler(event) {
  appendAlert('Upload aborted.', 'danger');
}

const appendAlert = (message, type) => {
  var alertPlaceholder = _("upload_alert");
  const wrapper = document.createElement('div')
  wrapper.innerHTML = [
    `<div class="alert alert-${type} alert-dismissible" role="alert">`,
    `   <div>${message}</div>`,
    '   <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>',
    '</div>'
  ].join('');
  alertPlaceholder.append(wrapper);
}

function delete_files() {
  var filename = document.getElementById('delete-filename').textContent;
  var xhr = new XMLHttpRequest();
  xhr.addEventListener("load", (event) => window.location.assign("/"), false);
  xhr.open("DELETE", "/audio/" + filename);
  xhr.send({});
}

function add_event_delete_file_modal() {
    // set filenames automatically
    var el = document.getElementById('delete-modal');
    el.addEventListener('show.bs.modal', function (event) {
	var filename = event.relatedTarget.getAttribute('data-id');
	var el = document.getElementById('delete-filename');
	el.textContent = filename + '.*';
    });
}

function add_event_preview_modal() {
    // set filenames automatically
    var el = document.getElementById('preview-modal');
    el.addEventListener('show.bs.modal', function (event) {
	var filename = event.relatedTarget.getAttribute('data-id');
	var el = document.getElementById('preview-title');
	el.textContent = filename;

	var xhr = new XMLHttpRequest();
	xhr.addEventListener("load", (event) => {
	    var el = document.getElementById('preview-text');
	    el.innerHTML = xhr.responseText.replaceAll('\n', '\n<br/>');
	}, false);
	xhr.open("GET", "/audio/" + filename);
	xhr.send({});
    });
}

add_event_preview_modal();
add_event_delete_file_modal();
