const BASE_PATH = window.location.pathname.replace(/\/$/, "");
const messageFeed = document.getElementById("message-feed");
const typingArea = document.getElementById("typing-area");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const agentListEl = document.getElementById("agent-list");
const channelListEl = document.getElementById("channel-list");
const sidebarToggle = document.getElementById("sidebar-toggle");
const sidebar = document.getElementById("sidebar");
const channelTitle = document.getElementById("channel-title");
const channelMeta = document.getElementById("channel-meta");
const addChannelBtn = document.getElementById("add-channel-btn");
const createModal = document.getElementById("create-channel-modal");
const modalClose = document.getElementById("modal-close");
const modalCancel = document.getElementById("modal-cancel");
const modalCreate = document.getElementById("modal-create");
const channelNameInput = document.getElementById("channel-name-input");
const channelDescInput = document.getElementById("channel-desc-input");
const agentCheckboxes = document.getElementById("agent-checkboxes");
const schedulesSection = document.getElementById("schedules-section");
const schedulesList = document.getElementById("schedule-list");
const scheduleCount = document.getElementById("schedule-count");
const schedulesToggle = document.getElementById("schedules-toggle");

let allAgents = {};
let availableAgents = [];
let channels = [];
let activeChannelId = "workspace";
let processing = false;
let msgCounter = 0;
let pendingToolCards = {};
let pendingDocuments = {};
let demoRunning = false;
let messageQueue = [];
let currentAbortController = null;
let pendingChannelSwitch = null;

