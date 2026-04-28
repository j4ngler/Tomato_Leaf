const API = "";
const $ = (id) => document.getElementById(id);
const modeBtn = $("modeBtn");
const modeTag = $("modeTag");
const modeTagInline = $("modeTagInline");
const themeToggle = $("themeToggle");
const deviceControls = $("deviceControls");
const autoModeHint = $("autoModeHint");
const sidebarStatus = $("sidebarStatus");
const sidebarSync = $("sidebarSync");
const tempEl = $("temp");
const humidEl = $("humid");
const lightEl = $("light");
const soilEl = $("soil");
const analysisEl = $("analysis");
const sensorTimeEl = $("sensorTime");
const eventLogEl = $("eventLog");
const applyThresholdsBtn = $("applyThresholds");
const toastRoot = $("toastRoot");
const liveImage = $("liveImage");
const liveVideoDashboard = $("liveVideoDashboard");
const dashboardCameraFallbackHint = $("dashboardCameraFallbackHint");
const liveVideoCamera = $("liveVideoCamera");
const splitSelect = $("splitSelect");
const frameName = $("frameName");
const liveImageCamera = $("liveImageCamera");
const cameraLiveFrame = $("cameraLiveFrame");
const cameraLivePlaceholder = $("cameraLivePlaceholder");
const liveImagePtz = $("liveImagePtz");
const ptzLiveFrame = $("ptzLiveFrame");
const frameNameCamera = $("frameNameCamera");
const analysisCamera = $("analysisCamera");
const eventLogHistory = $("eventLogHistory");
const splitSelectCamera = $("splitSelectCamera");
const cameraSourceSelect = $("cameraSourceSelect");
const cameraSourceSelectCamera = $("cameraSourceSelectCamera");
const burstCountInput = $("burstCount");
const burstIntervalInput = $("burstInterval");
const scheduleAtInput = $("scheduleAt");
const scheduleStatus = $("scheduleStatus");
const menuItems = document.querySelectorAll(".menu-item[data-page]");
const footerSyncText = $("footerSyncText");
const aiInsightText = $("aiInsightText");
const aiInsightBody = $("aiInsightBody");
const deviceOrbButtons = document.querySelectorAll("[data-device-btn]");

let manual = true;
let trendChart = null;
let frameTimer = null;
let sensorTimer = null;
let scheduleStatusTimer = null;
let activeSplit = "train";
let cameraSource = "dataset";
/** Server có CAM_RTSP_URL + OpenCV — cho phép chọn RTSP Live */
let rtspStreamReady = false;
/** URL frame dataset mới nhất (đồng bộ PTZ khi không dùng RTSP) */
let lastDatasetFrameUrl = "";
let dashboardWebcamStream = null;
let usingWebcamFallback = false;
let lastCameraNoticeMode = "";
const RTSP_STREAM_URL = "/api/camera/rtsp/stream.mjpg";
const RTSP_SNAPSHOT_URL = "/api/camera/rtsp/snapshot.jpg";
const THEME_KEY = "tomatoleaf-theme";

function pad2(n) {
  return String(n).padStart(2, "0");
}

function nowTimeString() {
  const d = new Date();
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
}

function toLocalDatetimeInputValue(d) {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}T${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

function createLogItem(message, time = null, author = "TomatoLeaf Bot") {
  const li = document.createElement("li");
  const avatar = document.createElement("span");
  avatar.className = "chat-avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = "TL";

  const bubble = document.createElement("div");
  bubble.className = "chat-bubble";

  const authorEl = document.createElement("strong");
  authorEl.className = "chat-bubble__author";
  authorEl.textContent = author;

  const msgEl = document.createElement("p");
  msgEl.className = "chat-bubble__text";
  msgEl.textContent = message || "";

  const timeEl = document.createElement("time");
  timeEl.className = "chat-bubble__time";
  timeEl.dateTime = new Date().toISOString();
  timeEl.textContent = time || nowTimeString();

  bubble.append(authorEl, msgEl, timeEl);
  li.append(avatar, bubble);
  return li;
}

function appendLog(message, time = null) {
  if (!eventLogEl || !message) return;
  const li = createLogItem(message, time);
  eventLogEl.prepend(li);
  while (eventLogEl.children.length > 40) {
    eventLogEl.removeChild(eventLogEl.lastChild);
  }
}

function showToast(message, variant = "success") {
  if (!toastRoot) return;
  const el = document.createElement("div");
  el.className = `toast toast--${variant}`;
  el.setAttribute("role", "status");
  el.textContent = message;
  toastRoot.appendChild(el);
  window.setTimeout(() => {
    el.style.opacity = "0";
    el.style.transform = "translateY(8px)";
    el.style.transition = "opacity 0.22s ease, transform 0.22s ease";
    window.setTimeout(() => el.remove(), 240);
  }, 3200);
}

function syncModeUi() {
  const manualText = "THỦ CÔNG";
  const autoText = "TỰ ĐỘNG";
  if (modeTag) {
    modeTag.textContent = manual ? manualText : autoText;
    modeTag.classList.toggle("badge", true);
    modeTag.classList.toggle("badge-mode", true);
    if (manual) {
      modeTag.style.background = "var(--badge-manual-bg)";
      modeTag.style.color = "var(--badge-manual-text)";
    } else {
      modeTag.style.background = "var(--badge-auto-bg)";
      modeTag.style.color = "var(--badge-auto-text)";
    }
  }
  if (modeTagInline) {
    modeTagInline.textContent = manual ? manualText : autoText;
    if (manual) {
      modeTagInline.style.background = "var(--badge-manual-bg)";
      modeTagInline.style.color = "var(--badge-manual-text)";
    } else {
      modeTagInline.style.background = "var(--badge-auto-bg)";
      modeTagInline.style.color = "var(--badge-auto-text)";
    }
  }
  if (deviceControls) {
    deviceControls.setAttribute("data-manual", manual ? "true" : "false");
    const fs = deviceControls.querySelector(".device-fieldset");
    if (fs) fs.disabled = !manual;
  }
  if (autoModeHint) {
    autoModeHint.classList.toggle("is-hidden", manual);
  }
  if (modeBtn) {
    modeBtn.setAttribute("aria-pressed", manual ? "true" : "false");
  }
  const modeTextEl = $("automationModeText");
  if (modeTextEl) modeTextEl.textContent = manual ? "THỦ CÔNG" : "TỰ ĐỘNG";
}

function activatePage(pageId) {
  document.querySelectorAll(".page-section").forEach((sec) => {
    sec.classList.toggle("is-active", sec.id === `page-${pageId}`);
  });
  menuItems.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.page === pageId);
  });
  void syncDashboardCameraPreview();
  syncLiveVideoForCurrentSource();
  resyncPtzPreview();
}

