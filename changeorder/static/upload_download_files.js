// ************************ Drag and drop uploader ***************** //
 window.CSRF_TOKEN = "{{ csrf_token }}";
let dropArea = document.getElementById("drop-area")

// Prevent default drag behaviors
;['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
  dropArea.addEventListener(eventName, preventDefaults, false)
  document.body.addEventListener(eventName, preventDefaults, false)
})

// Highlight drop area when item is dragged over it
;['dragenter', 'dragover'].forEach(eventName => {
  dropArea.addEventListener(eventName, highlight, false)
})

;['dragleave', 'drop'].forEach(eventName => {
  dropArea.addEventListener(eventName, unhighlight, false)
})

// Handle dropped files
dropArea.addEventListener('drop', handleDrop, false)

function preventDefaults (e) {
  e.preventDefault()
  e.stopPropagation()
}

function highlight(e) {
  dropArea.classList.add('highlight')
}

function unhighlight(e) {
  dropArea.classList.remove('active')
}

function handleDrop(e) {
  var dt = e.dataTransfer
  var files = dt.files

  handleFiles(files)
}

let uploadProgress = []
let progressBar = document.getElementById('progress-bar')

function initializeProgress(numFiles) {
  progressBar.value = 0
  uploadProgress = []

  for(let i = numFiles; i > 0; i--) {
    uploadProgress.push(0)
  }
}

function updateProgress(fileNumber, percent) {
  uploadProgress[fileNumber] = percent
  let total = uploadProgress.reduce((tot, curr) => tot + curr, 0) / uploadProgress.length
  progressBar.value = total
}

function handleFiles(files, url, csrf) {
  files = [...files]
  //initializeProgress(files.length)
  files.forEach((file) => uploadFile(file, url, csrf))
  files.forEach(previewFile)
}

function previewFile(file, url) {
  let reader = new FileReader()
  reader.readAsDataURL(file)
  reader.onloadend = function() {
    let img = document.createElement('img')
    img.src = reader.result
    document.getElementById('gallery').appendChild(img)
  }
}$(document).ajaxSend(function(event, xhr, settings){
    if (!csrfSafeMethod(settings.type)) {
       xhr.setRequestHeader("X-CSRFToken", csrftoken);
    }
});
function uploadFile(file, url, csrf) {
  var xhr = new XMLHttpRequest()
  var formData = new FormData()
    // add assoc key values, this will be posts values
    formData.append("upload_file", true);
      xhr.open('POST', url, true)
      xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest')

      // Update progress (can be used to show progress indicator)
      xhr.upload.addEventListener("progress", function(e) {
        //updateProgress(i, (e.loaded * 100.0 / e.total) || 100)
      })

      xhr.addEventListener('readystatechange', function(e) {
        if (xhr.readyState == 4 && xhr.status == 200) {
          //updateProgress(i, 100) // <- Add this
        }
        else if (xhr.readyState == 4 && xhr.status != 200) {
          // Error. Inform the user
        }
      })
      formData.append('file', file)
      xhr.send(formData)
}

function downloadFile(id, url){
    $.ajax({
        method: 'GET',
        url: url,
        data: {'id':id},
        success: function (data) {
            text = "<ul>"
            parsedData = JSON.parse(data);
            parsedData.forEach((element) => {
                text += "<li class='folderItem'><div>" + element + "</div></li>";
            })
            text += "</ul>"
            document.getElementById("folderList").innerHTML = text;
               }
    })
}
function getFolderContents(id, url){
    $.ajax({
        method: 'GET',
        url: url,
        data: {'id':id},
        success: function (data) {
            text = "<ul>"
            parsedData = JSON.parse(data);
            parsedData.forEach((element) => {
                text += "<li class='folderItem'><div>" + element + "</div></li>";
            })
            text += "</ul>"
            document.getElementById("folderList").innerHTML = text;
               }
    })
}