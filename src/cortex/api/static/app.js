/* Cortex dashboard — a view over state that already exists. */

const $ = (sel) => document.querySelector(sel);
let view = "overview";
let lastRoute = null;

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

async function api(path, opts = {}) {
  if (opts.body) {
    opts.headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
    opts.body = JSON.stringify(opts.body);
  }
  const resp = await fetch(path, opts);
  if (!resp.ok) {
    let detail = resp.statusText;
    try { detail = (await resp.json()).detail || detail; } catch {}
    throw new Error(detail);
  }
  return resp.json();
}

function toast(msg, ok = true) {
  const el = $("#toast");
  el.textContent = msg;
  el.className = ok ? "show" : "show err";
  setTimeout(() => (el.className = ""), 3200);
}

function chip(state) { return `<span class="chip ${esc(state)}">${esc(state)}</span>`; }
function fmtTs(ts) { return (ts || "").replace("T", " ").slice(0, 19); }
function usd(n) { return `$${Number(n || 0).toFixed(4)}`; }

/* ---------- navigation ---------- */
$("#nav").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-view]");
  if (!btn) return;
  view = btn.dataset.view;
  document.querySelectorAll("#nav button").forEach((b) => b.classList.toggle("active", b === btn));
  render();
});

setInterval(() => {
  if (["overview", "runs", "events", "costs"].includes(view)) render();
  refreshSidebar();
}, 5000);

async function refreshSidebar() {
  try {
    const [gw, costs] = await Promise.all([api("/settings/gateway"), api("/costs")]);
    $("#gw-pill").textContent = gw.up ? "gateway: up" : "gateway: down";
    $("#gw-pill").className = "pill " + (gw.up ? "up" : "down");
    $("#spend-mini").textContent = `${usd(costs.today_usd)} today / $${costs.caps.global_daily_usd.toFixed(2)} cap`;
  } catch {}
}

/* ---------- views ---------- */
async function render() {
  const renderers = { overview, ideas, projects, runs, events, costs, settings };
  try { await renderers[view](); } catch (err) { $("#main").innerHTML = `<div class="empty">error: ${esc(err.message)}</div>`; }
}

async function overview() {
  const [meta, ideasList, runsList, costsData, eventsList, cfg, gw] = await Promise.all([
    api("/meta"), api("/ideas"), api("/runs"), api("/costs"), api("/events?limit=6"),
    api("/settings"), api("/settings/gateway"),
  ]);
  const newIdeas = ideasList.filter((i) => i.status === "new").length;
  const doneRuns = runsList.filter((r) => r.state === "done").length;
  const anyKey = Object.values(cfg.keys).some((k) => k.set);
  const pct = Math.min(100, (costsData.today_usd / costsData.caps.global_daily_usd) * 100);

  const checklist = [
    [anyKey, "Add a model API key in Settings (OpenRouter free tier is enough)"],
    [gw.up, "Start the LiteLLM gateway (Settings → Restart gateway, or `make gateway`)"],
    [ideasList.length > 0, "Capture your first idea"],
    [runsList.length > 0, "Dispatch a dry-run to the Claude Code harness"],
  ];

  $("#main").innerHTML = `
    <h1>Overview</h1>
    <div class="sub">ideas enter · agents work · memory compounds · costs stay governed</div>
    <div class="grid cols-4">
      <div class="card"><h3>Ideas</h3><div class="stat">${newIdeas}<small>new · ${ideasList.length} total</small></div></div>
      <div class="card"><h3>Runs</h3><div class="stat">${runsList.length}<small>${doneRuns} done</small></div></div>
      <div class="card"><h3>Spend today</h3><div class="stat">${usd(costsData.today_usd)}</div>
        <div class="meter ${pct > 70 ? "hot" : ""}"><div style="width:${pct}%"></div></div>
        <span class="muted mono">${usd(costsData.daily_remaining_usd)} remaining</span></div>
      <div class="card"><h3>Plugs</h3>
        <div style="margin-top:4px">${meta.agents.map((a) => `<span class="chip routed">${esc(a)}</span>`).join(" ")}
        ${meta.harnesses.map((h) => `<span class="chip queued">${esc(h)}</span>`).join(" ")}</div>
        <div class="muted" style="margin-top:8px;font-size:12px">${meta.models.length} models registered</div></div>
    </div>
    <div class="grid cols-2">
      <div class="card"><h3>Getting started</h3>
        ${checklist.map(([done, label]) => `<div class="check-item"><span class="dot ${done ? "on" : "off"}"></span><span class="${done ? "muted" : ""}">${esc(label)}</span></div>`).join("")}
      </div>
      <div class="card"><h3>Recent events</h3>
        ${eventsList.length ? eventsList.map((e) => `<div class="check-item mono" style="font-size:12px"><span class="muted">${fmtTs(e.ts).slice(11)}</span><span>${esc(e.type)}</span></div>`).join("") : `<div class="empty">events will stream here — e.g. <b>idea.captured</b>, <b>run.finished</b></div>`}
      </div>
    </div>`;
}

