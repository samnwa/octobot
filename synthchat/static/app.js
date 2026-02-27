const messageFeed = document.getElementById("message-feed");
const typingArea = document.getElementById("typing-area");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const agentListEl = document.getElementById("agent-list");
const sidebarToggle = document.getElementById("sidebar-toggle");
const sidebar = document.getElementById("sidebar");

let agents = {};

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
    const base = new Date();
    base.setMinutes(base.getMinutes() - 30 + index * 2);
    return base.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function highlightMentions(html, mentionIds) {
    if (!mentionIds || mentionIds.length === 0) return html;
    for (const id of mentionIds) {
        const agent = agents[id];
        if (!agent) continue;
        const regex = new RegExp(`@${agent.name}`, "g");
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
            (t, i) => `
        <div class="tool-card">
            <div class="tool-card-header" onclick="toggleTool(this)">
                <span class="tool-icon">⚙️</span>
                <span class="tool-name">${escapeHtml(t.tool)}</span>
                <span class="tool-input-preview">${escapeHtml(t.input)}</span>
                <span class="tool-expand">▼</span>
            </div>
            <div class="tool-card-body">${escapeHtml(t.result)}</div>
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

    const rawHtml = msg._escaped ? `<p>${msg.content}</p>` : marked.parse(msg.content || "");
    const contentHtml = highlightMentions(rawHtml, msg.mentions);
    const toolHtml = renderToolCards(msg.tool_use);

    el.innerHTML = `
        <div class="msg-avatar" style="background:${msg.color}">${msg.avatar}</div>
        <div class="msg-body">
            <div class="msg-header">
                <span class="msg-name" style="color:${msg.color}">${escapeHtml(msg.agent_name)}</span>
                <span class="msg-time">${formatTime(msg.ts_offset)}</span>
            </div>
            ${toolHtml ? '<div class="msg-content">' + contentHtml + "</div>" + toolHtml : '<div class="msg-content">' + contentHtml + "</div>"}
        </div>
    `;

    messageFeed.appendChild(el);
    messageFeed.scrollTop = messageFeed.scrollHeight;
    return el;
}

function showTyping(agent) {
    typingArea.innerHTML = `
        <div class="typing-indicator">
            <div class="typing-avatar" style="background:${agent.color}">${agent.avatar}</div>
            <span class="typing-text">
                <strong>${escapeHtml(agent.name)}</strong> is typing
                <span class="typing-dots"><span></span><span></span><span></span></span>
            </span>
        </div>
    `;
}

function clearTyping() {
    typingArea.innerHTML = "";
}

async function loadAgents() {
    try {
        const r = await fetch("/api/agents");
        const data = await r.json();
        for (const a of data.agents) {
            agents[a.id] = a;
        }
        agentListEl.innerHTML = data.agents
            .map(
                (a) => `
            <div class="agent-item">
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
    } catch (e) {
        console.error("Failed to load agents:", e);
    }
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
    } catch (e) {
        console.error("Failed to load conversation:", e);
    }
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
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

function sendUserMessage() {
    const text = messageInput.value.trim();
    if (!text) return;
    renderMessage({
        id: "msg-user-live",
        agent_id: "user",
        agent_name: "You",
        avatar: "👤",
        color: "#94a3b8",
        role: "User",
        content: escapeHtml(text),
        tool_use: [],
        mentions: [],
        is_user: true,
        ts_offset: 99,
        _escaped: true,
    });
    messageInput.value = "";
    messageInput.style.height = "auto";
}

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