marked.setOptions({
    highlight: function (code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            return hljs.highlight(code, { language: lang }).value;
        }
        return hljs.highlightAuto(code).value;
    },
    breaks: true,
});

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(index) {
    if (typeof index === "number" && index < 50) {
        const base = new Date();
        base.setMinutes(base.getMinutes() - 30 + index * 2);
        return base.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    }
    if (typeof index === "number" && index > 1000000000) {
        return new Date(index * 1000).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    }
    return new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function highlightMentions(html) {
    for (const [id, agent] of Object.entries(allAgents)) {
        const regex = new RegExp(`@${agent.name}\\b`, "g");
        html = html.replace(
            regex,
            `<span class="mention" style="color:${agent.color}">@${agent.name}</span>`
        );
    }
    return html;
}

function renderToolCards(toolUseList) {
    if (!toolUseList || toolUseList.length === 0) return "";
    return toolUseList
        .map(
            (t) => `
        <div class="tool-card">
            <div class="tool-card-header" onclick="toggleTool(this)">
                <span class="tool-icon">&#9881;&#65039;</span>
                <span class="tool-name">${escapeHtml(t.tool)}</span>
                <span class="tool-input-preview">${escapeHtml(t.input || "")}</span>
                <span class="tool-expand">&#9660;</span>
            </div>
            <div class="tool-card-body">${escapeHtml(t.result || "")}</div>
        </div>`
        )
        .join("");
}

window.toggleTool = function (header) {
    const body = header.nextElementSibling;
    const arrow = header.querySelector(".tool-expand");
    body.classList.toggle("open");
    arrow.classList.toggle("open");
};

const FORMAT_ICONS = {
    csv: "\uD83D\uDCCA",
    html: "\uD83C\uDF10",
    pdf: "\uD83D\uDCC4",
    png: "\uD83D\uDDBC\uFE0F",
};

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function renderDocumentCards(documents) {
    if (!documents || documents.length === 0) return "";
    return documents.map(doc => {
        const icon = FORMAT_ICONS[doc.format] || "\uD83D\uDCC1";
        const size = formatFileSize(doc.size || 0);
        const url = BASE_PATH + doc.url;
        return `
        <a href="${url}" class="document-card" download>
            <span class="doc-icon">${icon}</span>
            <div class="doc-info">
                <span class="doc-name">${escapeHtml(doc.display_name || doc.filename)}</span>
                <span class="doc-meta">${doc.format.toUpperCase()} &middot; ${size}</span>
            </div>
            <span class="doc-download">&#11015;</span>
        </a>`;
    }).join("");
}

function renderMessage(msg) {
    const el = document.createElement("div");
    el.className = "message" + (msg.is_user ? " user-msg" : "") + (msg._queued ? " queued-msg" : "");
    el.id = "msg-" + msgCounter++;

    const rawHtml = msg._escaped
        ? `<p>${msg.content}</p>`
        : marked.parse(msg.content || "");
    const contentHtml = highlightMentions(rawHtml);
    const toolHtml = renderToolCards(msg.tool_use);
    const docHtml = renderDocumentCards(msg.documents);
    const ts = msg.timestamp || msg.ts_offset;
    const queuedBadge = msg._queued ? '<span class="queued-label">queued</span>' : '';

    el.innerHTML = `
        <div class="msg-avatar" style="background:${msg.color}">${msg.avatar}</div>
        <div class="msg-body">
            <div class="msg-header">
                <span class="msg-name" style="color:${msg.color}">${escapeHtml(msg.agent_name)}</span>
                ${queuedBadge}
                <span class="msg-time">${formatTime(ts)}</span>
            </div>
            <div class="msg-content">${contentHtml}</div>
            ${toolHtml}
            ${docHtml}
        </div>
    `;

    messageFeed.appendChild(el);
    messageFeed.scrollTop = messageFeed.scrollHeight;
    return el;
}

function showTyping(agentData) {
    const name = agentData.agent_name || agentData.name || "Agent";
    const avatar = agentData.avatar || "&#129302;";
    const color = agentData.color || "#666";

    typingArea.innerHTML = `
        <div class="typing-indicator">
            <div class="typing-avatar" style="background:${color}">${avatar}</div>
            <span class="typing-text">
                <strong>${escapeHtml(name)}</strong> is thinking
                <span class="typing-dots"><span></span><span></span><span></span></span>
            </span>
        </div>
    `;
    messageFeed.scrollTop = messageFeed.scrollHeight;
}

function showToolActivity(agentData, toolName) {
    const name = agentData.agent_name || agentData.name || "Agent";
    const avatar = agentData.avatar || "&#129302;";
    const color = agentData.color || "#666";

    typingArea.innerHTML = `
        <div class="typing-indicator">
            <div class="typing-avatar" style="background:${color}">${avatar}</div>
            <span class="typing-text">
                <strong>${escapeHtml(name)}</strong> is using <span class="tool-name-inline">${escapeHtml(toolName)}</span>
                <span class="typing-dots"><span></span><span></span><span></span></span>
            </span>
        </div>
    `;
    messageFeed.scrollTop = messageFeed.scrollHeight;
}

function clearTyping() {
    typingArea.innerHTML = "";
}

function setProcessing(val) {
    processing = val;
    messageInput.disabled = false;
    sendBtn.disabled = false;
    if (val) {
        sendBtn.classList.add("processing");
        sendBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>';
        sendBtn.title = "Stop";
    } else {
        sendBtn.classList.remove("processing");
        sendBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>';
        sendBtn.title = "Send";
        clearTyping();
        processQueue();
    }
    updateQueueBadge();
}

function updateQueueBadge() {
    let badge = document.getElementById("queue-badge");
    if (messageQueue.length > 0) {
        if (!badge) {
            badge = document.createElement("div");
            badge.id = "queue-badge";
            document.querySelector(".input-wrapper").appendChild(badge);
        }
        badge.textContent = messageQueue.length + " queued";
        badge.style.display = "block";
    } else if (badge) {
        badge.style.display = "none";
    }
}

function processQueue() {
    if (messageQueue.length > 0 && !processing) {
        const next = messageQueue.shift();
        updateQueueBadge();
        if (next.channelId !== activeChannelId) {
            switchChannel(next.channelId).then(() => startLiveChat(next.text));
        } else {
            startLiveChat(next.text);
        }
    } else if (pendingChannelSwitch) {
        const chId = pendingChannelSwitch;
        pendingChannelSwitch = null;
        switchChannel(chId);
    }
}

async function stopProcessing() {
    try {
        await fetch(BASE_PATH + "/stop", { method: "POST" });
    } catch (e) {
        console.error("Stop failed:", e);
    }
    messageQueue = [];
    updateQueueBadge();
    setTimeout(() => {
        if (processing) {
            setProcessing(false);
        }
    }, 3000);
}

async function loadAgents() {
    try {
        const r = await fetch(BASE_PATH + "/api/available-agents");
        const data = await r.json();
        availableAgents = data.agents;
        allAgents = {};
        for (const a of data.agents) {
            allAgents[a.id] = a;
        }
    } catch (e) {
        console.error("Failed to load agents:", e);
    }
}

function renderAgentList(agentIds) {
    const agentsToShow = agentIds
        ? agentIds.map(id => allAgents[id]).filter(Boolean)
        : Object.values(allAgents);

    agentListEl.innerHTML = agentsToShow
        .filter((a) => a.id !== "user")
        .map(
            (a) => `
        <div class="agent-item" data-agent="${a.id}">
            <div class="agent-avatar-sm" style="background:${a.color}">
                ${a.avatar}
                <div class="online-dot"></div>
            </div>
            <div class="agent-info-sm">
                <div class="agent-name-sm">${escapeHtml(a.name)}</div>
                <div class="agent-role-sm">${escapeHtml(a.role)}</div>
            </div>
        </div>`
        )
        .join("");

    channelMeta.textContent = `${agentsToShow.length} agents online`;
}

async function loadChannels() {
    try {
        const r = await fetch(BASE_PATH + "/api/channels");
        const data = await r.json();
        channels = data.channels;
        renderChannelList();
    } catch (e) {
        console.error("Failed to load channels:", e);
    }
}

function renderChannelList() {
    channelListEl.innerHTML = channels
        .map(
            (ch) => `
        <div class="channel-item${ch.id === activeChannelId ? " active" : ""}" data-channel="${ch.id}">
            <span class="channel-hash">#</span>
            <span class="channel-name-text">${escapeHtml(ch.name)}</span>
            ${ch.id !== "workspace" ? `<button class="channel-delete" data-channel-delete="${ch.id}" title="Delete channel">&times;</button>` : ""}
        </div>`
        )
        .join("");

    channelListEl.querySelectorAll(".channel-item").forEach((el) => {
        el.addEventListener("click", (e) => {
            if (e.target.classList.contains("channel-delete")) return;
            const chId = el.dataset.channel;
            if (chId !== activeChannelId) {
                switchChannel(chId);
            }
        });
    });

    channelListEl.querySelectorAll(".channel-delete").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
            e.stopPropagation();
            const chId = btn.dataset.channelDelete;
            if (confirm(`Delete #${chId}? This will also clear its history.`)) {
                await fetch(BASE_PATH + "/api/channels/" + chId, { method: "DELETE" });
                if (activeChannelId === chId) {
                    await switchChannel("workspace");
                }
                await loadChannels();
            }
        });
    });
}

