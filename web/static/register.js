const statusEl = document.getElementById("status");
const videoEl = document.getElementById("video");
const canvasEl = document.getElementById("canvas");
const previewEl = document.getElementById("preview");
const startCameraBtn = document.getElementById("startCamera");
const captureBtn = document.getElementById("capture");
const uploadBtn = document.getElementById("upload");

let capturedBlob = null;
const token = window.REGISTRATION_TOKEN;

async function validateLink() {
  try {
    const res = await fetch(`/registration/link/${token}`);
    if (!res.ok) throw new Error("Invalid or expired link");
    const data = await res.json();
    statusEl.textContent = `Welcome ${data.guest_name}. Take a clear face photo.`;
  } catch (error) {
    statusEl.textContent = error.message;
    startCameraBtn.disabled = true;
  }
}

startCameraBtn.addEventListener("click", async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
    videoEl.srcObject = stream;
    captureBtn.disabled = false;
    statusEl.textContent = "Camera ready. Capture your photo.";
  } catch (error) {
    statusEl.textContent = "Camera permission denied.";
  }
});

captureBtn.addEventListener("click", () => {
  canvasEl.width = videoEl.videoWidth;
  canvasEl.height = videoEl.videoHeight;
  canvasEl.getContext("2d").drawImage(videoEl, 0, 0);
  canvasEl.toBlob((blob) => {
    capturedBlob = blob;
    previewEl.src = URL.createObjectURL(blob);
    previewEl.classList.remove("hidden");
    uploadBtn.disabled = false;
    statusEl.textContent = "Photo captured. Tap Upload.";
  }, "image/jpeg", 0.92);
});

uploadBtn.addEventListener("click", async () => {
  if (!capturedBlob) return;
  const formData = new FormData();
  formData.append("token", token);
  formData.append("image", capturedBlob, "face.jpg");

  try {
    const res = await fetch("/registration/upload-face", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Upload failed");
    statusEl.textContent = "Face registration completed successfully.";
    uploadBtn.disabled = true;
    captureBtn.disabled = true;
  } catch (error) {
    statusEl.textContent = error.message;
  }
});

validateLink();
