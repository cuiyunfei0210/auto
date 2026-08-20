const headings = {
  job: ["任务", "先准备图片，再按账号队列模拟网页上传。"],
  folders: ["文件夹", "源图和一个单独的输出目录。"],
  accounts: ["账号", "一个账号传完再换下一个；每个账号尽量使用不同出口。"],
  site: ["网页上传", "用浏览器填登录表和上传表，不调用壁纸站后台接口。"],
  api: ["二创 API", "对接中转站。可随时跳过这一步。"],
};

const siteFields = [
  "login_url", "upload_url", "open_login_selector", "username_selector", "password_selector",
  "login_button_selector", "login_success_text", "logged_in_selector", "open_upload_selector",
  "file_input_selector", "file_uploaded_text", "title_selector",
  "category_selector", "category_value", "agree_selector", "submit_selector", "success_text",
];
const siteNumbers = ["min_width", "min_height"];

const apiFields = ["base_url", "api_key", "remix_model", "filename_model", "remix_prompt", "filename_prompt", "image_size"];

function $(id) { return document.getElementById(id); }

function accountRow(account = { username: "", password: "", upload_count: 3, interval_seconds: 8, proxy: "" }) {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td><input class="acc-user" value="${escapeAttr(account.username)}"></td>
    <td><input class="acc-pass" type="password" value="${escapeAttr(account.password)}"></td>
    <td><input class="acc-count" type="number" min="1" value="${account.upload_count}"></td>
    <td><input class="acc-interval" type="number" min="0" step="0.5" value="${account.interval_seconds}"></td>
    <td><input class="acc-proxy" placeholder="空则用代理池" value="${escapeAttr(account.proxy || "")}"></td>
    <td><button type="button" class="linkish acc-del">删除</button></td>
  `;
  tr.querySelector(".acc-del").onclick = () => tr.remove();
  return tr;
}

function escapeAttr(value) {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll('"', "&quot;").replaceAll("<", "&lt;");
}

function collectConfig() {
  const accounts = [...document.querySelectorAll("#account-rows tr")].map((row) => ({
    username: row.querySelector(".acc-user").value.trim(),
    password: row.querySelector(".acc-pass").value,
    upload_count: Number(row.querySelector(".acc-count").value || 1),
    interval_seconds: Number(row.querySelector(".acc-interval").value || 0),
    proxy: row.querySelector(".acc-proxy").value.trim(),
  })).filter((item) => item.username && item.password);

  const site = {};
  for (const key of siteFields) site[key] = $(key).value;
  for (const key of siteNumbers) site[key] = Number($(key).value || 0);
  site.headless = $("headless").checked;

  const api = {};
  for (const key of apiFields) api[key] = $(key).value;

  return {
    mode: document.querySelector("input[name=mode]:checked").value,
    api,
    paths: {
      source_dir: $("source_dir").value.trim(),
      output_dir: $("output_dir").value.trim(),
    },
    site,
    accounts,
    network: {
      proxy_enabled: $("proxy_enabled").checked,
      unique_ip_per_account: $("unique_ip_per_account").checked,
      rotate_every_accounts: Number($("rotate_every_accounts").value || 1),
      proxies: $("proxies").value.split("\n").map((line) => line.trim()).filter(Boolean),
    },
  };
}

function applyConfig(config) {
  document.querySelector(`input[name=mode][value="${config.mode}"]`).checked = true;
  $("source_dir").value = config.paths.source_dir || "";
  $("output_dir").value = config.paths.output_dir || "";
  for (const key of siteFields) $(key).value = config.site[key] ?? "";
  for (const key of siteNumbers) $(key).value = config.site[key] ?? 0;
  $("headless").checked = Boolean(config.site.headless);
  if ($("site_preset")) {
    $("site_preset").value = (config.site.login_url || "").includes("cqwall.com") ? "cqwall" : "demo";
  }
  for (const key of apiFields) $(key).value = config.api[key] ?? "";
  $("proxy_enabled").checked = Boolean(config.network.proxy_enabled);
  $("unique_ip_per_account").checked = config.network.unique_ip_per_account !== false;
  $("rotate_every_accounts").value = config.network.rotate_every_accounts ?? 1;
  $("proxies").value = (config.network.proxies || []).join("\n");
  const body = $("account-rows");
  body.innerHTML = "";
  (config.accounts || []).forEach((account) => body.appendChild(accountRow(account)));
  $("account-count").textContent = String((config.accounts || []).length);
}

function setStatus(running) {
  const pill = $("status-pill");
  pill.textContent = running ? "运行中" : "空闲";
  pill.classList.toggle("live", running);
}

function renderLogs(lines) {
  $("log").textContent = (lines || []).join("\n");
  $("log").scrollTop = $("log").scrollHeight;
}

let presets = {};

async function refresh() {
  const res = await fetch("/api/state");
  const data = await res.json();
  presets = data.presets || presets;
  applyConfig(data.config);
  $("source-count").textContent = data.source_count;
  $("output-count").textContent = data.output_count;
  $("path-hint").textContent = `源目录 ${data.source_dir} · 输出目录 ${data.output_dir}`;
  const hint = $("proxy-hint");
  if (hint) {
    if (data.proxy_error) {
      hint.textContent = data.proxy_error;
      hint.classList.add("error");
    } else if ((data.proxy_assignments || []).length) {
      const lines = data.proxy_assignments.map((row) => `${row.username} → ${row.proxy || "直连"}`);
      hint.textContent = lines.join("；");
      hint.classList.remove("error");
    } else {
      hint.textContent = "";
      hint.classList.remove("error");
    }
  }
  setStatus(data.running);
  renderLogs(data.logs);
}

async function saveConfig() {
  const res = await fetch("/api/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(collectConfig()),
  });
  const data = await res.json();
  if (!res.ok) {
    alert("保存失败，请检查账号和数字是否填完整");
    return data;
  }
  await refresh();
  return data;
}

document.querySelectorAll("aside nav button").forEach((button) => {
  button.onclick = () => {
    document.querySelectorAll("aside nav button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    const pane = button.dataset.pane;
    document.querySelectorAll(".pane").forEach((section) => section.classList.add("hidden"));
    $(`pane-${pane}`).classList.remove("hidden");
    $("heading").textContent = headings[pane][0];
    $("subheading").textContent = headings[pane][1];
  };
});

$("btn-add-account").onclick = () => $("account-rows").appendChild(accountRow());
$("btn-save").onclick = saveConfig;
$("btn-start").onclick = async () => {
  await saveConfig();
  const res = await fetch("/api/start", { method: "POST" });
  const data = await res.json();
  if (!res.ok) alert(data.error || "无法开始");
  setStatus(true);
};
$("btn-stop").onclick = async () => {
  await fetch("/api/stop", { method: "POST" });
};

if ($("site_preset")) {
  $("site_preset").onchange = () => {
    const preset = presets[$("site_preset").value];
    if (!preset) return;
    for (const key of siteFields) $(key).value = preset[key] ?? "";
    for (const key of siteNumbers) $(key).value = preset[key] ?? 0;
    $("headless").checked = Boolean(preset.headless);
  };
}

function connectWs() {
  const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
  ws.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    if (payload.message) {
      const log = $("log");
      log.textContent = `${log.textContent}\n${payload.message}`.trim();
      log.scrollTop = log.scrollHeight;
    }
    if (payload.type === "done" || payload.running === false) setStatus(Boolean(payload.running));
    if (payload.type === "hello") {
      renderLogs(payload.logs);
      setStatus(payload.running);
    }
  };
  ws.onclose = () => setTimeout(connectWs, 1500);
}

refresh().then(connectWs);