async function switchChannel(channelId) {
    activeChannelId = channelId;
    const ch = channels.find((c) => c.id === channelId);
    const name = ch ? ch.name : channelId;

    channelTitle.textContent = "# " + name.toLowerCase();
    messageInput.placeholder = `Message #${name.toLowerCase()}...`;

    renderChannelList();

    if (ch && ch.agent_ids) {
        renderAgentList(ch.agent_ids);
    } else {
        renderAgentList(null);
    }

    const isWorkspace = channelId === "workspace";
    messageFeed.innerHTML = `
        <div class="feed-start">
            <div class="feed-start-icon">&#128025;</div>
            <h2>Welcome to #${escapeHtml(name.toLowerCase())}</h2>
            <p>This is where agents collaborate on your tasks. Send a message to get started.</p>
            ${isWorkspace ? '<button class="demo-btn" id="demo-btn" onclick="startDemo()">&#9654; Watch Demo</button>' : ''}
        </div>
    `;

    msgCounter = 0;

    await loadChannelHistory(channelId);

    await loadSchedules();
}

async function loadChannelHistory(channelId) {
    try {
        const r = await fetch(BASE_PATH + "/api/channels/" + channelId + "/history");
        const data = await r.json();
        if (data.messages && data.messages.length > 0) {
            for (const msg of data.messages) {
                renderMessage(msg);
            }
        }
    } catch (e) {
        console.error("Failed to load history:", e);
    }
}

async function loadSchedules() {
    try {
        const r = await fetch(BASE_PATH + "/api/schedules?channel_id=" + encodeURIComponent(activeChannelId));
        const data = await r.json();
        const schedules = data.schedules || [];

        if (schedules.length === 0) {
            schedulesSection.style.display = "none";
            return;
        }

        schedulesSection.style.display = "";
        scheduleCount.textContent = schedules.length;
        schedulesList.innerHTML = schedules
            .map(
                (s) => `
            <div class="schedule-item">
                <div class="schedule-info">
                    <div class="schedule-name">${escapeHtml(s.name)}</div>
                    <div class="schedule-freq">${escapeHtml(s.frequency)}</div>
                </div>
                <button class="schedule-cancel" data-schedule-id="${s.id}" title="Cancel schedule">&times;</button>
            </div>`
            )
            .join("");

        schedulesList.querySelectorAll(".schedule-cancel").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const id = btn.dataset.scheduleId;
                await fetch(BASE_PATH + "/api/schedules/" + id, { method: "DELETE" });
                await loadSchedules();
            });
        });
    } catch (e) {
        console.error("Failed to load schedules:", e);
    }
}

window.startDemo = async function () {
    if (demoRunning || processing) return;
    demoRunning = true;

    const demoBtn = document.getElementById("demo-btn");
    if (demoBtn) {
        demoBtn.disabled = true;
        demoBtn.textContent = "Playing...";
    }

    try {
        const r = await fetch(BASE_PATH + "/api/mock-conversation");
        const data = await r.json();
        const messages = data.messages;

        for (let i = 0; i < messages.length; i++) {
            const msg = messages[i];

            if (!msg.is_user) {
                const agent = allAgents[msg.agent_id] || {
                    name: msg.agent_name,
                    avatar: msg.avatar,
                    color: msg.color,
                };
                showTyping(agent);
                await sleep(600 + Math.random() * 600);
                clearTyping();
            }

            renderMessage(msg);

            if (i < messages.length - 1) {
                await sleep(400 + Math.random() * 400);
            }
        }
        const divider = document.createElement("div");
        divider.className = "feed-divider";
        divider.innerHTML = "<span>Demo complete \u2014 try sending a real message below</span>";
        messageFeed.appendChild(divider);
        messageFeed.scrollTop = messageFeed.scrollHeight;
    } catch (e) {
        console.error("Failed to load demo:", e);
    }

    demoRunning = false;
    if (demoBtn) {
        demoBtn.disabled = false;
        demoBtn.innerHTML = "&#9654; Watch Demo";
    }
};

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function sendUserMessage() {
    const text = messageInput.value.trim();
    if (!text) return;

    renderMessage({
        agent_id: "user",
        agent_name: "You",
        avatar: "\uD83D\uDC64",
        color: "#94a3b8",
        role: "User",
        content: escapeHtml(text),
        tool_use: [],
        is_user: true,
        _escaped: true,
        _queued: processing,
    });

    messageInput.value = "";
    messageInput.style.height = "auto";

    if (processing) {
        messageQueue.push({ text, channelId: activeChannelId });
        updateQueueBadge();
    } else {
        startLiveChat(text);
    }
}