async function ideas() {
  const list = await api("/ideas");
  const ghost = list.length ? "" : `
    <tr class="ghost"><td>—</td><td>e.g. “cache the vault retrieval index”</td><td>cortex</td><td><span class="chip new">new</span></td></tr>
    <tr class="ghost"><td>—</td><td>e.g. “add a Telegram channel adapter”</td><td>cortex</td><td><span class="chip routed">routed</span></td></tr>`;
  $("#main").innerHTML = `
    <h1>Ideas</h1>
    <div class="sub">capture the moment it occurs — the router turns them into GitHub issues</div>
    <div class="card" style="margin-bottom:16px">
      <div class="row">
        <div style="flex:3"><label>Idea</label><input id="idea-text" placeholder="e.g. Add dark mode toggle to the settings page"></div>
        <div><label>Project (optional)</label><input id="idea-project" placeholder="e.g. cortex"></div>
        <div class="shrink"><button class="btn" id="idea-add">Capture</button></div>
      </div>
    </div>
    <div class="row" style="margin-bottom:14px; justify-content:flex-start">
      <div class="shrink"><button class="btn ghostbtn" id="route-dry">Dry-run route</button></div>
      <div class="shrink"><button class="btn" id="route-real">Route now → GitHub issues</button></div>
    </div>
    ${lastRoute ? `<div class="card" style="margin-bottom:16px"><h3>Last route ${lastRoute.dry_run ? "(dry-run)" : ""}</h3>
      ${lastRoute.tasks.length ? lastRoute.tasks.map((t) => `<div class="check-item"><span class="chip ${t.filed ? "routed" : "queued"}">${t.filed ? "filed" : "not filed"}</span><b>[${esc(t.project)}]</b> ${esc(t.title)} ${t.issue_url ? `<a href="${esc(t.issue_url)}" target="_blank">${esc(t.issue_url)}</a>` : ""}</div>`).join("") : '<div class="empty">no new ideas to route</div>'}</div>` : ""}
    <div class="card"><table>
      <tr><th>#</th><th>idea</th><th>project</th><th>status</th></tr>
      ${list.map((i) => `<tr><td class="mono muted">${i.id}</td><td>${esc(i.text)}</td><td>${esc(i.project || "—")}</td><td>${chip(i.status)}</td></tr>`).join("")}
      ${ghost}
    </table></div>`;

  $("#idea-add").onclick = async () => {
    const text = $("#idea-text").value.trim();
    if (!text) return toast("type an idea first", false);
    await api("/ideas", { method: "POST", body: { text, project: $("#idea-project").value.trim() || null, source: "dashboard" } });
    toast("idea captured");
    render();
  };
  $("#route-dry").onclick = () => routeNow(true);
  $("#route-real").onclick = () => routeNow(false);
}

async function routeNow(dry) {
  try {
    lastRoute = await api("/actions/route", { method: "POST", body: { dry_run: dry } });
    toast(lastRoute.tasks.length ? `${lastRoute.tasks.length} task(s) ${dry ? "planned" : "routed"}` : "no new ideas");
    render();
  } catch (err) { toast(err.message, false); }
}

async function projects() {
  const list = await api("/projects");
  const ghost = list.length ? "" : `<tr class="ghost"><td>e.g. cortex</td><td>you/cortex</td><td>~/Documents/cortex</td></tr>`;
  $("#main").innerHTML = `
    <h1>Projects</h1>
    <div class="sub">repo = where the router files issues · workspace = where the harness runs</div>
    <div class="card" style="margin-bottom:16px">
      <div class="row">
        <div><label>Name</label><input id="p-name" placeholder="e.g. cortex"></div>
        <div><label>GitHub repo</label><input id="p-repo" placeholder="e.g. owner/repo"></div>
        <div><label>Workspace path</label><input id="p-ws" placeholder="e.g. /Users/you/code/project"></div>
        <div class="shrink"><button class="btn" id="p-add">Register</button></div>
      </div>
    </div>
    <div class="card"><table>
      <tr><th>name</th><th>repo</th><th>workspace</th></tr>
      ${list.map((p) => `<tr><td><b>${esc(p.name)}</b></td><td class="mono">${esc(p.repo || "—")}</td><td class="mono muted">${esc(p.workspace_path || "—")}</td></tr>`).join("")}
      ${ghost}
    </table></div>`;
  $("#p-add").onclick = async () => {
    const name = $("#p-name").value.trim();
    if (!name) return toast("project needs a name", false);
    await api("/projects", { method: "PUT", body: { name, repo: $("#p-repo").value.trim() || null, workspace_path: $("#p-ws").value.trim() || null } });
    toast(`project ${name} registered`);
    render();
  };
}

