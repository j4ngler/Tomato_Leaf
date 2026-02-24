const fileInput = document.getElementById("file-input");
const previewImg = document.getElementById("preview-image");
const previewContainer = document.getElementById("preview-container");
const detectBtn = document.getElementById("detect-btn");
const resultStatus = document.getElementById("result-status");
const resultList = document.getElementById("result-list");
const serverStatus = document.getElementById("server-status");

let selectedFile = null;

async function checkServerHealth() {
  try {
    const res = await fetch("/health");
    if (!res.ok) throw new Error();
    const data = await res.json();
    if (data.status === "ok") {
      serverStatus.textContent = "online";
      serverStatus.style.color = "#22c55e";
    } else {
      throw new Error();
    }
  } catch {
    serverStatus.textContent = "offline";
    serverStatus.style.color = "#f97316";
  }
}

checkServerHealth();

fileInput.addEventListener("change", (event) => {
  const file = event.target.files?.[0];
  if (!file) return;

  selectedFile = file;
  const reader = new FileReader();

  reader.onload = (e) => {
    previewImg.src = e.target.result;
    previewImg.style.display = "block";
    const placeholder = previewContainer.querySelector(".placeholder");
    if (placeholder) placeholder.remove();
  };

  reader.readAsDataURL(file);
  detectBtn.disabled = false;
  resultStatus.textContent = "Ảnh đã sẵn sàng. Bấm 'Phát hiện bệnh'.";
  resultList.innerHTML = "";
});

detectBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  detectBtn.disabled = true;
  detectBtn.textContent = "Đang phân tích...";
  resultStatus.textContent = "Đang gửi ảnh tới server và chạy mô hình...";
  resultList.innerHTML = "";

  try {
    const formData = new FormData();
    formData.append("file", selectedFile);

    const res = await fetch("/predict", {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    const { num_detections, diseases } = data;

    if (!num_detections || !diseases || diseases.length === 0) {
      resultStatus.textContent =
        "Không phát hiện được vùng bệnh rõ ràng. Hãy thử chụp gần hơn, rõ hơn.";
      return;
    }

    resultStatus.textContent = `Phát hiện ${num_detections} vùng nghi bệnh.`;
    resultList.innerHTML = "";

    diseases
      .sort((a, b) => b.confidence - a.confidence)
      .forEach((d) => {
        const li = document.createElement("li");
        li.className = "result-item";

        const header = document.createElement("div");
        header.className = "result-item-header";

        const name = document.createElement("div");
        name.textContent = d.name ?? `Class ${d.class_id}`;

        const confidence = document.createElement("span");
        confidence.className = "badge success";
        confidence.textContent = `${(d.confidence * 100).toFixed(1)}%`;

        header.appendChild(name);
        header.appendChild(confidence);

        const bbox = document.createElement("div");
        bbox.className = "bbox";
        if (d.bbox && d.bbox.length === 4) {
          const [x1, y1, x2, y2] = d.bbox.map((v) => Math.round(v));
          bbox.textContent = `BBox: x1=${x1}, y1=${y1}, x2=${x2}, y2=${y2}`;
        } else {
          bbox.textContent = "Không có thông tin bbox chi tiết.";
        }

        li.appendChild(header);
        li.appendChild(bbox);
        resultList.appendChild(li);
      });
  } catch (err) {
    console.error(err);
    resultStatus.textContent = `Lỗi khi phát hiện bệnh: ${err.message}`;
  } finally {
    detectBtn.disabled = !selectedFile;
    detectBtn.textContent = "Phát hiện bệnh";
  }
});