function startLiveChat(message) {
    setProcessing(true);
    pendingToolCards = {};
    pendingDocuments = {};

    fetch(BASE_PATH + "/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, channel_id: activeChannelId }),
    }).then((response) => {
        if (!response.ok) {
            throw new Error("Chat request failed: " + response.status);
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        function processStream() {
            reader.read().then(({ done, value }) => {
                if (done) {
                    setProcessing(false);
                    loadSchedules();
                    return;
                }

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop();

                let eventType = null;
                for (const line of lines) {
                    if (line.startsWith("event: ")) {
                        eventType = line.slice(7).trim();
                    } else if (line.startsWith("data: ") && eventType) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            handleSSEEvent(eventType, data);
                        } catch (e) {
                            console.error("SSE parse error:", e);
                        }
                        eventType = null;
                    }
                }

                processStream();
            }).catch((e) => {
                console.error("Stream read error:", e);
                setProcessing(false);
            });
        }

        processStream();
    }).catch((e) => {
        console.error("Chat error:", e);
        setProcessing(false);
    });
}

function handleSSEEvent(type, data) {
    switch (type) {
        case "typing": {
            showTyping(data);
            break;
        }

        case "typing_clear": {
            clearTyping();
            break;
        }

        case "tool_use": {
            const agentData = allAgents[data.agent_id] || { name: data.agent_id, avatar: "\uD83E\uDD16", color: "#666" };
            showToolActivity(agentData, data.tool);

            if (!pendingToolCards[data.agent_id]) {
                pendingToolCards[data.agent_id] = [];
            }
            pendingToolCards[data.agent_id].push({
                tool: data.tool,
                input: data.input || "",
                result: "",
            });
            break;
        }

        case "tool_result": {
            const cards = pendingToolCards[data.agent_id];
            if (cards && cards.length > 0) {
                const last = cards[cards.length - 1];
                if (last.tool === data.tool) {
                    last.result = data.result || "";
                }
            }
            break;
        }

        case "document": {
            if (!pendingDocuments[data.agent_id]) {
                pendingDocuments[data.agent_id] = [];
            }
            pendingDocuments[data.agent_id].push(data);
            break;
        }

        case "message": {
            clearTyping();
            const toolCards = pendingToolCards[data.agent_id] || [];
            pendingToolCards[data.agent_id] = [];
            const docs = pendingDocuments[data.agent_id] || data.documents || [];
            pendingDocuments[data.agent_id] = [];

            renderMessage({
                agent_id: data.agent_id,
                agent_name: data.agent_name,
                avatar: data.avatar,
                color: data.color,
                role: data.role,
                content: data.content,
                tool_use: toolCards,
                documents: docs,
                mentions: data.mentions || [],
                is_user: false,
            });
            break;
        }

        case "agent_error": {
            clearTyping();
            const errAgent = allAgents[data.agent_id] || { name: "System", avatar: "\u26A0\uFE0F", color: "#ef4444" };
            renderMessage({
                agent_id: data.agent_id,
                agent_name: errAgent.name || "System",
                avatar: errAgent.avatar || "\u26A0\uFE0F",
                color: errAgent.color || "#ef4444",
                role: "Error",
                content: `**Error:** ${data.message}`,
                tool_use: [],
                is_user: false,
            });
            break;
        }

        case "agent_status": {
            break;
        }

        case "done": {
            setProcessing(false);
            loadSchedules();
            break;
        }
    }
}

function openCreateModal() {
    channelNameInput.value = "";
    channelDescInput.value = "";
    agentCheckboxes.innerHTML = availableAgents
        .map(
            (a) => `
        <label class="agent-checkbox${a.is_core ? " core" : ""}">
            <input type="checkbox" value="${a.id}" ${a.is_core ? "checked disabled" : "checked"}>
            <span class="agent-cb-avatar" style="background:${a.color}">${a.avatar}</span>
            <span class="agent-cb-name">${escapeHtml(a.name)}</span>
            <span class="agent-cb-role">${escapeHtml(a.role)}</span>
        </label>`
        )
        .join("");
    createModal.style.display = "flex";
    channelNameInput.focus();
}

function closeCreateModal() {
    createModal.style.display = "none";
}

async function createChannel() {
    const name = channelNameInput.value.trim();
    if (!name) return;
    const description = channelDescInput.value.trim();
    const checked = agentCheckboxes.querySelectorAll("input:checked");
    const agentIds = Array.from(checked).map((cb) => cb.value);

    try {
        const r = await fetch(BASE_PATH + "/api/channels", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, description, agent_ids: agentIds }),
        });
        const data = await r.json();
        closeCreateModal();
        await loadChannels();
        if (data.channel) {
            if (processing) {
                pendingChannelSwitch = data.channel.id;
            } else {
                await switchChannel(data.channel.id);
            }
        }
    } catch (e) {
        console.error("Failed to create channel:", e);
    }
}

addChannelBtn.addEventListener("click", openCreateModal);
modalClose.addEventListener("click", closeCreateModal);
modalCancel.addEventListener("click", closeCreateModal);
modalCreate.addEventListener("click", createChannel);
channelNameInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") createChannel();
});
createModal.addEventListener("click", (e) => {
    if (e.target === createModal) closeCreateModal();
});

sendBtn.addEventListener("click", () => {
    if (processing && !messageInput.value.trim()) {
        stopProcessing();
    } else {
        sendUserMessage();
    }
});
messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendUserMessage();
    }
});

messageInput.addEventListener("input", () => {
    messageInput.style.height = "auto";
    messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + "px";
});

sidebarToggle.addEventListener("click", () => {
    sidebar.classList.toggle("open");
});

document.addEventListener("click", (e) => {
    if (
        window.innerWidth <= 768 &&
        sidebar.classList.contains("open") &&
        !sidebar.contains(e.target) &&
        e.target !== sidebarToggle
    ) {
        sidebar.classList.remove("open");
    }
});