function syncCameraSourceUi() {
  document.querySelectorAll(".video-tools-split").forEach((el) => {
    el.classList.toggle("is-hidden", cameraSource === "rtsp");
  });
  if (cameraSourceSelect) cameraSourceSelect.value = cameraSource;
  if (cameraSourceSelectCamera) cameraSourceSelectCamera.value = cameraSource;
}

function applyRtspModeUi() {
  if (analysisEl) {
    analysisEl.textContent = "Luồng RTSP (chưa có bbox YOLO)";
    analysisEl.className = "analysis-pill analysis-pill--ok";
  }
  if (analysisCamera) {
    analysisCamera.textContent = "Luồng RTSP";
    analysisCamera.className = "analysis-pill analysis-pill--ok";
  }
  if (aiInsightText) {
    aiInsightText.classList.remove("ai-insight--warn");
    if (aiInsightBody) {
      aiInsightBody.textContent =
        "Luồng RTSP chỉ xem trực tiếp. Chuyển sang Dataset YOLO để phân tích có bounding box.";
    } else {
      aiInsightText.textContent =
        "AI Insight: Luồng RTSP chỉ xem trực tiếp. Chuyển sang Dataset YOLO để phân tích có bounding box.";
    }
  }
  if (frameName) frameName.textContent = "RTSP Live";
  if (frameNameCamera) frameNameCamera.textContent = "RTSP Live";
  if (sidebarStatus) {
    sidebarStatus.textContent = "Luồng RTSP";
    sidebarStatus.style.color = "#67e8f9";
  }
}

function setPtzPreviewReady(ready) {
  if (ptzLiveFrame) {
    ptzLiveFrame.classList.toggle("is-stream-ready", !!ready);
  }
}

function syncLiveVideoForCurrentSource() {
  if (cameraSource !== "rtsp") return;
  if (!rtspStreamReady) return;
  if (liveImage) liveImage.src = RTSP_STREAM_URL;
  if (liveImageCamera) {
    setCameraLiveStreamReady(false);
    liveImageCamera.onload = () => setCameraLiveStreamReady(true);
    liveImageCamera.onerror = () => setCameraLiveStreamReady(false);
    liveImageCamera.src = RTSP_STREAM_URL;
    if (liveImageCamera.complete && liveImageCamera.naturalHeight > 0) {
      setCameraLiveStreamReady(true);
    }
  }
  if (liveImagePtz) {
    setPtzPreviewReady(false);
    liveImagePtz.onload = () => setPtzPreviewReady(true);
    liveImagePtz.onerror = () => setPtzPreviewReady(false);
    liveImagePtz.src = RTSP_STREAM_URL;
    if (liveImagePtz.complete && liveImagePtz.naturalHeight > 0) {
      setPtzPreviewReady(true);
    }
  }
}

function stopDashboardWebcam() {
  if (!dashboardWebcamStream) return;
  dashboardWebcamStream.getTracks().forEach((track) => track.stop());
  dashboardWebcamStream = null;
  usingWebcamFallback = false;
  if (liveVideoDashboard) {
    liveVideoDashboard.srcObject = null;
    liveVideoDashboard.style.display = "none";
  }
  if (liveVideoCamera) {
    liveVideoCamera.srcObject = null;
    liveVideoCamera.style.display = "none";
  }
}

function setDashboardHint(message = "") {
  if (!dashboardCameraFallbackHint) return;
  dashboardCameraFallbackHint.textContent = message;
  dashboardCameraFallbackHint.style.display = message ? "flex" : "none";
}

function setCameraLiveHint(message = "") {
  if (!cameraLivePlaceholder) return;
  cameraLivePlaceholder.textContent = message || "Kết nối camera…";
}

function notifyCameraMode(mode, message, variant = "success") {
  if (lastCameraNoticeMode === mode) return;
  lastCameraNoticeMode = mode;
  showToast(message, variant);
}