async function runs() {
  const [list, projectList] = await Promise.all([api("/runs"), api("/projects")]);
  const ghost = list.length ? "" : `
    <tr class="ghost"><td>—</td><td colspan="2">e.g. “issue #12: cache the retrieval index”</td><td>claude-code</td><td><span class="chip done">done</span></td><td>$0.31</td></tr>`;
  $("#main").innerHTML = `
    <h1>Runs</h1>
    <div class="sub">dispatch approved tasks to a harness — it branches, works, opens a PR. never main.</div>
    <div class="card" style="margin-bottom:16px">
      <div class="row">
        <div style="flex:3"><label>Task</label><input id="r-task" placeholder="e.g. issue #12: add a status badge to the README"></div>
        <div><label>Project</label><select id="r-project"><option value="">— pick —</option>${projectList.map((p) => `<option>${esc(p.name)}</option>`).join("")}</select></div>
        <div class="shrink" style="padding-bottom:6px"><span class="checkline"><input type="checkbox" id="r-dry" checked> dry-run</span></div>
        <div class="shrink"><button class="btn" id="r-go">Dispatch</button></div>
      </div>
      <div class="muted" style="font-size:12px;margin-top:8px">dry-run shows the exact harness command without spending anything; budget gate runs either way</div>
    </div>
    <div class="card"><table>
      <tr><th>#</th><th>when</th><th>task</th><th>harness</th><th>state</th><th>cost</th></tr>
      ${list.map((r) => `<tr><td class="mono muted">${r.id}</td><td class="mono muted">${fmtTs(r.ts)}</td>
        <td>${esc(r.task.slice(0, 90))}<details><summary>details</summary><pre class="json">${esc(r.result_json)}</pre></details></td>
        <td>${esc(r.harness || "—")}</td><td>${chip(r.state)}</td><td class="mono">${usd(r.cost_usd)}</td></tr>`).join("")}
      ${ghost}
    </table></div>`;
  $("#r-go").onclick = async () => {
    const task = $("#r-task").value.trim();
    if (!task) return toast("describe the task", false);
    if (!$("#r-project").value) return toast("pick a project (register one first)", false);
    try {
      const res = await api("/actions/dispatch", { method: "POST", body: { task, project: $("#r-project").value, dry_run: $("#r-dry").checked } });
      toast(res.queued ? "harness running in background" : `run #${res.run_id} → ${res.state}`);
      render();
    } catch (err) { toast(err.message, false); }
  };
}

async function events() {
  const list = await api("/events?limit=100");
  $("#main").innerHTML = `
    <h1>Events</h1>
    <div class="sub">the append-only bus — everything that happens, happens here first</div>
    <div class="card"><table>
      <tr><th>#</th><th>when</th><th>type</th><th>payload</th></tr>
      ${list.length ? list.map((e) => `<tr><td class="mono muted">${e.id}</td><td class="mono muted">${fmtTs(e.ts)}</td><td><b>${esc(e.type)}</b></td><td class="mono muted" style="font-size:12px">${esc(JSON.stringify(e.payload))}</td></tr>`).join("") : `<tr class="ghost"><td>—</td><td>—</td><td>idea.captured</td><td>{"idea_id": 1, "project": "cortex"}</td></tr>`}
    </table></div>`;
}

async function costs() {
  const data = await api("/costs");
  const pct = Math.min(100, (data.today_usd / data.caps.global_daily_usd) * 100);
  $("#main").innerHTML = `
    <h1>Costs</h1>
    <div class="sub">two rails: LiteLLM per-key budgets at the gateway + this ledger gate before every dispatch</div>
    <div class="grid cols-3">
      <div class="card"><h3>Today</h3><div class="stat">${usd(data.today_usd)}</div>
        <div class="meter ${pct > 70 ? "hot" : ""}"><div style="width:${pct}%"></div></div>
        <span class="muted mono">${usd(data.daily_remaining_usd)} of $${data.caps.global_daily_usd.toFixed(2)} left</span></div>
      <div class="card"><h3>All time</h3><div class="stat">${usd(data.total_usd)}</div></div>
      <div class="card"><h3>Budget caps</h3>
        <label>Daily cap (USD)</label><input id="b-daily" type="number" step="0.5" value="${data.caps.global_daily_usd}">
        <label>Per-run cap (USD)</label><input id="b-run" type="number" step="0.1" value="${data.caps.per_run_usd}">
        <div style="margin-top:12px"><button class="btn ghostbtn" id="b-save">Save caps</button></div></div>
    </div>
    <div class="card"><h3>By model / harness</h3><table>
      <tr><th>model</th><th>calls</th><th>tokens in/out</th><th>cost</th></tr>
      ${data.by_model.length ? data.by_model.map((m) => `<tr><td class="mono">${esc(m.model)}</td><td>${m.calls}</td><td class="mono muted">${m.tokens_in}/${m.tokens_out}</td><td class="mono">${usd(m.cost_usd)}</td></tr>`).join("") : `<tr class="ghost"><td>free/llama-70b</td><td>12</td><td>18k/2k</td><td>$0.0000</td></tr><tr class="ghost"><td>claude-code</td><td>1</td><td>—</td><td>$0.3100</td></tr>`}
    </table></div>`;
  $("#b-save").onclick = async () => {
    try {
      await api("/settings/budgets", { method: "PUT", body: { global_daily_usd: +$("#b-daily").value, per_run_usd: +$("#b-run").value } });
      toast("budget caps saved");
      render();
    } catch (err) { toast(err.message, false); }
  };
}

