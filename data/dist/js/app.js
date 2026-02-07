/**
 * AetherPackBot Dashboard - app.js
 * Full-featured management console
 */

// ─── API Layer ───
const BASE = location.origin;
let TOKEN = localStorage.getItem("token") || "";

async function api(path, opts = {}) {
    const url = `${BASE}${path}`;
    const headers = { "Content-Type": "application/json" };
    if (TOKEN) headers["Authorization"] = `Bearer ${TOKEN}`;
    const res = await fetch(url, { ...opts, headers });
    const json = await res.json().catch(() => null);
    if (!res.ok) {
        const msg = json?.message || `HTTP ${res.status}`;
        throw new Error(msg);
    }
    if (json?.status === "error") throw new Error(json.message || "Unknown error");
    return json?.data ?? json;
}

// ─── Notifications ───
function notify(msg, type = "info") {
    const area = document.getElementById("notify-area");
    const el = document.createElement("div");
    el.className = `notification ${type}`;
    el.textContent = msg;
    area.appendChild(el);
    setTimeout(() => { el.style.opacity = "0"; setTimeout(() => el.remove(), 300); }, 3500);
}

// ─── Provider Type Metadata (local cache, updated from /api/providers/types) ───
let providerTypes = {};
async function loadProviderTypes() {
    try {
        const list = await api("/api/providers/types");
        if (Array.isArray(list)) {
            providerTypes = {};
            list.forEach(t => { providerTypes[t.type] = t; });
        }
    } catch { /* use defaults */ }
}