async function startDashboardWebcam() {
  if (!liveVideoDashboard && !liveVideoCamera) return false;
  if (!navigator.mediaDevices?.getUserMedia) return false;
  if (!dashboardWebcamStream) {
    dashboardWebcamStream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: false,
    });
  }
  if (liveVideoDashboard) {
    liveVideoDashboard.srcObject = dashboardWebcamStream;
    liveVideoDashboard.style.display = "block";
  }
  if (liveVideoCamera) {
    liveVideoCamera.srcObject = dashboardWebcamStream;
    liveVideoCamera.style.display = "block";
  }
  if (liveImage) liveImage.style.display = "none";
  if (liveImageCamera) liveImageCamera.style.display = "none";
  setCameraLiveStreamReady(true);
  setCameraLiveHint("Webcam máy tính");
  setDashboardHint("");
  await Promise.allSettled([liveVideoDashboard?.play?.(), liveVideoCamera?.play?.()]);
  usingWebcamFallback = true;
  return true;
}

async function probeRtspAvailable() {
  try {
    const info = await api("/api/camera/stream/info");
    return (
      info?.stream_ready === true &&
      info?.has_live_frame === true &&
      !info?.error
    );
  } catch {
    return false;
  }
}

async function syncDashboardCameraPreview() {
  rtspStreamReady = await probeRtspAvailable();
  if (rtspStreamReady) {
    stopDashboardWebcam();
    if (liveImage) {
      liveImage.style.display = "block";
      liveImage.src = `${RTSP_STREAM_URL}?_t=${Date.now()}`;
    }
    if (liveImageCamera) {
      liveImageCamera.style.display = "block";
      liveImageCamera.src = `${RTSP_STREAM_URL}?_t=${Date.now()}`;
    }
    setCameraLiveStreamReady(true);
    setCameraLiveHint("RTSP Live");
    setDashboardHint("");
    notifyCameraMode("rtsp", "Đang hiển thị RTSP Live.");
    usingWebcamFallback = false;
    return;
  }
  const host = window.location.hostname || "";
  const secureLikeLocalhost =
    window.isSecureContext || host === "localhost" || host === "127.0.0.1";
  if (!secureLikeLocalhost) {
    if (liveImage) liveImage.style.display = "none";
    if (liveImageCamera) liveImageCamera.style.display = "none";
    if (liveVideoDashboard) liveVideoDashboard.style.display = "none";
    if (liveVideoCamera) liveVideoCamera.style.display = "none";
    setDashboardHint("Không thể mở webcam trên kết nối không bảo mật. Hãy mở bằng http://localhost:5500.");
    setCameraLiveHint("Không thể mở webcam (không bảo mật).");
    appendLog("Webcam fallback bị chặn do context không bảo mật (không phải localhost/https).");
    setCameraLiveStreamReady(false);
    notifyCameraMode(
      "insecure",
      "Không thể mở webcam trên kết nối không bảo mật. Hãy mở bằng http://localhost:5500.",
      "error"
    );
    return;
  }
  try {
    if (usingWebcamFallback && dashboardWebcamStream) {
      if (liveImage) liveImage.style.display = "none";
      if (liveImageCamera) liveImageCamera.style.display = "none";
      if (liveVideoDashboard) liveVideoDashboard.style.display = "block";
      if (liveVideoCamera) liveVideoCamera.style.display = "block";
      setCameraLiveStreamReady(true);
      setCameraLiveHint("Webcam máy tính");
      setDashboardHint("");
      return;
    }
    const webcamReady = await startDashboardWebcam();
    if (!webcamReady) {
      if (liveImage) liveImage.style.display = "none";
      if (liveImageCamera) liveImageCamera.style.display = "none";
      setDashboardHint("Không truy cập được webcam máy tính.");
      setCameraLiveHint("Không truy cập được webcam máy tính.");
      setCameraLiveStreamReady(false);
      notifyCameraMode("webcam-error", "Không tìm thấy RTSP và không truy cập được webcam.", "error");
    } else {
      appendLog("RTSP chưa sẵn sàng, đang dùng webcam máy tính.");
      notifyCameraMode("webcam", "RTSP chưa sẵn sàng, đang hiển thị webcam máy tính.");
    }
  } catch (err) {
    if (liveImage) liveImage.style.display = "none";
    if (liveImageCamera) liveImageCamera.style.display = "none";
    if (liveVideoDashboard) liveVideoDashboard.style.display = "none";
    if (liveVideoCamera) liveVideoCamera.style.display = "none";
    setDashboardHint("Webcam bị chặn. Hãy cho phép quyền camera cho trình duyệt.");
    setCameraLiveHint("Webcam bị chặn. Hãy cho phép quyền camera.");
    setCameraLiveStreamReady(false);
    notifyCameraMode("webcam-blocked", `Không mở được webcam: ${err.message}`, "error");
  }
}

function downloadWebcamSnapshot() {
  if (!liveVideoDashboard || !liveVideoDashboard.videoWidth || !liveVideoDashboard.videoHeight) {
    throw new Error("Webcam chưa sẵn sàng.");
  }
  const canvas = document.createElement("canvas");
  canvas.width = liveVideoDashboard.videoWidth;
  canvas.height = liveVideoDashboard.videoHeight;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("Không tạo được ảnh từ webcam.");
  }
  ctx.drawImage(liveVideoDashboard, 0, 0, canvas.width, canvas.height);
  const a = document.createElement("a");
  a.href = canvas.toDataURL("image/jpeg", 0.92);
  a.download = `webcam_${Date.now()}.jpg`;
  a.click();
}

function captureWebcamBlob() {
  if (!liveVideoDashboard || !liveVideoDashboard.videoWidth || !liveVideoDashboard.videoHeight) {
    throw new Error("Webcam chưa sẵn sàng.");
  }
  const canvas = document.createElement("canvas");
  canvas.width = liveVideoDashboard.videoWidth;
  canvas.height = liveVideoDashboard.videoHeight;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("Không tạo được ảnh từ webcam.");
  }
  ctx.drawImage(liveVideoDashboard, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error("Không tạo được blob ảnh webcam."));
          return;
        }
        resolve(blob);
      },
      "image/jpeg",
      0.92
    );
  });
}

