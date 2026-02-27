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
let demoRunning = false;

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

function renderMessage(msg) {
    const el = document.createElement("div");
    el.className = "message" + (msg.is_user ? " user-msg" : "");
    el.id = "msg-" + msgCounter++;

    const rawHtml = msg._escaped
        ? `<p>${msg.content}</p>`
        : marked.parse(msg.content || "");
    const contentHtml = highlightMentions(rawHtml);
    const toolHtml = renderToolCards(msg.tool_use);
    const ts = msg.timestamp || msg.ts_offset;

    el.innerHTML = `
        <div class="msg-avatar" style="background:${msg.color}">${msg.avatar}</div>
        <div class="msg-body">
            <div class="msg-header">
                <span class="msg-name" style="color:${msg.color}">${escapeHtml(msg.agent_name)}</span>
                <span class="msg-time">${formatTime(ts)}</span>
            </div>
            <div class="msg-content">${contentHtml}</div>
            ${toolHtml}
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
    sendBtn.disabled = val;
    messageInput.disabled = val;
    if (val) {
        sendBtn.classList.add("processing");
    } else {
        sendBtn.classList.remove("processing");
        clearTyping();
    }
}

async function loadAgents() {
    try {
        const r = await fetch(BASE_PATH + "/api/available-agents");
        const data = await r.json();
        availableAgents = data.agents;
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
            if (chId !== activeChannelId && !processing) {
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
    if (!text || processing) return;

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
    });

    messageInput.value = "";
    messageInput.style.height = "auto";

    startLiveChat(text);
}

function startLiveChat(message) {
    setProcessing(true);
    pendingToolCards = {};

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

        case "message": {
            clearTyping();
            const toolCards = pendingToolCards[data.agent_id] || [];
            pendingToolCards[data.agent_id] = [];

            renderMessage({
                agent_id: data.agent_id,
                agent_name: data.agent_name,
                avatar: data.avatar,
                color: data.color,
                role: data.role,
                content: data.content,
                tool_use: toolCards,
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
            await switchChannel(data.channel.id);
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

sendBtn.addEventListener("click", sendUserMessage);
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

async function init() {
    await loadAgents();
    await loadChannels();
    await switchChannel("workspace");
    await loadSchedules();
}

init();
