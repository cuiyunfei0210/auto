const headings = {
  job: ["任务", "先选本轮分类，再准备图片，按账号队列模拟网页上传。"],
  folders: ["文件夹", "源图和一个单独的输出目录。"],
  accounts: ["账号", "一个账号传完再换下一个；每个账号尽量使用不同出口。"],
  site: ["网页上传", "上传时用内置浏览器填登录表和上传表，不调用壁纸站后台接口。"],
  api: ["二创 API", "对接中转站。后台测通文生图，不等于二创改图通了。"],
};

const siteFields = [
  "login_url", "upload_url", "open_login_selector", "username_selector", "password_selector",
  "login_button_selector", "login_success_text", "logged_in_selector", "open_upload_selector",
  "file_input_selector", "file_uploaded_text", "title_selector",
  "category_selector", "category_value", "agree_selector", "submit_selector", "success_text",
];

const CATEGORY_OPTIONS = [
  ["1", "动物"], ["2", "军事"], ["3", "汽车"], ["4", "电影"], ["5", "时代"], ["6", "明星"],
  ["7", "宇宙"], ["8", "美女"], ["9", "风景"], ["10", "动漫"], ["17", "游戏"], ["18", "都市"],
];

function canonicalCategory(value) {
  const raw = String(value == null ? "" : value).trim();
  if (!raw) return "";
  for (const [id, name] of CATEGORY_OPTIONS) {
    if (raw === id || raw === name) return name;
  }
  const lowered = raw.toLowerCase();
  const aliases = {
    animals: "动物", military: "军事", cars: "汽车", movie: "电影", era: "时代",
    celebrity: "明星", universe: "宇宙", girl: "美女", scenery: "风景", anime: "动漫",
    games: "游戏", urban: "都市",
  };
  return aliases[lowered] || "";
}

const FIXED_API_BASE = "https://api.newxxt.top";
const apiFields = [
  "api_key", "remix_chat_model", "remix_model", "filename_model",
  "filename_api_key", "remix_prompt", "filename_prompt", "image_size",
];

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
  return String(value == null ? "" : value).split("&").join("&amp;").split('"').join("&quot;").split("<").join("&lt;");
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
  api.base_url = FIXED_API_BASE;
  api.filename_base_url = FIXED_API_BASE;
  api.username = $("api_username") ? $("api_username").value.trim() : "";
  api.password = $("api_password") ? $("api_password").value : "";

  return {
    mode: document.querySelector("input[name=mode]:checked").value,
    upload_category: canonicalCategory($("upload_category") ? $("upload_category").value : ""),
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
  if ($("upload_category")) $("upload_category").value = canonicalCategory(config.upload_category || "");
  $("source_dir").value = config.paths.source_dir || "";
  $("output_dir").value = config.paths.output_dir || "";
  for (const key of siteFields) $(key).value = config.site[key] == null ? "" : config.site[key];
  $("headless").checked = Boolean(config.site.headless);
  if ($("site_preset")) {
    $("site_preset").value = (config.site.login_url || "").includes("cqwall.com") ? "cqwall" : "demo";
  }
  for (const key of apiFields) $(key).value = config.api[key] == null ? "" : config.api[key];
  if ($("api_username")) $("api_username").value = config.api.username || "";
  if ($("api_password")) $("api_password").value = config.api.password || "";
  $("proxy_enabled").checked = Boolean(config.network.proxy_enabled);
  $("unique_ip_per_account").checked = config.network.unique_ip_per_account !== false;
  $("rotate_every_accounts").value = config.network.rotate_every_accounts == null ? 1 : config.network.rotate_every_accounts;
  $("proxies").value = (config.network.proxies || []).join("\n");
  const body = $("account-rows");
  body.innerHTML = "";
  (config.accounts || []).forEach((account) => body.appendChild(accountRow(account)));
  $("account-count").textContent = String((config.accounts || []).length);
}

function setStatus(running, stopping) {
  const pill = $("status-pill");
  const isStopping = Boolean(stopping) || (jobStopping && running);
  if (isStopping && running) {
    pill.textContent = "正在停止";
    pill.classList.add("live");
  } else {
    jobStopping = false;
    pill.textContent = running ? "运行中" : "空闲";
    pill.classList.toggle("live", running);
  }
  if ($("btn-start")) $("btn-start").disabled = Boolean(running);
}

function appendLog(message) {
  const log = $("log");
  if (!log) return;
  const text = String(message || "").trim();
  if (!text) return;
  log.textContent = `${log.textContent}\n${text}`.trim();
  log.scrollTop = log.scrollHeight;
}

function renderLogs(lines) {
  const log = $("log");
  if (!log) return;
  log.textContent = (lines || []).join("\n");
  log.scrollTop = log.scrollHeight;
}

function notify(message) {
  let text = String(message || "").trim() || "发生了未知问题。";
  if (text.length > 180) text = `${text.slice(0, 180)}…`;
  window.alert(text);
}