async function runDetectFromBlob(imageBlob) {
  const form = new FormData();
  form.append("file", imageBlob, `capture_${Date.now()}.jpg`);
  const res = await fetch(`${API}/api/camera/detect`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const text = await res.text();
    let msg = text || `HTTP ${res.status}`;
    try {
      const parsed = JSON.parse(text || "{}");
      if (parsed && typeof parsed.detail === "string" && parsed.detail.trim()) {
        msg = parsed.detail.trim();
      }
    } catch {
      // keep text fallback
    }
    throw new Error(msg);
  }
  const out = await res.json();
  if (out?.image_data_url) {
    if (liveImage) {
      liveImage.src = out.image_data_url;
      liveImage.style.display = "block";
    }
    if (liveImageCamera) {
      liveImageCamera.src = out.image_data_url;
      liveImageCamera.style.display = "block";
    }
    if (liveVideoDashboard) liveVideoDashboard.style.display = "none";
    if (liveVideoCamera) liveVideoCamera.style.display = "none";
  }
  setAnalysisFromDisease({
    label: out?.top_disease || "Không phát hiện",
    severity: getSeverity(out?.top_disease || ""),
  });
  const n = Number(out?.num_detections || 0);
  showToast(`Đã chụp và detect: ${n} bbox`, "success");
  appendLog(`Detect ảnh chụp: ${out?.top_disease || "Không phát hiện"} (${n} bbox).`);
}

/** Khi đổi tab (ví dụ sang PTZ) cần gán lại preview nếu đang dùng dataset. */
function resyncPtzPreview() {
  if (!liveImagePtz) return;
  if (cameraSource === "rtsp") {
    if (!rtspStreamReady) return;
    setPtzPreviewReady(false);
    liveImagePtz.onload = () => setPtzPreviewReady(true);
    liveImagePtz.onerror = () => setPtzPreviewReady(false);
    liveImagePtz.src = RTSP_STREAM_URL;
    if (liveImagePtz.complete && liveImagePtz.naturalHeight > 0) {
      setPtzPreviewReady(true);
    }
    return;
  }
  const url = lastDatasetFrameUrl || liveImage?.src;
  if (!url) return;
  setPtzPreviewReady(false);
  liveImagePtz.onload = () => setPtzPreviewReady(true);
  liveImagePtz.onerror = () => setPtzPreviewReady(false);
  liveImagePtz.src = url;
  if (liveImagePtz.complete && liveImagePtz.naturalHeight > 0) {
    setPtzPreviewReady(true);
  }
}

async function applyCameraSource(next) {
  cameraSource = next;
  syncCameraSourceUi();
  if (next === "rtsp") {
    if (liveImage) liveImage.src = RTSP_STREAM_URL;
    if (liveImageCamera) {
      setCameraLiveStreamReady(false);
      liveImageCamera.onload = () => setCameraLiveStreamReady(true);
      liveImageCamera.onerror = () => setCameraLiveStreamReady(false);
      liveImageCamera.src = RTSP_STREAM_URL;
    }
    if (liveImagePtz) {
      setPtzPreviewReady(false);
      liveImagePtz.onload = () => setPtzPreviewReady(true);
      liveImagePtz.onerror = () => setPtzPreviewReady(false);
      liveImagePtz.src = RTSP_STREAM_URL;
    }
    applyRtspModeUi();
    appendLog("Đã chuyển sang luồng RTSP.");
  } else {
    await refreshFrame();
    appendLog("Đã chuyển sang Dataset YOLO.");
  }
}

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    let msg = text || `HTTP ${res.status}`;
    try {
      const parsed = JSON.parse(text || "{}");
      if (parsed && typeof parsed.detail === "string" && parsed.detail.trim()) {
        msg = parsed.detail.trim();
      }
    } catch {
      // keep raw text fallback
    }
    throw new Error(msg);
  }
  return res.json();
}

function chartThemeColors() {
  const dark = document.documentElement.getAttribute("data-theme") === "dark";
  return {
    grid: dark ? "rgba(71, 85, 105, 0.25)" : "rgba(148, 163, 184, 0.24)",
    ticks: dark ? "#94a3b8" : "#64748b",
  };
}