schedulesToggle.addEventListener("click", () => {
    schedulesList.classList.toggle("collapsed");
});

const profilePanel = document.getElementById("profile-panel");
const profileOverlay = document.getElementById("profile-overlay");
const profileClose = document.getElementById("profile-close");
const profilePanelBody = document.getElementById("profile-panel-body");

function openProfilePanel(agentId) {
    fetch(BASE_PATH + "/api/agents/" + encodeURIComponent(agentId))
        .then((r) => r.json())
        .then((data) => {
            if (data.error) return;
            const a = data.agent;
            const badgeClass = a.is_core ? "core" : "custom";
            const badgeText = a.is_core ? "Core Agent" : "Custom";

            const toolsHtml = a.tools && a.tools.length > 0
                ? a.tools.map((t) => `<span class="profile-tool-tag">${escapeHtml(t)}</span>`).join("")
                : '<span class="profile-no-items">No tools</span>';

            const skillsHtml = a.skills && a.skills.length > 0
                ? a.skills.map((s) => `<span class="profile-skill-tag">${escapeHtml(s)}</span>`).join("")
                : '<span class="profile-no-items">No skills loaded</span>';

            const actionsHtml = a.is_custom ? `
                <div class="profile-actions">
                    <button class="profile-btn profile-btn-edit" onclick="openAgentModal('${escapeHtml(a.id)}')">Edit</button>
                    <button class="profile-btn profile-btn-delete" onclick="deleteAgent('${escapeHtml(a.id)}')">Delete</button>
                </div>` : "";

            profilePanelBody.innerHTML = `
                <div class="profile-hero">
                    <div class="profile-avatar" style="background:${a.color}">${a.avatar}</div>
                    <div class="profile-name">${escapeHtml(a.name)}</div>
                    <div class="profile-role">${escapeHtml(a.role)}</div>
                    <span class="profile-badge ${badgeClass}">${badgeText}</span>
                    ${actionsHtml}
                </div>
                <p class="profile-description">${escapeHtml(a.description)}</p>
                <div class="profile-section">
                    <div class="profile-section-title">Tools</div>
                    <div class="profile-tools-list">${toolsHtml}</div>
                </div>
                <div class="profile-section">
                    <div class="profile-section-title">Skills</div>
                    <div class="profile-skills-list">${skillsHtml}</div>
                </div>
                <div class="profile-section">
                    <div class="profile-section-title">System Prompt</div>
                    <button class="profile-system-toggle" onclick="toggleSystemPrompt(this)">
                        <span class="toggle-arrow">&#9660;</span>
                        <span>Show system prompt</span>
                    </button>
                    <div class="profile-system-content">${escapeHtml(a.system || "No system prompt defined.")}</div>
                </div>
            `;

            profilePanel.classList.add("open");
            profileOverlay.classList.add("open");
        })
        .catch((e) => console.error("Failed to load agent profile:", e));
}

function closeProfilePanel() {
    profilePanel.classList.remove("open");
    profileOverlay.classList.remove("open");
}

window.toggleSystemPrompt = function (btn) {
    const content = btn.nextElementSibling;
    const arrow = btn.querySelector(".toggle-arrow");
    content.classList.toggle("open");
    arrow.classList.toggle("open");
    btn.querySelector("span:last-child").textContent =
        content.classList.contains("open") ? "Hide system prompt" : "Show system prompt";
};

profileClose.addEventListener("click", closeProfilePanel);
profileOverlay.addEventListener("click", closeProfilePanel);

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && profilePanel.classList.contains("open")) {
        closeProfilePanel();
    }
});

agentListEl.addEventListener("click", (e) => {
    const agentItem = e.target.closest(".agent-item");
    if (agentItem) {
        const agentId = agentItem.dataset.agent;
        if (agentId) openProfilePanel(agentId);
    }
});

const createAgentModal = document.getElementById("create-agent-modal");
const agentModalTitle = document.getElementById("agent-modal-title");
const agentModalClose = document.getElementById("agent-modal-close");
const agentModalCancel = document.getElementById("agent-modal-cancel");
const agentModalSave = document.getElementById("agent-modal-save");
const agentNameInput = document.getElementById("agent-name-input");
const agentRoleInput = document.getElementById("agent-role-input");
const agentDescInput = document.getElementById("agent-desc-input");
const agentAvatarInput = document.getElementById("agent-avatar-input");
const avatarPreview = document.getElementById("avatar-preview");
const agentColorInput = document.getElementById("agent-color-input");
const colorSwatches = document.getElementById("color-swatches");
const agentToolsCheckboxes = document.getElementById("agent-tools-checkboxes");
const agentSkillsCheckboxes = document.getElementById("agent-skills-checkboxes");
const agentSystemInput = document.getElementById("agent-system-input");
const createAgentBtn = document.getElementById("create-agent-btn");

let editingAgentId = null;
let cachedTools = null;
let cachedSkills = null;

async function loadToolsAndSkills() {
    if (!cachedTools) {
        try {
            const r = await fetch(BASE_PATH + "/api/tools");
            const data = await r.json();
            cachedTools = data.tools || [];
        } catch (e) {
            cachedTools = [];
        }
    }
    if (!cachedSkills) {
        try {
            const r = await fetch(BASE_PATH + "/api/skills");
            const data = await r.json();
            cachedSkills = data.skills || [];
        } catch (e) {
            cachedSkills = [];
        }
    }
}