function localStartProblems(cfg) {
  const problems = [];
  if (!cfg.accounts.length) {
    problems.push("还没有账号。请到「账号」页填写 CQwall 邮箱和密码。");
  }
  if (!canonicalCategory(cfg.upload_category)) {
    problems.push("请先在任务页选择本轮分类。选了什么分类，二创和上传就按什么分类。");
  }
  const sourceCount = Number(lastState.source_count != null ? lastState.source_count : ($("source-count").textContent || 0));
  if (!Number.isFinite(sourceCount) || sourceCount <= 0) {
    problems.push(
      lastState.source_note
      || `源文件夹里没有图片：${lastState.source_dir || $("source_dir").value || "data\\source"}。请把 png/jpg/webp 放进这个目录后再点开始。`
    );
  }
  if (cfg.mode === "remix_then_upload") {
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

async function parseJson(res) {
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch (ignore) {
    const snippet = String(text || "").replace(/\s+/g, " ").slice(0, 160);
    throw new Error(`服务器出错（${res.status}）。${snippet || "请看右侧日志，或 data\\studio.log。"}`);
  }
}

let lastState = {};
let presets = {};
let jobStopping = false;

function applySourceStatus(data) {
  lastState = data || {};
  $("source-count").textContent = data.source_count == null ? 0 : data.source_count;
  if ($("remix-count")) {
    $("remix-count").textContent = data.remix_pending == null ? 0 : data.remix_pending;
  }
  if ($("path-hint") && data.source_dir) {
    $("path-hint").textContent = `源目录 ${data.source_dir} · 输出目录 ${data.output_dir}`;
  }
  const countHint = $("count-hint");
  if (countHint) {
    const pending = Number(data.remix_pending == null ? 0 : data.remix_pending);
    const total = Number(data.remix_total == null ? pending : data.remix_total);
    if (data.running && total > 0) {
      countHint.textContent = `待二创 ${pending}/${total}，每完成一张减 1。`;
    } else {
      countHint.textContent = "";
    }
  }
  const hint = $("source-hint");
  if (hint) {
    hint.textContent = data.source_note || "";
    hint.hidden = !data.source_note;
  }
  const resolved = $("folder-resolved");
  if (resolved && data.source_dir) {
    resolved.textContent = `程序实际读取的源目录：${data.source_dir}`;
  }
}

async function refresh() {
  const res = await fetch("/api/state");
  const data = await parseJson(res);
  if (!res.ok) {
    applySourceStatus({
      source_count: data.source_count || 0,
      remix_pending: data.remix_pending || 0,
      source_dir: data.source_dir || "",
      output_dir: data.output_dir || "",
      source_note: data.error || data.source_note || `服务器出错（${res.status}）`,
    });
    renderLogs(data.logs || [data.error || `服务器出错（${res.status}）`]);
    throw new Error(data.error || `服务器出错（${res.status}）`);
  }
  presets = data.presets || presets;
  if (data.config && data.config.mode) applyConfig(data.config);
  applySourceStatus(data);
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
  if (data.stopping) jobStopping = true;
  setStatus(data.running, data.stopping);
  renderLogs(data.logs);
}

async function saveConfig({ silent = false } = {}) {
  const res = await fetch("/api/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(collectConfig()),
  });
  let data = {};
  try {
    data = await parseJson(res);
  } catch (err) {
    const message = err && err.message ? err.message : "保存失败，请检查账号和数字是否填完整。";
    if (!silent) notify(message);
    return { ok: false, error: message };
  }
  if (!res.ok) {
    const message = "保存失败，请检查账号和数字是否填完整。";
    if (!silent) notify(message);
    return { ok: false, error: message, ...data };
  }
  await refresh();
  return data;
}

function bindClick(id, handler) {
  const el = $(id);
  if (!el) return;
  el.onclick = handler;
}

try {
document.querySelectorAll("aside nav button").forEach((button) => {
  button.onclick = () => {
    document.querySelectorAll("aside nav button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    const pane = button.dataset.pane;
    document.querySelectorAll(".pane").forEach((section) => section.classList.add("hidden"));
    $(`pane-${pane}`).classList.remove("hidden");
    $("heading").textContent = headings[pane][0];
    $("subheading").textContent = headings[pane][1];
    if (pane === "folders" || pane === "job") refreshCounts();
  };
});

bindClick("btn-add-account", () => $("account-rows").appendChild(accountRow()));
bindClick("btn-save", async () => {
  const data = await saveConfig();
  if (data && data.ok === false) return;
  notify("设置已保存。");
});
bindClick("btn-start", async () => {
  const running = $("status-pill").classList.contains("live");
  if (running) {
    notify("任务正在运行。请先点「停止」，或等当前任务结束后再开始。");
    return;
  }
  if ($("btn-start").dataset.busy === "1") {
    notify("正在提交开始请求，请稍等。");
    return;
  }
  $("btn-start").dataset.busy = "1";
  try {
    const saved = await saveConfig({ silent: true });
    if (!saved || saved.ok === false) {
      notify(formatErrorPayload(saved) === "无法开始" ? "保存失败，请检查账号和数字是否填完整。" : formatErrorPayload(saved));
      return;
    }
    const cfg = collectConfig();
    const local = localStartProblems(cfg);
    if (local.length) {
      notify(local.length === 1 ? local[0] : `还不能开始，请先处理：\n${local.map((item, index) => `${index + 1}. ${item}`).join("\n")}`);
      return;
    }
    const res = await fetch("/api/start", { method: "POST" });
    const data = await parseJson(res);
    if (!res.ok) {
      setStatus(res.status === 409);
      notify(formatErrorPayload(data));
      return;
    }
    jobStopping = false;
    setStatus(true);
    renderLogs(data.logs || ["任务已开始"]);
    notify("任务已开始。请看右侧运行日志；二创每张图可能要几十秒。");
  } catch (err) {
    setStatus(false);
    notify(`无法开始：${err && err.message ? err.message : err}`);
  } finally {
    $("btn-start").dataset.busy = "0";
  }
});
bindClick("btn-stop", async () => {
  try {
    appendLog("正在发送停止请求…");
    const res = await fetch("/api/stop", { method: "POST" });
    const data = await parseJson(res);
    const message = (data && data.message) || "已发送停止请求。";
    appendLog(message);
    if (data && data.stopping) {
      jobStopping = true;
      setStatus(true, true);
    } else if (data && data.running) {
      setStatus(true, data.stopping);
    } else {
      jobStopping = false;
      setStatus(false);
    }
  } catch (err) {
    jobStopping = false;
    notify(`停止失败：${err && err.message ? err.message : err}`);
  }
});
bindClick("btn-quit", async () => {
  if (!window.confirm("退出壁纸工坊？未完成的任务会停止。")) return;
  try {
    await fetch("/api/shutdown", { method: "POST" });
  } catch (ignore) {
    /* the process may close the connection */
  }
  notify("程序正在退出。");
});

if ($("site_preset")) {
  $("site_preset").onchange = () => {
    const preset = presets[$("site_preset").value];
    if (!preset) return;
    for (const key of siteFields) $(key).value = preset[key] == null ? "" : preset[key];
    $("headless").checked = Boolean(preset.headless);
  };
}
} catch (err) {
  const log = $("log");
  if (log) log.textContent = "界面脚本加载失败，请重新打开程序。";
  window.alert("界面脚本加载失败，请重新打开程序。\n" + (err && err.message ? err.message : err));
}

function connectWs() {
  const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
  ws.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "remix_progress") {
      if ($("remix-count") && payload.remaining != null) {
        $("remix-count").textContent = payload.remaining;
      }
      const countHint = $("count-hint");
      if (countHint && payload.total) {
        countHint.textContent = `待二创 ${payload.remaining}/${payload.total}，每完成一张减 1。`;
      }
      return;
    }
    if (payload.type === "hello" || payload.type === "reset" || payload.type === "done") {
      renderLogs(payload.logs || []);
      if (payload.remix_pending != null && $("remix-count")) {
        $("remix-count").textContent = payload.remix_pending;
      }
      if (payload.type === "done") {
        jobStopping = false;
        setStatus(false);
        refreshCounts();
        if (payload.stopped) notify("任务已停止。");
        else if (payload.last_error) notify(`任务失败：\n${payload.last_error}`);
        else if (payload.last_result) {
          const uploaded = payload.last_result.uploaded;
          const skipped = payload.last_result.skipped || 0;
          if (skipped) {
            notify(`任务结束：成功上传 ${uploaded} 张，跳过 ${skipped} 张。失败原因在右侧日志，已自动继续下一张。`);
          } else {
            notify(`任务完成：成功上传 ${uploaded} 张。`);
          }
        } else {
          notify("任务已结束。请看右侧运行日志。");
        }
      } else if ("running" in payload) {
        if (payload.stopping) jobStopping = true;
        setStatus(Boolean(payload.running), payload.stopping);
      }
      return;
    }
    if (payload.message) {
      appendLog(payload.message);
    }
  };
  ws.onclose = () => setTimeout(connectWs, 1500);
}

async function refreshCounts() {
  try {
    const res = await fetch("/api/state");
    const data = await parseJson(res);
    if (!res.ok) {
      applySourceStatus({
        source_count: 0,
        remix_pending: 0,
        source_dir: data.source_dir || "",
        output_dir: data.output_dir || "",
        source_note: data.error || data.source_note || `服务器出错（${res.status}）`,
      });
      return;
    }
    applySourceStatus(data);
    if (data.stopping) jobStopping = true;
    if ("running" in data) setStatus(Boolean(data.running), data.stopping);
  } catch (ignore) {
    /* keep the last known counts */
  }
}

refresh()
  .catch((err) => {
    const message = err && err.message ? err.message : String(err);
    renderLogs([`界面加载失败：${message}`, "请重新打开壁纸工坊。"]);
  })
  .finally(connectWs);

setInterval(() => {
  if ($("btn-start").dataset.busy === "1") return;
  refreshCounts();
}, 2500);