function initTrendChart() {
  const canvas = document.getElementById("chartTrends");
  if (!canvas || typeof Chart === "undefined") return;

  if (trendChart) {
    trendChart.destroy();
    trendChart = null;
  }

  const c = chartThemeColors();

  const gradientFill = (chart, rgbaTop, rgbaBottom) => {
    const { ctx, chartArea } = chart;
    if (!chartArea) return rgbaBottom;
    const g = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
    g.addColorStop(0, rgbaTop);
    g.addColorStop(1, rgbaBottom);
    return g;
  };

  trendChart = new Chart(canvas, {
    type: "line",
    data: {
      labels: ["06:00", "09:00", "12:00", "15:00", "18:00", "21:00"],
      datasets: [
        {
          label: "Nhiệt độ",
          data: [28.2, 29.1, 31.4, 30.8, 29.6, 28.0],
          tension: 0.38,
          fill: true,
          borderWidth: 2.5,
          borderColor: "#2563eb",
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: "#ffffff",
          pointBorderColor: "#2563eb",
          pointBorderWidth: 2,
          backgroundColor: (ctx) => {
            const ch = ctx.chart;
            return gradientFill(
              ch,
              "rgba(37, 99, 235, 0.38)",
              "rgba(37, 99, 235, 0.02)"
            );
          },
        },
        {
          label: "Độ ẩm không khí",
          data: [58, 55, 52, 56, 60, 59],
          tension: 0.38,
          fill: true,
          borderWidth: 2.2,
          borderColor: "#60a5fa",
          pointRadius: 2,
          backgroundColor: (ctx) => {
            const ch = ctx.chart;
            return gradientFill(
              ch,
              "rgba(34, 197, 94, 0.32)",
              "rgba(34, 197, 94, 0.02)"
            );
          },
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          position: "right",
          align: "end",
          labels: {
            color: c.ticks,
            usePointStyle: true,
            boxWidth: 8,
            boxHeight: 8,
            padding: 16,
            font: { family: "Inter, system-ui, sans-serif", size: 12 },
          },
        },
        tooltip: {
          backgroundColor: "rgba(15, 23, 42, 0.94)",
          titleColor: "#f8fafc",
          bodyColor: "#e2e8f0",
          padding: 12,
          cornerRadius: 10,
          displayColors: true,
        },
      },
      scales: {
        x: {
          grid: { color: c.grid, drawBorder: false },
          ticks: { color: c.ticks, maxRotation: 0, font: { size: 11 } },
        },
        y: {
          grid: { color: c.grid, drawBorder: false },
          ticks: { color: c.ticks, font: { size: 11 } },
        },
      },
    },
  });
}

function applyChartTheme() {
  if (!trendChart) return;
  const c = chartThemeColors();
  const x = trendChart.options.scales.x;
  const y = trendChart.options.scales.y;
  x.grid.color = c.grid;
  y.grid.color = c.grid;
  x.ticks.color = c.ticks;
  y.ticks.color = c.ticks;
  trendChart.options.plugins.legend.labels.color = c.ticks;
  trendChart.update();
}

function loadTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  const prefersDark =
    window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches;
  const dark = saved === "dark" || (!saved && prefersDark);
  document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  if (themeToggle) {
    themeToggle.setAttribute("aria-pressed", dark ? "true" : "false");
  }
}

function toggleTheme() {
  const next =
    document.documentElement.getAttribute("data-theme") === "dark"
      ? "light"
      : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem(THEME_KEY, next === "dark" ? "dark" : "light");
  if (themeToggle) {
    themeToggle.setAttribute("aria-pressed", next === "dark" ? "true" : "false");
  }
  applyChartTheme();
}

function setAnalysisFromDisease(d) {
  if (!analysisEl) return;
  const viMap = {
    "Early blight": "Bệnh úa sớm",
    "Bacterial spot": "Đốm vi khuẩn",
    "Yellow Leaf Curl Virus": "Virus xoăn lá vàng",
  };
  const vi = viMap[d.label] || d.label;
  analysisEl.textContent = `${vi} (${d.label})`;
  analysisEl.className = `analysis-pill analysis-pill--${d.severity || "ok"}`;
  if (analysisCamera) {
    analysisCamera.textContent = `${vi} (${d.label})`;
    analysisCamera.className = `analysis-pill analysis-pill--${d.severity || "ok"}`;
  }

  if (aiInsightText) {
    aiInsightText.classList.toggle("ai-insight--warn", d.severity === "warn" || d.severity === "danger");
    if (d.label === "Early blight") {
      if (aiInsightBody) {
        aiInsightBody.textContent =
          "Phát hiện Early blight. Đề xuất giảm độ ẩm xuống ~50% và bật quạt hút ẩm trong 2 giờ.";
      } else {
        aiInsightText.textContent =
          "AI Insight: Phát hiện Early blight. Đề xuất giảm độ ẩm xuống ~50% và bật quạt hút ẩm trong 2 giờ.";
      }
    } else if (d.label === "Bacterial spot") {
      if (aiInsightBody) {
        aiInsightBody.textContent =
          "Phát hiện Bacterial spot. Đề xuất tăng thông gió, hạn chế đọng nước trên lá.";
      } else {
        aiInsightText.textContent =
          "AI Insight: Phát hiện Bacterial spot. Đề xuất tăng thông gió, hạn chế đọng nước trên lá.";
      }
    } else if (d.label === "Yellow Leaf Curl Virus") {
      if (aiInsightBody) {
        aiInsightBody.textContent =
          "Phát hiện Yellow Leaf Curl Virus. Đề xuất cách ly cây và tăng giám sát sâu môi giới.";
      } else {
        aiInsightText.textContent =
          "AI Insight: Phát hiện Yellow Leaf Curl Virus. Đề xuất cách ly cây và tăng giám sát sâu môi giới.";
      }
    } else {
      if (aiInsightBody) {
        aiInsightBody.textContent = "Không phát hiện bất thường đáng kể.";
      } else {
        aiInsightText.textContent = "AI Insight: Không phát hiện bất thường đáng kể.";
      }
    }
  }

  if (sidebarStatus) {
    if (d.severity === "danger") {
      sidebarStatus.textContent = "Cảnh báo";
      sidebarStatus.style.color = "#fca5a5";
    } else if (d.severity === "warn") {
      sidebarStatus.textContent = "Theo dõi";
      sidebarStatus.style.color = "#fdba74";
    } else {
      sidebarStatus.textContent = "Ổn định";
      sidebarStatus.style.color = "#74e79f";
    }
  }
}