function renderToolCheckboxes(selectedTools) {
    const selected = new Set(selectedTools || []);
    let html = "";
    let lastCategory = "";
    for (const tool of cachedTools) {
        if (tool.category !== lastCategory) {
            lastCategory = tool.category;
            html += `<div class="agent-tool-category">${escapeHtml(tool.category)}</div>`;
        }
        html += `
        <label class="agent-tool-checkbox">
            <input type="checkbox" value="${escapeHtml(tool.name)}" ${selected.has(tool.name) ? "checked" : ""}>
            <span class="agent-tool-name">${escapeHtml(tool.name)}</span>
        </label>`;
    }
    agentToolsCheckboxes.innerHTML = html;
}

function renderSkillCheckboxes(selectedSkills) {
    const selected = new Set(selectedSkills || []);
    if (!cachedSkills || cachedSkills.length === 0) {
        agentSkillsCheckboxes.innerHTML = '<span class="no-skills-msg">No skills available</span>';
        return;
    }
    agentSkillsCheckboxes.innerHTML = cachedSkills.map(s => `
        <label class="agent-skill-checkbox">
            <input type="checkbox" value="${escapeHtml(s.name)}" ${selected.has(s.name) ? "checked" : ""}>
            <span class="agent-skill-name">${escapeHtml(s.display_name || s.name)}</span>
            ${s.description ? `<span class="agent-skill-desc">${escapeHtml(s.description)}</span>` : ""}
        </label>
    `).join("");
}

function setSelectedColor(color) {
    agentColorInput.value = color;
    avatarPreview.style.background = color;
    colorSwatches.querySelectorAll(".color-swatch").forEach(sw => {
        sw.classList.toggle("active", sw.dataset.color === color);
    });
}

function generateSystemPrompt(name, role) {
    return `You are ${name}, a ${role} agent in a multi-agent team called SynthChat.\n\nRULES:\n1. Be concise and helpful.\n2. Use your tools effectively.\n3. Collaborate with other agents when needed.`;
}

window.openAgentModal = async function openAgentModal(agentId) {
    await loadToolsAndSkills();
    editingAgentId = agentId || null;

    if (editingAgentId) {
        agentModalTitle.textContent = "Edit Agent";
        agentModalSave.textContent = "Save Changes";
        try {
            const r = await fetch(BASE_PATH + "/api/agents/" + encodeURIComponent(editingAgentId));
            const data = await r.json();
            if (data.error) return;
            const a = data.agent;
            agentNameInput.value = a.name;
            agentRoleInput.value = a.role;
            agentDescInput.value = a.description || "";
            agentAvatarInput.value = a.avatar;
            avatarPreview.textContent = a.avatar;
            setSelectedColor(a.color);
            renderToolCheckboxes(a.tools);
            renderSkillCheckboxes(a.skills);
            agentSystemInput.value = a.system || "";
        } catch (e) {
            console.error("Failed to load agent for editing:", e);
            return;
        }
    } else {
        agentModalTitle.textContent = "Create Agent";
        agentModalSave.textContent = "Create Agent";
        agentNameInput.value = "";
        agentRoleInput.value = "";
        agentDescInput.value = "";
        agentAvatarInput.value = "";
        avatarPreview.textContent = "\uD83E\uDD16";
        setSelectedColor("#4ade80");
        renderToolCheckboxes([]);
        renderSkillCheckboxes([]);
        agentSystemInput.value = "";
    }

    createAgentModal.style.display = "flex";
    agentNameInput.focus();
}

function closeAgentModal() {
    createAgentModal.style.display = "none";
    editingAgentId = null;
}

