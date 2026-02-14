let canvas, ctx;
let drawing = false;

/* =========================
   INIT
========================= */
function signatureCapture() {
    canvas = document.getElementById("newSignature");
    if (!canvas) return;

    ctx = canvas.getContext("2d");

    resizeCanvas();

    ctx.strokeStyle = "#000";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";

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
    ctx.beginPath();

    const pos = getPos(e);
    ctx.moveTo(pos.x, pos.y);
}

function draw(e) {
    if (!drawing) return;
    e.preventDefault();

    const pos = getPos(e);
    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();
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
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    let x, y;
    if (e.touches && e.touches[0]) {
        x = (e.touches[0].clientX - rect.left) * scaleX;
        y = (e.touches[0].clientY - rect.top) * scaleY;
    } else {
        x = (e.clientX - rect.left) * scaleX;
        y = (e.clientY - rect.top) * scaleY;
    }
    return { x, y };
}

function resizeCanvas() {
    const ratio = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();

    canvas.width = rect.width * ratio;
    canvas.height = rect.height * ratio;

    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
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
    alert("HI")
	document.getElementById("hide_until_signed").style.display = "none";
	document.getElementById("hide_until_signed2").style.display = "none";
};