loadTheme();
syncModeUi();
appendLog("Khởi động dashboard điều khiển...");
initTrendChart();

themeToggle?.addEventListener("click", toggleTheme);

modeBtn?.addEventListener("click", () => {
  const next = !manual;
  api("/api/control/mode", {
    method: "POST",
    body: JSON.stringify({ manual: next }),
  })
    .then((data) => {
      manual = !!data.manual;
      syncModeUi();
      appendLog(manual ? "Chuyển chế độ THỦ CÔNG." : "Chuyển chế độ TỰ ĐỘNG.");
      showToast("Đã cập nhật chế độ vận hành");
    })
    .catch((err) => showToast(`Lỗi đổi chế độ: ${err.message}`, "error"));
});

function getSeverity(labelText) {
  const s = (labelText || "").toLowerCase();
  if (s.includes("virus")) return "danger";
  if (s.includes("spot") || s.includes("blight")) return "warn";
  if (s.includes("không phát hiện") || s.includes("no detection")) return "ok";
  return "ok";
}

async function refreshSensors() {
  try {
    const s = await api("/api/sensors");
    tempEl.textContent = `${s.temperature} °C`;
    humidEl.textContent = `${s.humidity} %`;
    lightEl.textContent = `${s.light} lux`;
    soilEl.textContent = `${s.soil} %`;
    if (sensorTimeEl) sensorTimeEl.textContent = s.updated_at || nowTimeString();
    if (sidebarSync) sidebarSync.textContent = `Đồng bộ: ${s.updated_at || nowTimeString()}`;
    if (footerSyncText) {
      footerSyncText.textContent = `Dữ liệu được cập nhật từ Trạm cảm biến #1 vào ${s.updated_at || nowTimeString()}`;
    }
  } catch (err) {
    showToast(`Lỗi lấy cảm biến: ${err.message}`, "error");
  }
}

function setCameraLiveStreamReady(ready) {
  if (cameraLiveFrame) {
    cameraLiveFrame.classList.toggle("is-stream-ready", !!ready);
  }
}

async function refreshFrame() {
  if (cameraSource === "rtsp") {
    return;
  }
  try {
    const data = await api(`/api/camera/next?split=${encodeURIComponent(activeSplit)}`);
    if (liveImage) liveImage.src = data.image_url;
    lastDatasetFrameUrl = data.image_url || "";
    if (liveImageCamera) {
      setCameraLiveStreamReady(false);
      const onDone = () => setCameraLiveStreamReady(true);
      liveImageCamera.onload = onDone;
      liveImageCamera.onerror = () => setCameraLiveStreamReady(false);
      liveImageCamera.src = data.image_url;
      if (liveImageCamera.complete && liveImageCamera.naturalHeight > 0) {
        onDone();
      }
    }
    if (liveImagePtz) {
      setPtzPreviewReady(false);
      const onPtz = () => setPtzPreviewReady(true);
      liveImagePtz.onload = onPtz;
      liveImagePtz.onerror = () => setPtzPreviewReady(false);
      liveImagePtz.src = data.image_url;
      if (liveImagePtz.complete && liveImagePtz.naturalHeight > 0) {
        onPtz();
      }
    }
    const top = data.top_disease || data.detections?.[0]?.name || "Không phát hiện";
    if (frameName) frameName.textContent = `Bệnh: ${top}`;
    if (frameNameCamera) frameNameCamera.textContent = `Bệnh: ${top}`;
    setAnalysisFromDisease({ label: top, severity: getSeverity(top) });
  } catch (err) {
    showToast(`Lỗi lấy frame: ${err.message}`, "error");
  }
}

async function refreshLogs() {
  try {
    const logs = await api("/api/logs?limit=30");
    if (!eventLogEl) return;
    eventLogEl.innerHTML = "";
    logs.forEach((x) => {
      eventLogEl.appendChild(createLogItem(x.message || "", x.time || "--:--:--"));
    });
    if (eventLogHistory) {
      eventLogHistory.innerHTML = eventLogEl.innerHTML;
    }
  } catch {
    // keep local logs if API lỗi
  }
}

async function refreshSystemState() {
  try {
    const s = await api("/api/system/state");
    manual = !!s.manual;
    syncModeUi();
    Object.entries(s.devices || {}).forEach(([dev, st]) => {
      const btn = document.querySelector(`[data-device-btn="${dev}"]`);
      if (btn) btn.classList.toggle("is-on", !!st);
    });
    $("automationPump").textContent = s.devices?.pump ? "ON" : "OFF";
    $("automationFanCool").textContent = s.devices?.["fan-cool"] ? "ON" : "OFF";
    $("automationFanDehum").textContent = s.devices?.["fan-dehum"] ? "ON" : "OFF";
    $("automationLight").textContent = s.devices?.light ? "ON" : "OFF";
  } catch (err) {
    showToast(`Lỗi trạng thái hệ thống: ${err.message}`, "error");
  }
}

async function refreshScheduleStatus() {
  if (!scheduleStatus) return;
  try {
    const data = await api("/api/camera/capture/schedule");
    if (!data.has_job) {
      scheduleStatus.textContent = "Chưa có lịch chụp.";
      return;
    }
    const base = `Lịch: ${data.status || "unknown"} - ${data.count} ảnh, mỗi ${data.interval_sec}s, nguồn ${data.source}.`;
    if (data.status === "scheduled") {
      scheduleStatus.textContent = `${base} Thời điểm: ${data.run_at}`;
      return;
    }
    if (data.status === "done") {
      scheduleStatus.textContent = `${base} Hoàn tất, lưu ${data.captured_files?.length || 0} ảnh tại ${data.saved_dir}.`;
      return;
    }
    if (data.status === "cancelled") {
      scheduleStatus.textContent = "Lịch chụp đã được huỷ.";
      return;
    }
    if (data.status === "error") {
      scheduleStatus.textContent = `Lịch chụp lỗi: ${data.error || "unknown"}`;
      return;
    }
    scheduleStatus.textContent = base;
  } catch (err) {
    scheduleStatus.textContent = `Không đọc được trạng thái lịch: ${err.message}`;
  }
}