async function saveAgent() {
    const name = agentNameInput.value.trim();
    const role = agentRoleInput.value.trim();
    const system = agentSystemInput.value.trim();

    if (!name) { agentNameInput.focus(); return; }
    if (!role) { agentRoleInput.focus(); return; }
    if (!system) {
        const gen = generateSystemPrompt(name, role);
        agentSystemInput.value = gen;
        agentSystemInput.focus();
        return;
    }

    const toolChecks = agentToolsCheckboxes.querySelectorAll("input:checked");
    const tools = Array.from(toolChecks).map(cb => cb.value);
    const skillChecks = agentSkillsCheckboxes.querySelectorAll("input:checked");
    const skills = Array.from(skillChecks).map(cb => cb.value);

    const body = {
        name,
        role,
        avatar: agentAvatarInput.value.trim() || "\uD83E\uDD16",
        color: agentColorInput.value.trim() || "#6b7280",
        description: agentDescInput.value.trim(),
        tools,
        skills,
        system,
    };

    try {
        let url, method;
        if (editingAgentId) {
            url = BASE_PATH + "/api/agents/" + encodeURIComponent(editingAgentId);
            method = "PUT";
        } else {
            url = BASE_PATH + "/api/agents";
            method = "POST";
        }
        const r = await fetch(url, {
            method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        const data = await r.json();
        if (!r.ok) {
            alert(data.error || "Failed to save agent");
            return;
        }
        closeAgentModal();
        await loadAgents();
        renderAgentList(null);
    } catch (e) {
        console.error("Failed to save agent:", e);
        alert("Failed to save agent");
    }
}

window.deleteAgent = async function deleteAgent(agentId) {
    if (!confirm("Delete this agent? This cannot be undone.")) return;
    try {
        const r = await fetch(BASE_PATH + "/api/agents/" + encodeURIComponent(agentId), {
            method: "DELETE",
        });
        const data = await r.json();
        if (!r.ok) {
            alert(data.error || "Failed to delete agent");
            return;
        }
        closeProfilePanel();
        await loadAgents();
        renderAgentList(null);
    } catch (e) {
        console.error("Failed to delete agent:", e);
    }
}

agentAvatarInput.addEventListener("input", () => {
    const val = agentAvatarInput.value.trim();
    avatarPreview.textContent = val || "\uD83E\uDD16";
});

colorSwatches.addEventListener("click", (e) => {
    const swatch = e.target.closest(".color-swatch");
    if (swatch) {
        e.preventDefault();
        setSelectedColor(swatch.dataset.color);
    }
});

agentColorInput.addEventListener("input", () => {
    const val = agentColorInput.value.trim();
    if (/^#[0-9a-fA-F]{6}$/.test(val)) {
        avatarPreview.style.background = val;
        colorSwatches.querySelectorAll(".color-swatch").forEach(sw => {
            sw.classList.toggle("active", sw.dataset.color === val);
        });
    }
});

agentNameInput.addEventListener("input", () => {
    if (!editingAgentId && !agentSystemInput.value.trim()) {
        const name = agentNameInput.value.trim();
        const role = agentRoleInput.value.trim();
        if (name && role) {
            agentSystemInput.value = generateSystemPrompt(name, role);
        }
    }
});

agentRoleInput.addEventListener("input", () => {
    if (!editingAgentId && !agentSystemInput.dataset.userEdited) {
        const name = agentNameInput.value.trim();
        const role = agentRoleInput.value.trim();
        if (name && role) {
            agentSystemInput.value = generateSystemPrompt(name, role);
        }
    }
});

agentSystemInput.addEventListener("input", () => {
    agentSystemInput.dataset.userEdited = "true";
});

createAgentBtn.addEventListener("click", () => openAgentModal(null));
agentModalClose.addEventListener("click", closeAgentModal);
agentModalCancel.addEventListener("click", closeAgentModal);
agentModalSave.addEventListener("click", saveAgent);
createAgentModal.addEventListener("click", (e) => {
    if (e.target === createAgentModal) closeAgentModal();
});

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && createAgentModal.style.display === "flex") {
        closeAgentModal();
    }
});

const libraryBtn = document.getElementById("library-btn");
const libraryModal = document.getElementById("library-modal");
const libraryClose = document.getElementById("library-close");
const libraryBody = document.getElementById("library-body");

function openLibrary() {
    libraryModal.style.display = "flex";
    switchLibraryTab("my-agents");
}

function closeLibrary() {
    libraryModal.style.display = "none";
}

function switchLibraryTab(tabName) {
    document.querySelectorAll(".library-tab").forEach(t => t.classList.toggle("active", t.dataset.tab === tabName));
    document.querySelectorAll(".library-tab-content").forEach(c => c.classList.toggle("active", c.id === `tab-${tabName}`));

    if (tabName === "my-agents") loadMyAgentsTab();
    else if (tabName === "community") loadCommunityTab();
    else if (tabName === "skills") loadSkillsTab();
}

async function loadMyAgentsTab() {
    const container = document.getElementById("tab-my-agents");
    try {
        const res = await fetch(`${BASE_PATH}/api/agents`);
        const data = await res.json();
        const agents = data.agents || [];

        let html = `<div class="library-section-header"><h3>${agents.length} Agent${agents.length !== 1 ? 's' : ''}</h3><button class="library-create-btn" onclick="closeLibrary(); openAgentModal(null);">+ Create Agent</button></div>`;
        html += '<div class="library-grid">';

        for (const a of agents) {
            const badge = a.is_builtin ? '<span class="library-card-badge badge-builtin">Built-in</span>' : '<span class="library-card-badge badge-custom">Custom</span>';
            const toolCount = a.tools ? a.tools.length : 0;

            let actions = '';
            if (a.is_custom) {
                actions = `
                    <button class="library-card-btn btn-edit" onclick="closeLibrary(); openAgentModal('${a.id}');">Edit</button>
                    <button class="library-card-btn btn-publish" onclick="publishAgent('${a.id}')" id="publish-${a.id}">Publish</button>
                    <button class="library-card-btn btn-delete" onclick="libraryDeleteAgent('${a.id}')">Delete</button>`;
            } else {
                actions = `<button class="library-card-btn btn-installed" disabled>Core Agent</button>`;
            }

            html += `
                <div class="library-card">
                    <div class="library-card-header">
                        <div class="library-card-avatar" style="background:${a.color}20">${a.avatar}</div>
                        <div class="library-card-info">
                            <p class="library-card-name">${a.name}</p>
                            <p class="library-card-role">${a.role}</p>
                        </div>
                    </div>
                    <p class="library-card-desc">${a.description || 'No description'}</p>
                    <div class="library-card-meta">${badge}<span class="library-card-badge badge-tools">${toolCount} tools</span></div>
                    <div class="library-card-actions">${actions}</div>
                </div>`;
        }
        html += '</div>';
        container.innerHTML = html;

        checkPublishStatus(agents.filter(a => a.is_custom));
    } catch (err) {
        container.innerHTML = '<div class="library-empty"><p>Failed to load agents</p></div>';
    }
}

