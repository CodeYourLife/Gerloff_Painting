
function getVehicleData(driver, vin, date, mileage, notes){
    let formattedDate = new Date(date);
    stringDate = dateToYMD(formattedDate)
    document.getElementById('driver').value = driver.toString();
    document.getElementById('vin').value = vin;
    document.getElementById('datePurchased').value = stringDate;
    document.getElementById('mileage').value = mileage;
}

function showNotes(id, notes){
    let notesLog = ""
    notes.forEach((note) => {
        if (note.id == id) {
            notesLog += "Employee: " + note.name + "\n"
            notesLog += "Date: " + note.date + "\n"
            notesLog += "Note: " + note.note + "\n"
            notesLog += "----------------------------------" + "\n"
        }
    })
    document.getElementById("vehicleId").value = id
    document.getElementById('notesLog').innerHTML = notesLog;
}

function dateToYMD(date) {
    var d = date.getDate();
    var m = date.getMonth() + 1; //Month from 0 to 11
    var y = date.getFullYear();
    return '' + y + '-' + (m<=9 ? '0' + m : m) + '-' + (d <= 9 ? '0' + d : d);
}