// ─── Main App ───
const app = {
    current: "home",
    chatHistory: [],

    // Auth
    async login() {
        const u = document.getElementById("username").value.trim();
        const p = document.getElementById("password").value.trim();
        const errEl = document.getElementById("login-error");
        if (!u || !p) { errEl.textContent = "请输入用户名和密码"; return; }
        try {
            const data = await api("/api/auth/login", {
                method: "POST",
                body: JSON.stringify({ username: u, password: p }),
            });
            TOKEN = data.token;
            localStorage.setItem("token", TOKEN);
            errEl.textContent = "";
            this.enterApp();
        } catch (e) {
            errEl.textContent = e.message || "登录失败";
        }
    },

    logout() {
        TOKEN = "";
        localStorage.removeItem("token");
        document.getElementById("app-layout").classList.add("hidden");
        document.getElementById("login-screen").style.display = "";
        document.getElementById("password").value = "";
    },

    async enterApp() {
        document.getElementById("login-screen").style.display = "none";
        document.getElementById("app-layout").classList.remove("hidden");
        document.getElementById("app-layout").style.display = "flex";
        await loadProviderTypes();
        this.nav("home");
    },

    // Navigation
    nav(view) {
        this.current = view;
        document.querySelectorAll(".view").forEach(v => v.classList.add("hidden"));
        const el = document.getElementById(`view-${view}`);
        if (el) el.classList.remove("hidden");

        document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
        const navItems = document.querySelectorAll(".nav-item");
        const labels = { home: "仪表盘", platforms: "消息平台", providers: "模型提供商", persona: "人格管理", plugins: "扩展插件", chat: "在线聊天", settings: "系统设置", logs: "控制台日志" };
        navItems.forEach(n => { if (n.textContent.includes(labels[view] || "___")) n.classList.add("active"); });

        // Load data for the view
        const loaders = {
            home: () => this.loadDashboard(),
            platforms: () => this.loadPlatforms(),
            providers: () => this.loadProviders(),
            persona: () => this.loadPersonas(),
            plugins: () => this.loadPlugins(),
            chat: () => this.loadChat(),
            settings: () => this.loadSettings(),
            logs: () => this.fetchLogs(),
        };
        if (loaders[view]) loaders[view]();
    },

    // ─── Dashboard ───
    async loadDashboard() {
        try {
            const data = await api("/api/status");
            document.getElementById("stat-platforms").textContent = data.platforms?.length ?? 0;
            document.getElementById("stat-providers").textContent = data.providers?.length ?? 0;
            document.getElementById("stat-plugins").textContent = data.plugins?.length ?? 0;

            const uptime = data.uptime || 0;
            const h = Math.floor(uptime / 3600);
            const m = Math.floor((uptime % 3600) / 60);
            document.getElementById("stat-uptime").textContent = h > 0 ? `${h}h ${m}m` : `${m}m`;

            const cpu = data.cpu_percent ?? 0;
            document.getElementById("stat-cpu").textContent = `${cpu.toFixed(1)}%`;
            document.getElementById("stat-cpu-bar").style.width = `${Math.min(cpu, 100)}%`;
            document.getElementById("stat-mem").textContent = `${data.memory_mb ?? 0} MB`;

            const ver = data.version || "1.0.0";
            document.getElementById("sidebar-version").textContent = `v${ver}`;
        } catch (e) {
            notify("获取状态失败: " + e.message, "error");
        }
    },

    // ─── Platforms ───
    async loadPlatforms() {
        const container = document.getElementById("platforms-list");
        try {
            const list = await api("/api/platforms");
            if (!Array.isArray(list) || list.length === 0) {
                container.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><div class="icon">📱</div><p>暂无消息平台</p><button class="btn btn-primary mt-4" onclick="app.modals.openPlatform()">+ 添加第一个平台</button></div>`;
                return;
            }
            container.innerHTML = list.map(p => {
                const running = p.status === "running" || p.enabled;
                const statusBadge = running
                    ? `<span class="badge badge-success">运行中</span>`
                    : `<span class="badge badge-secondary">已停止</span>`;
                return `<div class="card"><div class="flex justify-between items-center"><h3>${this._escHtml(p.name || p.id)}</h3>${statusBadge}</div><p class="text-sm text-gray mt-2">类型: ${this._escHtml(p.type)} &nbsp; ID: ${this._escHtml(p.id)}</p><div class="flex gap-2 mt-4"><button class="btn btn-sm btn-secondary" onclick="app.actions.togglePlatform('${p.id}')">⏯ ${running ? '停止' : '启动'}</button><button class="btn btn-sm btn-secondary" onclick="app.modals.openPlatform('${p.id}')">✏️ 编辑</button><button class="btn btn-sm btn-danger" onclick="app.actions.deletePlatform('${p.id}')">🗑 删除</button></div></div>`;
            }).join("");
        } catch (e) {
            container.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><p>加载失败: ${this._escHtml(e.message)}</p></div>`;
        }
    },

    // ─── Providers ───
    async loadProviders() {
        const container = document.getElementById("providers-list");
        try {
            const list = await api("/api/providers");
            if (!Array.isArray(list) || list.length === 0) {
                container.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><div class="icon">✨</div><p>暂无模型提供商</p><button class="btn btn-primary mt-4" onclick="app.modals.openProvider()">+ 添加第一个提供商</button></div>`;
                return;
            }
            container.innerHTML = list.map(p => {
                const isDefault = p.is_default ? `<span class="badge" style="background:#fef3c7;color:#92400e;">默认</span>` : "";
                const statusBadge = p.status === "running"
                    ? `<span class="badge badge-success">可用</span>`
                    : `<span class="badge badge-secondary">不可用</span>`;
                return `<div class="card"><div class="flex justify-between items-center"><h3>${this._escHtml(p.display_name || p.type_display || p.type)}</h3><div class="flex gap-2">${isDefault}${statusBadge}</div></div><p class="text-sm text-gray mt-2">模型: <strong>${this._escHtml(p.model || '-')}</strong></p><p class="text-sm text-gray">类型: ${this._escHtml(p.type_display || p.type)} &nbsp; ID: ${this._escHtml(p.id)}</p><div class="flex gap-2 mt-4">${!p.is_default ? `<button class="btn btn-sm btn-secondary" onclick="app.actions.setDefaultProvider('${p.id}')">⭐ 设为默认</button>` : ''}<button class="btn btn-sm btn-secondary" onclick="app.actions.healthCheck('${p.id}')">🩺 检测</button><button class="btn btn-sm btn-danger" onclick="app.actions.deleteProvider('${p.id}')">🗑 删除</button></div></div>`;
            }).join("");
        } catch (e) {
            container.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><p>加载失败: ${this._escHtml(e.message)}</p></div>`;
        }
    },

    // ─── Persona ───
    async loadPersonas() {
        const container = document.getElementById("persona-list");
        try {
            const cfg = await api("/api/config");
            const personas = cfg.personas || [];
            const defaultName = cfg.default_persona || "";
            if (personas.length === 0) {
                container.innerHTML = `<div class="empty-state"><div class="icon">❤️</div><p>暂无人格配置</p><button class="btn btn-primary mt-4" onclick="app.modals.openPersona()">+ 新建人格</button></div>`;
                return;
            }
            container.innerHTML = personas.map((p, i) => {
                const isActive = p.name === defaultName;
                return `<div class="card persona-card ${isActive ? 'active' : ''}"><div class="flex justify-between items-center"><h3>${this._escHtml(p.name || '未命名')}</h3><div class="flex gap-2">${isActive ? '<span class="badge badge-success">当前使用</span>' : `<button class="btn btn-sm btn-secondary" onclick="app.actions.setDefaultPersona('${this._escHtml(p.name)}')">设为默认</button>`}</div></div><p class="text-sm text-gray mt-2">${this._escHtml(p.description || p.desc || '无描述')}</p><div style="background:#f8fafc;border-radius:6px;padding:10px;margin-top:8px;max-height:120px;overflow-y:auto;"><pre style="margin:0;font-size:12px;white-space:pre-wrap;color:#475569;">${this._escHtml((p.prompt || p.system_prompt || p.content || '').substring(0, 500))}</pre></div><div class="flex gap-2 mt-4"><button class="btn btn-sm btn-secondary" onclick='app.modals.editPersona(${i})'>✏️ 编辑</button><button class="btn btn-sm btn-danger" onclick="app.actions.deletePersona(${i})">🗑 删除</button></div></div>`;
            }).join("");
        } catch (e) {
            container.innerHTML = `<div class="empty-state"><p>加载失败: ${this._escHtml(e.message)}</p></div>`;
        }
    },

    // ─── Plugins ───
    async loadPlugins() {
        const container = document.getElementById("plugins-list");
        try {
            const list = await api("/api/plugins");
            if (!Array.isArray(list) || list.length === 0) {
                container.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><div class="icon">🧩</div><p>暂无扩展插件</p></div>`;
                return;
            }
            container.innerHTML = list.map(p => {
                const badge = p.status === "ACTIVE"
                    ? `<span class="badge badge-success">运行中</span>`
                    : `<span class="badge badge-secondary">${this._escHtml(p.status)}</span>`;
                return `<div class="card"><div class="flex justify-between items-center"><h3>${this._escHtml(p.name)}</h3>${badge}</div><p class="text-sm text-gray mt-2">${this._escHtml(p.description || '无描述')}</p><p class="text-sm text-gray">版本: ${this._escHtml(p.version || '-')} &nbsp; 作者: ${this._escHtml(p.author || '-')}</p><div class="flex gap-2 mt-4"><button class="btn btn-sm btn-secondary" onclick="app.actions.reloadPlugin('${this._escHtml(p.name)}')">🔄 重载</button></div></div>`;
            }).join("");
        } catch (e) {
            container.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><p>加载失败: ${this._escHtml(e.message)}</p></div>`;
        }
    },

    // ─── Chat ───
    async loadChat() {
        // Populate provider selector
        try {
            const providers = await api("/api/providers");
            const sel = document.getElementById("chat-provider-select");
            sel.innerHTML = `<option value="">默认提供商</option>` +
                (Array.isArray(providers) ? providers.map(p =>
                    `<option value="${p.id}">${this._escHtml(p.display_name || p.type)} (${this._escHtml(p.model || '')})</option>`
                ).join("") : "");
        } catch { /* ignore */ }
        this.fetchChat();
    },

    async fetchChat() {
        try {
            const data = await api("/api/chat/history?limit=50");
            this.chatHistory = data?.history || [];
            this._renderChat();
        } catch { /* first time, no history */ }
    },

    _renderChat() {
        const container = document.getElementById("chat-messages");
        if (this.chatHistory.length === 0) {
            container.innerHTML = `<div class="empty-state"><div class="icon">💬</div><p>开始聊天吧！</p></div>`;
            return;
        }
        container.innerHTML = this.chatHistory.map(m => {
            const isUser = m.role === "user";
            const time = m.time ? new Date(m.time).toLocaleTimeString() : "";
            return `<div class="msg-row msg-${m.role}"><div class="msg-meta"><span>${isUser ? '你' : 'Bot'}</span><span>${time}</span></div><div class="msg-bubble">${this._escHtml(m.content)}</div></div>`;
        }).join("");
        container.scrollTop = container.scrollHeight;
    },

    async sendChat() {
        const input = document.getElementById("chat-input");
        const msg = input.value.trim();
        if (!msg) return;
        input.value = "";
        input.disabled = true;

        // Optimistic UI
        this.chatHistory.push({ role: "user", content: msg, time: new Date().toISOString() });
        this._renderChat();

        try {
            const providerId = document.getElementById("chat-provider-select").value;
            const body = {
                message: msg,
                history: this.chatHistory.filter(m => m.role !== "system").slice(-20).map(m => ({ role: m.role, content: m.content })),
            };
            if (providerId) body.provider_id = providerId;
            const data = await api("/api/chat", { method: "POST", body: JSON.stringify(body) });
            this.chatHistory.push({ role: "assistant", content: data.content, time: new Date().toISOString() });
            this._renderChat();
        } catch (e) {
            notify("发送失败: " + e.message, "error");
            this.chatHistory.push({ role: "assistant", content: `[错误] ${e.message}`, time: new Date().toISOString() });
            this._renderChat();
        } finally {
            input.disabled = false;
            input.focus();
        }
    },

    // ─── Settings ───
    async loadSettings() {
        try {
            const cfg = await api("/api/config");
            document.getElementById("conf-agent-name").value = cfg.agent?.name || cfg.agent_name || "";
            document.getElementById("conf-wake-prefixes").value = (cfg.agent?.wake_prefixes || []).join(", ");
            document.getElementById("conf-default-provider").value = cfg.agent?.default_provider || "";
            document.getElementById("conf-web-host").value = cfg.web?.host || "0.0.0.0";
            document.getElementById("conf-web-port").value = cfg.web?.port || 6185;
            document.getElementById("conf-reply-at").checked = cfg.reply?.at_sender ?? false;
            document.getElementById("conf-reply-quote").checked = cfg.reply?.quote_original ?? false;
            document.getElementById("conf-reply-prefix").checked = cfg.reply?.add_prefix ?? false;
            document.getElementById("conf-reply-prefix-tpl").value = cfg.reply?.prefix_template || "";
        } catch (e) {
            notify("加载设置失败: " + e.message, "error");
        }
    },

    settingsTab(tab, btn) {
        document.querySelectorAll(".settings-panel").forEach(p => p.classList.add("hidden"));
        document.getElementById(`settings-${tab}`).classList.remove("hidden");
        document.querySelectorAll(".tab-bar button").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
    },

    // ─── Logs ───
    async fetchLogs() {
        const container = document.getElementById("logs-container");
        try {
            const logs = await api("/api/logs?count=200");
            if (!Array.isArray(logs) || logs.length === 0) {
                container.textContent = "暂无日志";
                return;
            }
            container.innerHTML = logs.map(l => {
                const levelColor = { ERROR: "#ef4444", WARNING: "#f59e0b", INFO: "#3b82f6", DEBUG: "#6b7280" }[l.level] || "#d4d4d4";
                const ts = l.timestamp ? l.timestamp.split("T")[1]?.substring(0, 8) : "";
                return `<div><span style="color:#6b7280">${ts}</span> <span style="color:${levelColor};font-weight:600">[${l.level}]</span> <span style="color:#94a3b8">${l.logger || ""}</span> ${this._escHtml(l.message)}</div>`;
            }).join("");
            if (document.getElementById("auto-scroll-logs")?.checked) {
                container.scrollTop = container.scrollHeight;
            }
        } catch (e) {
            container.textContent = "加载日志失败: " + e.message;
        }
    },

    // ─── Render helpers ───
    render: {
        onProvTypeChange() {
            const type = document.getElementById("prov-type").value;
            const info = providerTypes[type] || {};
            const modelInput = document.getElementById("prov-model");
            const baseInput = document.getElementById("prov-base-url");
            const keyField = document.getElementById("field-prov-key");
            const hintEl = document.getElementById("prov-models-hint");

            modelInput.placeholder = info.default_model || "模型 ID";
            if (!modelInput.value) modelInput.value = info.default_model || "";
            baseInput.placeholder = info.default_api_base || "留空使用默认";
            if (info.default_api_base && !baseInput.value) baseInput.value = info.default_api_base;
            keyField.style.display = (info.requires_api_key === false) ? "none" : "";
            hintEl.textContent = info.models?.length ? "可选: " + info.models.join(", ") : "";
        },

        onPlatTypeChange() {
            const type = document.getElementById("plat-type").value;
            const onebotOpts = document.getElementById("field-onebot-opts");
            const tokenField = document.getElementById("field-plat-token");
            const urlField = document.getElementById("field-plat-url");
            const tokenInput = document.getElementById("plat-token");
            const tokenLabel = tokenField.querySelector("label");

            if (type === "qq_onebot") {
                onebotOpts.classList.remove("hidden");
                tokenField.style.display = "none";
                urlField.style.display = "none";
            } else {
                onebotOpts.classList.add("hidden");
                tokenField.style.display = "";
                urlField.style.display = "none";

                // Update label and placeholder per platform type
                if (type === "dingtalk") {
                    tokenLabel.textContent = "Client ID : Client Secret";
                    tokenInput.placeholder = "client_id:client_secret";
                } else if (type === "lark") {
                    tokenLabel.textContent = "App ID : App Secret";
                    tokenInput.placeholder = "app_id:app_secret";
                } else {
                    tokenLabel.textContent = "Token / 凭证";
                    tokenInput.placeholder = "Bot Token";
                }
            }
        },
    },

    // ─── Modals ───
    modals: {
        _editingId: null,
        _editingPersonaIdx: null,

        openProvider(editId) {
            this._editingId = editId || null;
            document.getElementById("modal-provider-title").textContent = editId ? "编辑提供商" : "添加提供商";
            // Reset form to defaults first
            document.getElementById("prov-type").value = "openai";
            document.getElementById("prov-name").value = "";
            document.getElementById("prov-key").value = "";
            document.getElementById("prov-base-url").value = "";
            document.getElementById("prov-model").value = "";

            if (editId) {
                // Load saved values for editing
                api("/api/providers").then(list => {
                    const p = (list || []).find(x => x.id === editId);
                    if (p) {
                        document.getElementById("prov-type").value = p.type || "openai";
                        document.getElementById("prov-name").value = p.display_name || p.name || "";
                        document.getElementById("prov-key").value = p.api_key || "";
                        document.getElementById("prov-base-url").value = p.api_base_url || "";
                        document.getElementById("prov-model").value = p.model || "";
                        app.render.onProvTypeChange();
                    }
                }).catch(() => {});
            }

            app.render.onProvTypeChange();
            document.getElementById("modal-provider").classList.add("show");
        },

        async openPlatform(editId) {
            this._editingId = editId || null;
            document.getElementById("modal-platform-title").textContent = editId ? "编辑平台" : "添加平台";
            // Reset form to defaults first
            document.getElementById("plat-type").value = "telegram";
            document.getElementById("plat-name").value = "";
            document.getElementById("plat-token").value = "";
            document.getElementById("plat-url").value = "";
            document.getElementById("plat-ws-host").value = "0.0.0.0";
            document.getElementById("plat-ws-port").value = "8081";
            document.getElementById("plat-ws-token").value = "";

            if (editId) {
                // Load saved config for editing
                try {
                    const p = await api(`/api/platforms/${editId}`);
                    if (p) {
                        document.getElementById("plat-type").value = p.type || "telegram";
                        document.getElementById("plat-name").value = p.name || p.id || "";

                        if (p.type === "qq_onebot") {
                            const cfg = p.config || {};
                            document.getElementById("plat-ws-host").value = cfg.host || p.host || p.ws_reverse_host || "0.0.0.0";
                            document.getElementById("plat-ws-port").value = cfg.port || p.port || p.ws_reverse_port || "8081";
                            document.getElementById("plat-ws-token").value = cfg.token || p.token || "";
                        } else if (p.type === "dingtalk") {
                            const cid = p.client_id || "";
                            const csecret = p.client_secret || "";
                            document.getElementById("plat-token").value = (cid && csecret) ? `${cid}:${csecret}` : (p.token || "");
                        } else if (p.type === "lark") {
                            const aid = p.app_id || "";
                            const asecret = p.app_secret || "";
                            document.getElementById("plat-token").value = (aid && asecret) ? `${aid}:${asecret}` : (p.token || "");
                        } else {
                            document.getElementById("plat-token").value = p.bot_token || p.token || "";
                        }
                    }
                } catch (e) {
                    // Failed to load, use defaults
                }
            }

            app.render.onPlatTypeChange();
            document.getElementById("modal-platform").classList.add("show");
        },

        openPersona() {
            this._editingPersonaIdx = null;
            document.getElementById("modal-persona-title").textContent = "新建人格";
            document.getElementById("persona-name").value = "";
            document.getElementById("persona-desc").value = "";
            document.getElementById("persona-prompt").value = "";
            document.getElementById("modal-persona").classList.add("show");
        },

        async editPersona(idx) {
            this._editingPersonaIdx = idx;
            document.getElementById("modal-persona-title").textContent = "编辑人格";
            try {
                const cfg = await api("/api/config");
                const p = (cfg.personas || [])[idx];
                if (!p) return;
                document.getElementById("persona-name").value = p.name || "";
                document.getElementById("persona-desc").value = p.description || p.desc || "";
                document.getElementById("persona-prompt").value = p.prompt || p.system_prompt || p.content || "";
                document.getElementById("modal-persona").classList.add("show");
            } catch (e) {
                notify("加载人格失败: " + e.message, "error");
            }
        },

        close() {
            document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("show"));
        },
    },

    // ─── Actions ───
    actions: {
        // Provider CRUD
        async saveProvider() {
            const data = {
                type: document.getElementById("prov-type").value,
                name: document.getElementById("prov-name").value.trim(),
                api_key: document.getElementById("prov-key").value.trim(),
                api_base_url: document.getElementById("prov-base-url").value.trim(),
                model: document.getElementById("prov-model").value.trim(),
            };
            // Remove empty optional fields
            if (!data.api_key) delete data.api_key;
            if (!data.api_base_url) delete data.api_base_url;
            if (!data.name) data.name = data.type;

            const editId = app.modals._editingId;
            try {
                if (editId) {
                    await api(`/api/providers/${editId}`, { method: "PUT", body: JSON.stringify(data) });
                    notify("提供商已更新", "success");
                } else {
                    await api("/api/providers", { method: "POST", body: JSON.stringify(data) });
                    notify("提供商已添加", "success");
                }
                app.modals.close();
                app.loadProviders();
            } catch (e) {
                notify("操作失败: " + e.message, "error");
            }
        },

        async deleteProvider(id) {
            if (!confirm("确定要删除这个提供商吗？")) return;
            try {
                await api(`/api/providers/${id}`, { method: "DELETE" });
                notify("提供商已删除", "success");
                app.loadProviders();
            } catch (e) {
                notify("删除失败: " + e.message, "error");
            }
        },

        async setDefaultProvider(id) {
            try {
                await api(`/api/providers/${id}/default`, { method: "POST" });
                notify("已设为默认提供商", "success");
                app.loadProviders();
            } catch (e) {
                notify("操作失败: " + e.message, "error");
            }
        },

        async healthCheck(id) {
            try {
                const data = await api(`/api/providers/${id}/health`);
                if (data.healthy) {
                    notify("连接正常 ✓", "success");
                } else {
                    notify("连接失败 ✗", "error");
                }
            } catch (e) {
                notify("检测失败: " + e.message, "error");
            }
        },

        // Platform CRUD
        async savePlatform() {
            const type = document.getElementById("plat-type").value;
            const nameVal = document.getElementById("plat-name").value.trim();
            const data = {
                type,
                name: nameVal || type,
            };
            // Only set ID if editing; for new platforms, backend auto-generates
            if (nameVal) data.id = nameVal;

            if (type === "qq_onebot") {
                const wsToken = document.getElementById("plat-ws-token").value.trim();
                data.config = {
                    host: document.getElementById("plat-ws-host").value.trim() || "0.0.0.0",
                    port: parseInt(document.getElementById("plat-ws-port").value) || 8081,
                };
                if (wsToken) data.token = wsToken;
            } else if (type === "dingtalk") {
                const token = document.getElementById("plat-token").value.trim();
                // DingTalk: token field holds "client_id:client_secret"
                if (token.includes(":")) {
                    const [cid, csecret] = token.split(":", 2);
                    data.client_id = cid;
                    data.client_secret = csecret;
                } else if (token) {
                    data.token = token; // fallback
                }
            } else if (type === "lark") {
                const token = document.getElementById("plat-token").value.trim();
                // Lark: token field holds "app_id:app_secret"
                if (token.includes(":")) {
                    const [aid, asecret] = token.split(":", 2);
                    data.app_id = aid;
                    data.app_secret = asecret;
                } else if (token) {
                    data.token = token; // fallback
                }
            } else {
                // telegram, discord, slack: bot_token
                const token = document.getElementById("plat-token").value.trim();
                if (token) data.bot_token = token;
            }

            const editId = app.modals._editingId;
            try {
                if (editId) {
                    await api(`/api/platforms/${editId}`, { method: "PUT", body: JSON.stringify(data) });
                    notify("平台已更新", "success");
                } else {
                    await api("/api/platforms", { method: "POST", body: JSON.stringify(data) });
                    notify("平台已添加", "success");
                }
                app.modals.close();
                app.loadPlatforms();
            } catch (e) {
                notify("操作失败: " + e.message, "error");
            }
        },

        async deletePlatform(id) {
            if (!confirm("确定要删除这个平台吗？")) return;
            try {
                await api(`/api/platforms/${id}`, { method: "DELETE" });
                notify("平台已删除", "success");
                app.loadPlatforms();
            } catch (e) {
                notify("删除失败: " + e.message, "error");
            }
        },

        async togglePlatform(id) {
            try {
                const data = await api(`/api/platforms/${id}/toggle`, { method: "POST" });
                notify(data.enabled ? "平台已启动" : "平台已停止", "success");
                app.loadPlatforms();
            } catch (e) {
                notify("操作失败: " + e.message, "error");
            }
        },

        // Persona CRUD
        async savePersona() {
            const name = document.getElementById("persona-name").value.trim();
            const desc = document.getElementById("persona-desc").value.trim();
            const prompt = document.getElementById("persona-prompt").value.trim();
            if (!name) { notify("请输入人格名称", "error"); return; }
            if (!prompt) { notify("请输入系统提示词", "error"); return; }

            try {
                const cfg = await api("/api/config");
                const personas = cfg.personas || [];
                const idx = app.modals._editingPersonaIdx;
                const entry = { name, description: desc, prompt };

                if (idx !== null && idx >= 0 && idx < personas.length) {
                    personas[idx] = entry;
                } else {
                    personas.push(entry);
                }

                await api("/api/config", { method: "PUT", body: JSON.stringify({ personas }) });
                notify("人格已保存", "success");
                app.modals.close();
                app.loadPersonas();
            } catch (e) {
                notify("保存失败: " + e.message, "error");
            }
        },

        async deletePersona(idx) {
            if (!confirm("确定要删除这个人格吗？")) return;
            try {
                const cfg = await api("/api/config");
                const personas = cfg.personas || [];
                if (idx >= 0 && idx < personas.length) {
                    personas.splice(idx, 1);
                    await api("/api/config", { method: "PUT", body: JSON.stringify({ personas }) });
                    notify("人格已删除", "success");
                    app.loadPersonas();
                }
            } catch (e) {
                notify("删除失败: " + e.message, "error");
            }
        },

        async setDefaultPersona(name) {
            try {
                await api("/api/config", { method: "PUT", body: JSON.stringify({ default_persona: name }) });
                notify(`已切换默认人格为: ${name}`, "success");
                app.loadPersonas();
            } catch (e) {
                notify("操作失败: " + e.message, "error");
            }
        },

        // Plugin actions
        async reloadPlugin(name) {
            try {
                await api(`/api/plugins/${name}/reload`, { method: "POST" });
                notify("插件已重载", "success");
                app.loadPlugins();
            } catch (e) {
                notify("重载失败: " + e.message, "error");
            }
        },

        // Settings save
        async saveSettings() {
            const wakePrefixes = document.getElementById("conf-wake-prefixes").value
                .split(",").map(s => s.trim()).filter(Boolean);
            try {
                await api("/api/config", {
                    method: "PUT",
                    body: JSON.stringify({
                        "agent": {
                            name: document.getElementById("conf-agent-name").value.trim(),
                            wake_prefixes: wakePrefixes,
                            default_provider: document.getElementById("conf-default-provider").value.trim(),
                        }
                    }),
                });
                notify("设置已保存", "success");
            } catch (e) {
                notify("保存失败: " + e.message, "error");
            }
        },

        async saveWebSettings() {
            try {
                await api("/api/config", {
                    method: "PUT",
                    body: JSON.stringify({
                        "web": {
                            host: document.getElementById("conf-web-host").value.trim(),
                            port: parseInt(document.getElementById("conf-web-port").value) || 6185,
                        }
                    }),
                });
                notify("Web 设置已保存 (重启生效)", "success");
            } catch (e) {
                notify("保存失败: " + e.message, "error");
            }
        },

        async saveReplySettings() {
            try {
                await api("/api/config", {
                    method: "PUT",
                    body: JSON.stringify({
                        "reply": {
                            at_sender: document.getElementById("conf-reply-at").checked,
                            quote_original: document.getElementById("conf-reply-quote").checked,
                            add_prefix: document.getElementById("conf-reply-prefix").checked,
                            prefix_template: document.getElementById("conf-reply-prefix-tpl").value.trim(),
                        }
                    }),
                });
                notify("回复设置已保存", "success");
            } catch (e) {
                notify("保存失败: " + e.message, "error");
            }
        },

        async changePassword() {
            const newPw = document.getElementById("conf-new-password").value;
            const newPw2 = document.getElementById("conf-new-password2").value;
            const newUser = document.getElementById("conf-new-username").value.trim();
            if (newPw && newPw !== newPw2) { notify("两次密码不一致", "error"); return; }
            if (!newPw && !newUser) { notify("请输入新密码或用户名", "error"); return; }
            try {
                const update = {};
                if (newUser) update.admin_username = newUser;
                if (newPw) update.admin_password = newPw;
                await api("/api/config", {
                    method: "PUT",
                    body: JSON.stringify({ web: update }),
                });
                notify("账号信息已更新，下次登录生效", "success");
                document.getElementById("conf-new-password").value = "";
                document.getElementById("conf-new-password2").value = "";
            } catch (e) {
                notify("修改失败: " + e.message, "error");
            }
        },
    },

    // ─── Utils ───
    _escHtml(s) {
        if (!s) return "";
        const d = document.createElement("div");
        d.textContent = String(s);
        return d.innerHTML;
    },
};

// ─── Auto-init ───
(async function init() {
    if (TOKEN) {
        try {
            await api("/api/auth/verify");
            app.enterApp();
        } catch {
            app.logout();
        }
    }
    // Auto-refresh logs every 5s when on logs view
    setInterval(() => {
        if (app.current === "logs") app.fetchLogs();
    }, 5000);
    // Auto-refresh dashboard every 10s
    setInterval(() => {
        if (app.current === "home") app.loadDashboard();
    }, 10000);
})();