async function checkPublishStatus(customAgents) {
    try {
        const res = await fetch(`${BASE_PATH}/api/community/agents`);
        const data = await res.json();
        const communityIds = new Set((data.agents || []).map(a => a.id));
        for (const a of customAgents) {
            const btn = document.getElementById(`publish-${a.id}`);
            if (btn && communityIds.has(a.id)) {
                btn.textContent = "Published";
                btn.className = "library-card-btn btn-published";
                btn.disabled = true;
            }
        }
    } catch (e) {}
}

async function loadCommunityTab() {
    const container = document.getElementById("tab-community");
    try {
        const res = await fetch(`${BASE_PATH}/api/community/agents`);
        const data = await res.json();
        const agents = data.agents || [];

        if (agents.length === 0) {
            container.innerHTML = '<div class="library-empty"><p>No community agents yet.</p><p>Create an agent and click Publish to share it!</p></div>';
            return;
        }

        let html = `<div class="library-section-header"><h3>${agents.length} Community Agent${agents.length !== 1 ? 's' : ''}</h3></div>`;
        html += '<div class="library-grid">';

        for (const a of agents) {
            const toolCount = a.tools ? a.tools.length : 0;
            const installBtn = a.installed
                ? `<button class="library-card-btn btn-installed" disabled>Installed</button>`
                : `<button class="library-card-btn btn-install" onclick="installAgent('${a.id}')">+ Add to Library</button>`;

            html += `
                <div class="library-card" id="community-card-${a.id}">
                    <div class="library-card-header">
                        <div class="library-card-avatar" style="background:${a.color}20">${a.avatar}</div>
                        <div class="library-card-info">
                            <p class="library-card-name">${a.name}</p>
                            <p class="library-card-role">${a.role}</p>
                        </div>
                    </div>
                    <p class="library-card-desc">${a.description || 'No description'}</p>
                    <div class="library-card-meta"><span class="library-card-badge badge-tools">${toolCount} tools</span></div>
                    <div class="library-card-actions">${installBtn}</div>
                </div>`;
        }
        html += '</div>';
        container.innerHTML = html;
    } catch (err) {
        container.innerHTML = '<div class="library-empty"><p>Failed to load community agents</p></div>';
    }
}

async function loadSkillsTab() {
    const container = document.getElementById("tab-skills");
    try {
        const res = await fetch(`${BASE_PATH}/api/skills`);
        const data = await res.json();
        const skills = data.skills || [];

        if (skills.length === 0) {
            container.innerHTML = '<div class="library-empty"><p>No skills available yet.</p><p>Add SKILL.md files to ~/.octobot/skills/ to create skills.</p></div>';
            return;
        }

        let html = `<div class="library-section-header"><h3>${skills.length} Skill${skills.length !== 1 ? 's' : ''}</h3></div>`;
        for (const s of skills) {
            html += `
                <div class="skill-card">
                    <p class="skill-card-name">${s.display_name || s.name}</p>
                    <p class="skill-card-desc">${s.description || 'No description available'}</p>
                </div>`;
        }
        container.innerHTML = html;
    } catch (err) {
        container.innerHTML = '<div class="library-empty"><p>Failed to load skills</p></div>';
    }
}

async function installAgent(agentId) {
    try {
        const res = await fetch(`${BASE_PATH}/api/agents/install`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ agent_id: agentId }),
        });
        const data = await res.json();
        if (res.ok) {
            await loadAgents();
            loadCommunityTab();
        } else {
            alert(data.error || "Failed to install agent");
        }
    } catch (err) {
        alert("Failed to install agent");
    }
}

async function publishAgent(agentId) {
    try {
        const res = await fetch(`${BASE_PATH}/api/agents/${agentId}/publish`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
        });
        const data = await res.json();
        if (res.ok) {
            const btn = document.getElementById(`publish-${agentId}`);
            if (btn) {
                btn.textContent = "Published";
                btn.className = "library-card-btn btn-published";
                btn.disabled = true;
            }
        } else {
            alert(data.error || "Failed to publish agent");
        }
    } catch (err) {
        alert("Failed to publish agent");
    }
}

async function libraryDeleteAgent(agentId) {
    if (!confirm("Delete this agent? This cannot be undone.")) return;
    try {
        const res = await fetch(`${BASE_PATH}/api/agents/${agentId}`, { method: "DELETE" });
        if (res.ok) {
            await loadAgents();
            loadMyAgentsTab();
        } else {
            const data = await res.json();
            alert(data.error || "Failed to delete agent");
        }
    } catch (err) {
        alert("Failed to delete agent");
    }
}

libraryBtn.addEventListener("click", openLibrary);
libraryClose.addEventListener("click", closeLibrary);
libraryModal.addEventListener("click", (e) => {
    if (e.target === libraryModal) closeLibrary();
});

document.querySelectorAll(".library-tab").forEach(tab => {
    tab.addEventListener("click", () => switchLibraryTab(tab.dataset.tab));
});

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && libraryModal.style.display === "flex") {
        closeLibrary();
    }
});

async function init() {
    await loadAgents();
    await loadChannels();
    await switchChannel("workspace");
    await loadSchedules();
}

init();
