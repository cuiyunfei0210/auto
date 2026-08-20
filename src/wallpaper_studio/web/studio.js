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

const apiFields = ["base_url", "api_key", "remix_chat_model", "remix_model", "filename_model", "remix_prompt", "filename_prompt", "image_size"];

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
  site.min_width = 0;
  site.min_height = 0;
  site.headless = $("headless").checked;

  const api = {};
  for (const key of apiFields) api[key] = $(key).value;
  api.username = $("api_username") ? $("api_username").value.trim() : "";
  api.password = $("api_password") ? $("api_password").value : "";

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
  $("headless").checked = Boolean(config.site.headless);
  if ($("site_preset")) {
    $("site_preset").value = (config.site.login_url || "").includes("cqwall.com") ? "cqwall" : "demo";
  }
  for (const key of apiFields) $(key).value = config.api[key] ?? "";
  if ($("api_username")) $("api_username").value = config.api.username || "";
  if ($("api_password")) $("api_password").value = config.api.password || "";
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
  $("btn-stop").disabled = !running;
}

function notify(message) {
  const text = String(message || "").trim() || "发生了未知问题。";
  window.alert(text);
}

function localStartProblems(cfg) {
  const problems = [];
  if (!cfg.accounts.length) {
    problems.push("还没有账号。请到「账号」页填写 CQwall 邮箱和密码。");
  }
  const sourceCount = Number($("source-count").textContent || 0);
  if (!Number.isFinite(sourceCount) || sourceCount <= 0) {
    problems.push("源文件夹里没有图片。请到「文件夹」确认源目录，并放入 png/jpg 图片。");
  }
  if (cfg.mode === "remix_then_upload") {
    if (!(cfg.api.base_url || "").trim()) {
      problems.push("二创模式需要填写中转站接口地址，例如 https://xmapi.site。");
    }
    if (!(cfg.api.api_key || "").trim() && !((cfg.api.username || "").trim() && cfg.api.password)) {
      problems.push("二创模式需要 API Key，或中转站邮箱和密码。请到「二创 API」填写。");
    }
    if (!(cfg.api.remix_model || "").trim()) {
      problems.push("二创模式需要填写生图模型，当前这组 Key 一般用 gpt-image-2。");
    }
  }
  if (cfg.network.proxy_enabled && cfg.network.unique_ip_per_account && cfg.accounts.length > (cfg.network.proxies || []).length) {
    const missing = cfg.accounts.filter((item) => !(item.proxy || "").trim()).length;
    if (missing && cfg.network.proxies.length < missing) {
      problems.push("已开启一人一代理，但代理不够。请到「账号」页补代理。");
    }
  }
  return problems;
}

function formatErrorPayload(data) {
  if (!data) return "无法开始";
  if (typeof data.error === "string" && data.error.trim()) return data.error;
  if (Array.isArray(data.problems) && data.problems.length) return data.problems.join("\n");
  if (Array.isArray(data.error)) return "保存失败，请检查账号和数字是否填完整";
  return "无法开始";
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
  const banner = $("env-banner");
  if (banner) {
    if (data.archive_warning) {
      banner.textContent = data.archive_warning;
      banner.hidden = false;
    } else {
      banner.textContent = "";
      banner.hidden = true;
    }
  }
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

async function saveConfig({ silent = false } = {}) {
  const res = await fetch("/api/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(collectConfig()),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message = "保存失败，请检查账号和数字是否填完整。";
    if (!silent) notify(message);
    return { ok: false, error: message, ...data };
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
$("btn-save").onclick = async () => {
  const data = await saveConfig();
  if (data && data.ok === false) return;
  notify("设置已保存。");
};
$("btn-start").onclick = async () => {
  const running = $("status-pill").classList.contains("live");
  if (running) {
    notify("任务正在运行。请先点「停止」，或等当前任务结束后再开始。");
    return;
  }
  if ($("btn-start").dataset.busy === "1") {
    notify("正在提交开始请求，请稍等。");
    return;
  }
  const cfg = collectConfig();
  const local = localStartProblems(cfg);
  if (local.length) {
    notify(local.length === 1 ? local[0] : `还不能开始，请先处理：\n${local.map((item, index) => `${index + 1}. ${item}`).join("\n")}`);
    return;
  }
  $("btn-start").dataset.busy = "1";
  try {
    const saved = await saveConfig({ silent: true });
    if (!saved || saved.ok === false) {
      notify(formatErrorPayload(saved) === "无法开始" ? "保存失败，请检查账号和数字是否填完整。" : formatErrorPayload(saved));
      return;
    }
    const res = await fetch("/api/start", { method: "POST" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setStatus(res.status === 409);
      notify(formatErrorPayload(data));
      return;
    }
    setStatus(true);
    renderLogs(data.logs || ["任务已开始"]);
    notify("任务已开始。请看右侧运行日志；二创每张图可能要几十秒。");
  } catch (err) {
    setStatus(false);
    notify(`无法开始：${err && err.message ? err.message : err}`);
  } finally {
    $("btn-start").dataset.busy = "0";
  }
};
$("btn-stop").onclick = async () => {
  try {
    await fetch("/api/stop", { method: "POST" });
    notify("已发送停止请求。请看右侧运行日志。");
  } catch (err) {
    notify(`停止失败：${err && err.message ? err.message : err}`);
  }
};

if ($("site_preset")) {
  $("site_preset").onchange = () => {
    const preset = presets[$("site_preset").value];
    if (!preset) return;
    for (const key of siteFields) $(key).value = preset[key] ?? "";
    $("headless").checked = Boolean(preset.headless);
  };
}

function connectWs() {
  const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
  ws.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "hello" || payload.type === "reset" || payload.type === "done") {
      renderLogs(payload.logs || []);
      if (payload.type === "done") {
        setStatus(false);
        if (payload.last_error) notify(`任务失败：\n${payload.last_error}`);
        else if (payload.last_result) {
          const uploaded = payload.last_result.uploaded;
          notify(`任务完成：成功上传 ${uploaded} 张。`);
        } else {
          notify("任务已结束。请看右侧运行日志。");
        }
      } else if ("running" in payload) setStatus(Boolean(payload.running));
      return;
    }
    if (payload.message) {
      const log = $("log");
      log.textContent = `${log.textContent}\n${payload.message}`.trim();
      log.scrollTop = $("log").scrollHeight;
    }
  };
  ws.onclose = () => setTimeout(connectWs, 1500);
}

refresh().then(connectWs);