applyThresholdsBtn?.addEventListener("click", () => {
  const soilMin = document.getElementById("soilMin")?.value;
  const soilMax = document.getElementById("soilMax")?.value;
  const tempMin = document.getElementById("tempMin")?.value;
  const tempMax = document.getElementById("tempMax")?.value;
  const humidMin = document.getElementById("humidMin")?.value;
  const humidMax = document.getElementById("humidMax")?.value;
  appendLog(
    `Đã lưu ngưỡng: đất ${soilMin}-${soilMax}%, nhiệt độ ${tempMin}-${tempMax}°C, ẩm KK ${humidMin}-${humidMax}%.`
  );
  showToast("Cập nhật ngưỡng thành công!", "success");
});

deviceOrbButtons.forEach((btn) => {
  btn.addEventListener("click", async () => {
    const device = btn.dataset.deviceBtn;
    const nextState = !btn.classList.contains("is-on");
    try {
      await api("/api/control/device", {
        method: "POST",
        body: JSON.stringify({ device, state: nextState }),
      });
      btn.classList.toggle("is-on", nextState);
      appendLog(`Thiết bị ${device}: ${nextState ? "BẬT" : "TẮT"}.`);
      await refreshSystemState();
    } catch (err) {
      showToast(`Không thể đổi thiết bị: ${err.message}`, "error");
    }
  });
});

document.querySelectorAll("[data-ptz]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const action = btn.dataset.ptz;
    try {
      await api("/api/camera/ptz", {
        method: "POST",
        body: JSON.stringify({ action }),
      });
      appendLog(`Lệnh PTZ: ${action}`);
    } catch (err) {
      showToast(`Lỗi PTZ: ${err.message}`, "error");
    }
  });
});

$("btnCapture")?.addEventListener("click", async () => {
  try {
    let imageBlob;
    if (rtspStreamReady) {
      const res = await fetch(`${RTSP_SNAPSHOT_URL}?_t=${Date.now()}`);
      if (!res.ok) {
        throw new Error("Không lấy được snapshot RTSP.");
      }
      imageBlob = await res.blob();
    } else {
      imageBlob = await captureWebcamBlob();
    }
    await runDetectFromBlob(imageBlob);
  } catch (err) {
    showToast(`Chụp/detect thất bại: ${err.message}`, "error");
  }
});

$("btnBurstCapture")?.addEventListener("click", async () => {
  const count = Number(burstCountInput?.value || 5);
  const intervalSec = Number(burstIntervalInput?.value || 3);
  if (!Number.isFinite(count) || count < 1 || count > 30) {
    showToast("Số ảnh phải từ 1 đến 30.", "error");
    return;
  }
  if (!Number.isFinite(intervalSec) || intervalSec < 0.5 || intervalSec > 60) {
    showToast("Khoảng cách phải từ 0.5 đến 60 giây.", "error");
    return;
  }
  const source = cameraSource === "rtsp" ? "rtsp" : "dataset";
  try {
    const out = await api("/api/camera/capture/burst", {
      method: "POST",
      body: JSON.stringify({
        count,
        interval_sec: intervalSec,
        source,
        split: activeSplit,
      }),
    });
    showToast(`Đã chụp ${out.count} ảnh liên tiếp`, "success");
    appendLog(`Chụp liên tiếp ${out.count} ảnh (${source}, mỗi ${intervalSec}s).`);
  } catch (err) {
    showToast(`Chụp liên tiếp lỗi: ${err.message}`, "error");
  }
});

$("btnScheduleCapture")?.addEventListener("click", async () => {
  const at = scheduleAtInput?.value || "";
  if (!at) {
    showToast("Chọn thời điểm hẹn giờ trước.", "error");
    return;
  }
  const selected = new Date(at);
  if (Number.isNaN(selected.getTime())) {
    showToast("Thời điểm hẹn giờ không hợp lệ.", "error");
    return;
  }
  const now = new Date();
  if (selected.getTime() <= now.getTime()) {
    showToast("Thời điểm hẹn giờ phải ở tương lai.", "error");
    return;
  }
  const count = Number(burstCountInput?.value || 5);
  const intervalSec = Number(burstIntervalInput?.value || 3);
  const source = cameraSource === "rtsp" ? "rtsp" : "dataset";
  try {
    const out = await api("/api/camera/capture/schedule", {
      method: "POST",
      body: JSON.stringify({
        run_at: at,
        count,
        interval_sec: intervalSec,
        source,
        split: activeSplit,
      }),
    });
    showToast("Đã đặt lịch chụp", "success");
    appendLog(`Đặt lịch chụp lúc ${out.run_at}.`);
    await refreshScheduleStatus();
  } catch (err) {
    showToast(`Đặt lịch lỗi: ${err.message}`, "error");
  }
});

