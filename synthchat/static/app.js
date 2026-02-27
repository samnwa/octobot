const messageFeed = document.getElementById("message-feed");
const typingArea = document.getElementById("typing-area");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const agentListEl = document.getElementById("agent-list");
const sidebarToggle = document.getElementById("sidebar-toggle");
const sidebar = document.getElementById("sidebar");

let agents = {};
let processing = false;
let msgCounter = 0;
let pendingToolCards = {};

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
    return new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function highlightMentions(html) {
    for (const [id, agent] of Object.entries(agents)) {
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
                <span class="tool-icon">⚙️</span>
                <span class="tool-name">${escapeHtml(t.tool)}</span>
                <span class="tool-input-preview">${escapeHtml(t.input || "")}</span>
                <span class="tool-expand">▼</span>
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

    el.innerHTML = `
        <div class="msg-avatar" style="background:${msg.color}">${msg.avatar}</div>
        <div class="msg-body">
            <div class="msg-header">
                <span class="msg-name" style="color:${msg.color}">${escapeHtml(msg.agent_name)}</span>
                <span class="msg-time">${formatTime(msg.ts_offset)}</span>
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
    const avatar = agentData.avatar || "🤖";
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
    const avatar = agentData.avatar || "🤖";
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
        const r = await fetch("/api/agents");
        const data = await r.json();
        for (const a of data.agents) {
            agents[a.id] = a;
        }
        renderAgentList();
    } catch (e) {
        console.error("Failed to load agents:", e);
    }
}

function renderAgentList() {
    agentListEl.innerHTML = Object.values(agents)
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
}

async function playConversation() {
    try {
        const r = await fetch("/api/mock-conversation");
        const data = await r.json();
        const messages = data.messages;

        for (let i = 0; i < messages.length; i++) {
            const msg = messages[i];

            if (!msg.is_user) {
                const agent = agents[msg.agent_id] || {
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
        divider.innerHTML = '<span>Demo complete — try sending a message below</span>';
        messageFeed.appendChild(divider);
        messageFeed.scrollTop = messageFeed.scrollHeight;
    } catch (e) {
        console.error("Failed to load conversation:", e);
    }
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function sendUserMessage() {
    const text = messageInput.value.trim();
    if (!text || processing) return;

    renderMessage({
        agent_id: "user",
        agent_name: "You",
        avatar: "👤",
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

    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
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
            const agentData = agents[data.agent_id] || { name: data.agent_id, avatar: "🤖", color: "#666" };
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
            const errAgent = agents[data.agent_id] || { name: "System", avatar: "⚠️", color: "#ef4444" };
            renderMessage({
                agent_id: data.agent_id,
                agent_name: errAgent.name || "System",
                avatar: errAgent.avatar || "⚠️",
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
            break;
        }
    }
}

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

async function init() {
    await loadAgents();
    await playConversation();
}

init();
