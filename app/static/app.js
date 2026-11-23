const $ = (id) => document.getElementById(id);
const STATE_LABELS = {
  IDLE: "Idle", PREPARE: "Preparing", RUNNING: "Printing", PAUSE: "Paused",
  FINISH: "Finished", FAILED: "Failed", SLICING: "Slicing", UNKNOWN: "Unknown",
};
const SPEEDS = { 1: "Silent", 2: "Standard", 3: "Sport", 4: "Ludicrous" };

function fmtTemp(cur, target) {
  if (cur == null) return "—";
  return target ? `${Math.round(cur)}° / ${Math.round(target)}°` : `${Math.round(cur)}°`;
}
function fmtMinutes(min) {
  if (min == null) return "—";
  const h = Math.floor(min / 60), m = min % 60;
  return h ? `${h}h ${m}m` : `${m}m`;
}

async function refreshStatus() {
  try {
    const res = await fetch("/api/status");
    const s = await res.json();
    render(s);
  } catch {
    setConn("Server unreachable", "bad");
  }
}

function setConn(text, cls) {
  const el = $("conn");
  el.textContent = text;
  el.className = `pill ${cls}`;
}

function render(s) {
  $("mock").hidden = !s.mock;
  const stale = s.last_update && Date.now() / 1000 - s.last_update > 120;
  if (!s.connected) setConn(s.error || "Not connected", "bad");
  else if (stale) setConn("No recent data", "warn");
  else setConn("Connected", "ok");

  const active = ["RUNNING", "PAUSE", "PREPARE"].includes(s.state);
  const badge = $("state");
  badge.textContent = STATE_LABELS[s.state] || s.state;
  badge.className = `badge ${s.state}`;
  $("job-name").textContent = s.job_name || "No job";
  $("bar-fill").style.width = `${s.progress ?? 0}%`;
  $("progress").textContent = s.progress != null ? `${s.progress}%` : "—";
  $("layer").textContent = s.total_layers ? `${s.layer ?? 0} / ${s.total_layers}` : "—";
  $("remaining").textContent = active ? fmtMinutes(s.remaining_minutes) : "—";
  $("eta").textContent = active && s.remaining_minutes != null
    ? new Date(Date.now() + s.remaining_minutes * 60000).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
    : "—";
  $("nozzle").textContent = fmtTemp(s.nozzle_temp, s.nozzle_target);
  $("bed").textContent = fmtTemp(s.bed_temp, s.bed_target);
  $("speed").textContent = SPEEDS[s.speed_level] || "—";
  $("wifi").textContent = s.wifi_signal || "—";

  const ams = $("ams");
  if (s.ams && s.ams.length) {
    ams.innerHTML = "";
    for (const t of s.ams) {
      const div = document.createElement("div");
      div.className = "tray";
      const sw = document.createElement("span");
      sw.className = "swatch";
      sw.style.background = t.color;
      const txt = document.createElement("span");
      const left = t.remaining >= 0 ? ` · ${t.remaining}%` : "";
      txt.textContent = `${t.slot} ${t.type}${left}`;
      div.append(sw, txt);
      ams.append(div);
    }
  }
}

let snapBusy = false;
async function refreshSnapshot() {
  if (snapBusy) return;
  snapBusy = true;
  $("snap").disabled = true;
  try {
    const res = await fetch("/api/snapshot", { cache: "no-store" });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `HTTP ${res.status}`);
    }
    const blob = await res.blob();
    const img = $("cam");
    if (img.src) URL.revokeObjectURL(img.src);
    img.src = URL.createObjectURL(blob);
    img.classList.add("loaded");
    $("cam-msg").textContent = "";
    $("cam-time").textContent = `Taken ${new Date().toLocaleTimeString()}`;
  } catch (err) {
    $("cam-msg").textContent = `Snapshot failed: ${err.message}`;
  } finally {
    snapBusy = false;
    $("snap").disabled = false;
  }
}

let autoTimer = null;
$("auto").addEventListener("change", (e) => {
  clearInterval(autoTimer);
  if (e.target.checked) autoTimer = setInterval(refreshSnapshot, 10000);
});
$("snap").addEventListener("click", refreshSnapshot);

refreshStatus();
refreshSnapshot();
setInterval(refreshStatus, 3000);