$("btnCancelSchedule")?.addEventListener("click", async () => {
  try {
    const out = await api("/api/camera/capture/schedule/cancel", { method: "POST", body: "{}" });
    if (out.cancelled) {
      showToast("Đã huỷ lịch chụp", "success");
      appendLog("Đã huỷ lịch chụp.");
    } else {
      showToast("Không có lịch chụp đang chờ.");
    }
    await refreshScheduleStatus();
  } catch (err) {
    showToast(`Huỷ lịch lỗi: ${err.message}`, "error");
  }
});

document.querySelectorAll("[data-step-target]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const target = btn.dataset.stepTarget;
    const input = target ? $(target) : null;
    if (!input) return;
    const delta = Number(btn.dataset.step || 0);
    const min = Number(input.min || "-999999");
    const max = Number(input.max || "999999");
    const current = Number(input.value || 0);
    if (!Number.isFinite(current) || !Number.isFinite(delta)) return;
    const next = Math.min(max, Math.max(min, current + delta));
    input.value = String(next);
  });
});

$("btnSave")?.addEventListener("click", () => {
  if (rtspStreamReady) {
    const a = document.createElement("a");
    a.href = RTSP_SNAPSHOT_URL;
    a.download = `rtsp_${Date.now()}.jpg`;
    a.click();
    showToast("Đã tải ảnh RTSP");
    return;
  }
  try {
    downloadWebcamSnapshot();
    showToast("Đã tải ảnh webcam");
  } catch (err) {
    showToast(`Không tải được ảnh webcam: ${err.message}`, "error");
  }
});

$("btnHandleNow")?.addEventListener("click", async () => {
  const text = analysisEl?.textContent || "";
  try {
    if (text.includes("Early blight")) {
      document.getElementById("humidMax").value = "50";
      document.getElementById("soilMax").value = "65";
      $("applyThresholds")?.click();
      await api("/api/control/mode", {
        method: "POST",
        body: JSON.stringify({ manual: true }),
      });
      await api("/api/control/device", {
        method: "POST",
        body: JSON.stringify({ device: "fan-dehum", state: true }),
      });
      showToast("Đã áp dụng xử lý nhanh cho Early blight", "success");
    } else {
      showToast("Đã ghi nhận khuyến nghị AI", "success");
    }
    await refreshSystemState();
  } catch (err) {
    showToast(`Xử lý nhanh thất bại: ${err.message}`, "error");
  }
});

splitSelect?.addEventListener("change", async (e) => {
  activeSplit = e.target.value;
  if (splitSelectCamera) splitSelectCamera.value = activeSplit;
  if (cameraSource !== "rtsp") await refreshFrame();
});

splitSelectCamera?.addEventListener("change", async (e) => {
  activeSplit = e.target.value;
  if (splitSelect) splitSelect.value = activeSplit;
  if (cameraSource !== "rtsp") await refreshFrame();
});

async function onCameraSourceChange(e) {
  const v = e.target.value;
  await applyCameraSource(v === "rtsp" ? "rtsp" : "dataset");
}

cameraSourceSelect?.addEventListener("change", onCameraSourceChange);
cameraSourceSelectCamera?.addEventListener("change", onCameraSourceChange);

menuItems.forEach((btn) => {
  btn.addEventListener("click", () => activatePage(btn.dataset.page));
});

$("applyThresholdsAutomation")?.addEventListener("click", () => {
  $("applyThresholds")?.click();
});

$("btnAutoSample")?.addEventListener("click", () => {
  appendLog("Đã chạy kiểm tra tự động (mô phỏng).");
  showToast("Đã chạy kiểm tra tự động", "success");
});

async function bootstrap() {
  activatePage("dashboard");
  await refreshSystemState();
  await refreshSensors();
  try {
    const info = await api("/api/camera/stream/info");
    rtspStreamReady = info.stream_ready === true && info.has_live_frame === true;
    const enableRtsp = rtspStreamReady;
    [cameraSourceSelect, cameraSourceSelectCamera].forEach((sel) => {
      if (!sel) return;
      const opt = sel.querySelector('option[value="rtsp"]');
      if (opt) {
        opt.disabled = !enableRtsp;
        opt.textContent = enableRtsp ? "RTSP Live" : "RTSP (chưa cấu hình)";
      }
    });
    if (info.error && enableRtsp) {
      appendLog(`RTSP: ${info.error}`);
    }
  } catch {
    rtspStreamReady = false;
    // API stream/info lỗi — giữ RTSP disabled
  }
  // Dashboard chỉ hiển thị camera: RTSP nếu có, không thì webcam máy tính.
  await applyCameraSource("rtsp");
  await syncDashboardCameraPreview();
  await refreshLogs();
  await refreshScheduleStatus();
  if (scheduleAtInput) {
    const minDt = new Date(Date.now() + 60 * 1000);
    const minValue = toLocalDatetimeInputValue(minDt);
    scheduleAtInput.min = minValue;
    scheduleAtInput.value = minValue;
    scheduleAtInput.addEventListener("focus", () => {
      const nextMin = toLocalDatetimeInputValue(new Date(Date.now() + 60 * 1000));
      scheduleAtInput.min = nextMin;
    });
  }
  // Không dò RTSP theo chu kỳ; nếu thiếu RTSP thì giữ webcam chạy liên tục.
  frameTimer = null;
  sensorTimer = setInterval(refreshSensors, 3000);
  scheduleStatusTimer = setInterval(refreshScheduleStatus, 4000);
  setInterval(refreshLogs, 7000);
}

bootstrap();

window.addEventListener("beforeunload", () => {
  stopDashboardWebcam();
});

window.addEventListener("resize", () => {
  trendChart?.resize();
});