const KEY_META = {
  LITELLM_MASTER_KEY: ["Gateway master key", "any string — clients auth to your local proxy with it"],
  OPENROUTER_API_KEY: ["OpenRouter", "free-tier models · openrouter.ai/keys"],
  GROQ_API_KEY: ["Groq", "free fast inference · console.groq.com/keys"],
  ANTHROPIC_API_KEY: ["Anthropic", "paid, premium tier · console.anthropic.com"],
};

async function settings() {
  const [cfg, gw] = await Promise.all([api("/settings"), api("/settings/gateway")]);
  $("#main").innerHTML = `
    <h1>Settings</h1>
    <div class="sub">keys are written to the local <span class="mono">.env</span> only — they never leave this machine and are shown masked</div>
    <div class="card" style="margin-bottom:16px"><h3>API keys</h3>
      ${Object.entries(KEY_META).map(([key, [label, hint]]) => `
        <div class="keyrow">
          <div><div class="name">${label}</div><div class="muted" style="font-size:11.5px">${hint}</div></div>
          <div class="hint">${cfg.keys[key].set ? `<span class="chip routed">set ${esc(cfg.keys[key].hint)}</span>` : '<span class="chip queued">not set</span>'}</div>
          <input type="password" id="k-${key}" placeholder="${key === "LITELLM_MASTER_KEY" ? "sk-cortex-local" : "paste to set / overwrite"}" autocomplete="off">
        </div>`).join("")}
      <div style="margin-top:14px"><button class="btn" id="k-save">Save keys</button></div>
    </div>
    <div class="grid cols-2">
      <div class="card"><h3>Gateway (LiteLLM)</h3>
        <div class="check-item"><span class="dot ${gw.up ? "on" : "off"}"></span>${gw.up ? "up" : "down"} at <span class="mono" style="margin-left:6px">${esc(gw.url)}</span></div>
        <label>Gateway URL</label><input id="c-gwurl" value="${esc(cfg.config.CORTEX_GATEWAY_URL || "http://localhost:4000")}">
        <div style="margin-top:12px" class="row">
          <div class="shrink"><button class="btn ghostbtn" id="gw-restart">Restart gateway</button></div>
        </div>
        <div class="muted" style="font-size:12px;margin-top:8px">restart after saving keys — the container reads .env at start (needs Docker running)</div>
      </div>
      <div class="card"><h3>Storage</h3>
        <label>Database</label><div class="mono muted">${esc(cfg.config.CORTEX_DB || "data/cortex.db")}</div>
        <label>Budgets file</label><div class="mono muted">config/registries/models.yaml</div>
        <label>Registries</label><div class="mono muted">config/registries/ — drop an agent .md in agents/ and restart</div>
      </div>
    </div>`;

  $("#k-save").onclick = async () => {
    const body = {};
    for (const key of Object.keys(KEY_META)) {
      const val = $(`#k-${key}`).value.trim();
      if (val) body[key] = val;
    }
    const gwUrl = $("#c-gwurl").value.trim();
    if (gwUrl && gwUrl !== (cfg.config.CORTEX_GATEWAY_URL || "")) body.CORTEX_GATEWAY_URL = gwUrl;
    if (!Object.keys(body).length) return toast("nothing to save — paste a key first", false);
    try {
      const res = await api("/settings/keys", { method: "PUT", body });
      toast(`saved: ${res.saved.join(", ")}`);
      render();
    } catch (err) { toast(err.message, false); }
  };
  $("#gw-restart").onclick = async () => {
    toast("restarting gateway…");
    try {
      await api("/settings/gateway/restart", { method: "POST" });
      toast("gateway restarted");
      setTimeout(render, 1500);
    } catch (err) { toast(err.message, false); }
  };
}

render();
refreshSidebar();
