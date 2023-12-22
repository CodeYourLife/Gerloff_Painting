// ************************ Drag and drop uploader ***************** //
let dropArea = document.getElementById("drop-area")

function preventDefaults (e) {
  e.preventDefault()
  e.stopPropagation()
}

function highlight(e) {
    if (dropArea == null){
        dropArea = document.getElementById("drop-area")
    }
  preventDefaults(e)
  dropArea.classList.add('highlight')
}

function unhighlight(e) {
    if (dropArea == null){
        dropArea = document.getElementById("drop-area")
    }
    preventDefaults(e)
  dropArea.classList.remove('highlight')
}

function handleDrop(e, url, id, uploadUrl) {
  unhighlight(e)
  var dt = e.dataTransfer
  var files = dt.files
  handleFiles(files, url, id, uploadUrl)
}

function updateProgress(fileNumber, percent) {
  uploadProgress[fileNumber] = percent
  let total = uploadProgress.reduce((tot, curr) => tot + curr, 0) / uploadProgress.length
  progressBar.value = total
}

function handleFiles(files, url, id, uploadUrl) {
  files = [...files]
  names = []
  files.forEach(async file =>
  {
      names.push(file.name)
      await uploadFile(file, url, id)
  })
  getFolderContents(id, uploadUrl, names)
}

function uploadFile(file, url, id) {
  var xhr = new XMLHttpRequest()
  var formData = new FormData()
  xhr.open('POST', url, true)
  xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest')
  formData.append("id", id)
  formData.append("file", file)
  xhr.send(formData)
  return
}

function downloadFile(id, item){
    $.ajax({
        method: 'GET',
        url: '/changeorder/downloadFile',
        data: {'id':id, 'name': item.id},
        success: function (data) {
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = data;
            a.download = item.id;
            document.body.appendChild(a);
            a.click();
        }
    })
}

function getFolderContents(id, url, names=[]){
    document.getElementById("folderList").style.display = 'none';
    $.ajax({
        method: 'GET',
        url: url,
        data: {'id':id},
        success: function (data) {
            text = "<ul>"
            parsedData = JSON.parse(data);
            parsedData.forEach((element) => {
                text += "<li style='color: blue; cursor: pointer;' id='" + element + "' onclick='downloadFile(" + id + ", this)' class='folderItem'><div>" + element + "</div></li>";
            })
            text += "</ul>"
            document.getElementById("folderList").innerHTML = text;
               }

    })
    document.getElementById("folderList").style.display = 'block';
}