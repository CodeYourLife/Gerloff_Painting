let canvas, ctx;
let drawing = false;

/* =========================
   INIT
========================= */
function signatureCapture() {
    canvas = document.getElementById("newSignature");
    if (!canvas) return;

    ctx = canvas.getContext("2d");

    setTimeout(function() {
        resizeCanvas();
    }, 50);

    ctx.strokeStyle = "#000";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    canvas.addEventListener("mousedown", startDraw);
    canvas.addEventListener("mousemove", draw);
    canvas.addEventListener("mouseup", endDraw);
    canvas.addEventListener("mouseleave", endDraw);

    canvas.addEventListener("touchstart", startDraw, { passive: false });
    canvas.addEventListener("touchmove", draw, { passive: false });
    canvas.addEventListener("touchend", endDraw);
}

/* =========================
   DRAWING
========================= */
function startDraw(e) {
    e.preventDefault();
    drawing = true;

    const pos = getPos(e);

    lastX = pos.x;
    lastY = pos.y;

    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
}

function draw(e) {
    if (!drawing) return;
    e.preventDefault();

    const pos = getPos(e);

    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();

    lastX = pos.x;
    lastY = pos.y;
}



function endDraw(e) {
    if (!drawing) return;
    drawing = false;
    ctx.closePath();
}

/* =========================
   HELPERS
========================= */
function getPos(e) {
    const rect = canvas.getBoundingClientRect();

    let clientX, clientY;

    if (e.touches && e.touches[0]) {
        clientX = e.touches[0].clientX;
        clientY = e.touches[0].clientY;
    } else {
        clientX = e.clientX;
        clientY = e.clientY;
    }

    return {
        x: clientX - rect.left,
        y: clientY - rect.top
    };
}


function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

/* =========================
   SAVE / CLEAR
========================= */
function signatureSave2() {

    const canvas = document.getElementById("newSignature");

    // Create a smaller temporary canvas
    const tempCanvas = document.createElement("canvas");
    const scale = 0.7;  // 70% of original size

    tempCanvas.width = canvas.width * scale;
    tempCanvas.height = canvas.height * scale;

    const tempCtx = tempCanvas.getContext("2d");

    // White background (important for JPEG)
    tempCtx.fillStyle = "#ffffff";
    tempCtx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);

    // Draw scaled signature
    tempCtx.drawImage(canvas, 0, 0, tempCanvas.width, tempCanvas.height);

    // Export compressed JPEG (0.6 quality)
    const dataURL = tempCanvas.toDataURL("image/jpeg", 0.6);

    document.getElementById("signatureValue").value = dataURL;
    document.getElementById("saveSignature").src = dataURL;
    document.getElementById("saveSignature").style.display = "block";

    canvas.style.display = "none";
    document.getElementById("saveSignatureBtn").style.display = "none";
    document.getElementById("clearSignatureBtn").style.display = "none";

    document.getElementById("hide_until_signed").style.display = "block";
    document.getElementById("hide_until_signed2").style.display = "block";
}

function signatureClear() {
    resizeCanvas();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
}

/* =========================
   RESIZE
========================= */
window.addEventListener("resize", () => {
    if (canvas) resizeCanvas();
});
/* =========================
   RUN WHEN OPENING
========================= */
window.onload = function() {
	document.getElementById("hide_until_signed").style.display = "none";
	document.getElementById("hide_until_signed2").style.display = "none";
};