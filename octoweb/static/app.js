const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const resetBtn = document.getElementById("reset-btn");
const tokenDisplay = document.getElementById("token-display");
const swimmer = document.getElementById("swimming-octopus");
const filesBtn = document.getElementById("files-btn");
const filePanel = document.getElementById("file-panel");
const panelClose = document.getElementById("panel-close");
const hideCore = document.getElementById("hide-core");
const refreshFiles = document.getElementById("refresh-files");
const fileTree = document.getElementById("file-tree");
const fileViewer = document.getElementById("file-viewer");
const viewerPath = document.getElementById("viewer-path");
const viewerContent = document.getElementById("viewer-content");
const viewerClose = document.getElementById("viewer-close");
const cmdBtn = document.getElementById("cmd-btn");
const cmdDropdown = document.getElementById("cmd-dropdown");
const cmdAutocomplete = document.getElementById("cmd-autocomplete");
const modelTrigger = document.getElementById("model-trigger");
const modelDropdown = document.getElementById("model-dropdown");
const modelList = document.getElementById("model-list");
const currentModelEl = document.getElementById("current-model");
const statusBar = document.getElementById("status-bar");
const statusText = document.getElementById("status-text");
const viewerToggle = document.getElementById("viewer-toggle");
const togglePreview = document.getElementById("toggle-preview");
const toggleCode = document.getElementById("toggle-code");
const viewerPreview = document.getElementById("viewer-preview");

let commands = [];
let modelsCache = null;
let currentFileContent = "";
let currentFileExt = "";

marked.setOptions({
    highlight: function (code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            return hljs.highlight(code, { language: lang }).value;
        }
        return hljs.highlightAuto(code).value;
    },
    breaks: true,
});

let isProcessing = false;
let currentReader = null;

sendBtn.addEventListener("click", async (e) => {
    if (isProcessing) {
        e.preventDefault();
        await fetch("/stop", { method: "POST" });
        if (currentReader) {
            try { await currentReader.cancel(); } catch(_) {}
            currentReader = null;
        }
        setProcessing(false);
        return;
    }
});

chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = messageInput.value.trim();
    if (!message || isProcessing) return;

    hideCmdAutocomplete();
    messageInput.value = "";

    if (message === "/history") {
        addUserMessage(message);
        await showHistory();
        return;
    }

    if (message.startsWith("/history ")) {
        addUserMessage(message);
        const num = parseInt(message.split(" ")[1]);
        await loadHistorySession(num);
        return;
    }

    addUserMessage(message);
    setProcessing(true);

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message }),
        });

        const reader = response.body.getReader();
        currentReader = reader;
        const decoder = new TextDecoder();
        let buffer = "";
        let currentAssistantEl = null;
        let currentText = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop();

            let eventType = null;
            for (const line of lines) {
                if (line.startsWith("event: ")) {
                    eventType = line.slice(7);
                } else if (line.startsWith("data: ") && eventType) {
                    const data = JSON.parse(line.slice(6));

                    switch (eventType) {
                        case "text":
                            if (!currentAssistantEl) {
                                currentAssistantEl = addAssistantMessage("");
                                currentText = "";
                            }
                            currentText += data.content;
                            currentAssistantEl.innerHTML = marked.parse(currentText);
                            setStatus("Responding...");
                            break;
                        case "thinking":
                            if (data.text && data.text !== "Thinking...") {
                                addThinking(data.text);
                                const preview = data.text.length > 60 ? data.text.slice(0, 60) + "..." : data.text;
                                setStatus("Thinking: " + preview);
                            } else {
                                setStatus("Thinking...");
                            }
                            break;
                        case "tool_use":
                            addToolUse(data.name, data.input);
                            setStatus("Running: " + data.name);
                            break;
                        case "tool_result":
                            addToolResult(data.name, data.result);
                            setStatus("Done: " + data.name);
                            break;
                        case "tokens":
                            tokenDisplay.textContent =
                                `${data.input.toLocaleString()} in / ${data.output.toLocaleString()} out`;
                            break;
                        case "file_written":
                            onFileWritten(data.path);
                            break;
                        case "error":
                            addError(data.message);
                            break;
                        case "done":
                            break;
                    }
                    eventType = null;
                    scrollToBottom();
                }
            }
        }
    } catch (err) {
        if (err.name !== "AbortError" && err.message !== "Released reader") {
            addError("Connection error: " + err.message);
        }
    }

    currentReader = null;
    setProcessing(false);
});

resetBtn.addEventListener("click", async () => {
    await fetch("/reset", { method: "POST" });
    messagesEl.innerHTML = `<div class="welcome-message"><p>Conversation reset. Ask me anything.</p></div>`;
    tokenDisplay.textContent = "";
});

function setProcessing(val) {
    isProcessing = val;
    sendBtn.disabled = false;
    messageInput.disabled = false;
    swimmer.classList.toggle("hidden", !val);
    if (val) {
        sendBtn.textContent = "Stop";
        sendBtn.type = "button";
        sendBtn.classList.add("stop-mode");
        setStatus("Thinking...");
    } else {
        sendBtn.textContent = "Send";
        sendBtn.type = "submit";
        sendBtn.classList.remove("stop-mode");
        statusBar.classList.add("hidden");
        messageInput.focus();
    }
}

function setStatus(text) {
    statusText.textContent = text;
    statusBar.classList.remove("hidden");
}

function addUserMessage(text) {
    clearWelcome();
    const div = document.createElement("div");
    div.className = "message message-user";
    div.innerHTML = `<div class="message-bubble">${escapeHtml(text)}</div>`;
    messagesEl.appendChild(div);
    scrollToBottom();
}

function addAssistantMessage(html) {
    clearWelcome();
    const div = document.createElement("div");
    div.className = "message message-assistant";
    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.innerHTML = html;
    div.appendChild(bubble);
    messagesEl.appendChild(div);
    scrollToBottom();
    return bubble;
}

function addThinking(text) {
    clearWelcome();
    let preview = text;
    if (preview.length > 200) preview = preview.slice(0, 200) + "...";
    const div = document.createElement("div");
    div.className = "thinking-text";
    div.textContent = preview;
    messagesEl.appendChild(div);
    scrollToBottom();
}

function addToolUse(name, input) {
    clearWelcome();
    const panel = document.createElement("div");
    panel.className = "tool-panel";
    panel.innerHTML = `
        <div class="tool-header" onclick="toggleTool(this)">
            <span class="tool-name">Tool: ${escapeHtml(name)}</span>
            <span class="toggle-icon">&#9654;</span>
        </div>
        <div class="tool-body">${escapeHtml(input)}</div>
    `;
    messagesEl.appendChild(panel);
    scrollToBottom();
}

function addToolResult(name, result) {
    const panel = document.createElement("div");
    panel.className = "tool-panel tool-result-panel";
    panel.innerHTML = `
        <div class="tool-header" onclick="toggleTool(this)">
            <span class="tool-name">Result: ${escapeHtml(name)}</span>
            <span class="toggle-icon">&#9654;</span>
        </div>
        <div class="tool-body">${escapeHtml(result)}</div>
    `;
    messagesEl.appendChild(panel);
    scrollToBottom();
}

function addError(message) {
    const div = document.createElement("div");
    div.className = "message message-assistant";
    div.innerHTML = `<div class="message-bubble" style="border-color: #f8514933; color: #f85149;">${escapeHtml(message)}</div>`;
    messagesEl.appendChild(div);
    scrollToBottom();
}

function toggleTool(header) {
    const body = header.nextElementSibling;
    const icon = header.querySelector(".toggle-icon");
    body.classList.toggle("open");
    icon.classList.toggle("open");
}

function clearWelcome() {
    const welcome = messagesEl.querySelector(".welcome-message");
    if (welcome) welcome.remove();
}

function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

filesBtn.addEventListener("click", () => {
    const isHidden = filePanel.classList.contains("hidden");
    filePanel.classList.toggle("hidden", !isHidden);
    filesBtn.classList.toggle("active", isHidden);
    if (isHidden) loadFiles();
});

panelClose.addEventListener("click", () => {
    filePanel.classList.add("hidden");
    filesBtn.classList.remove("active");
});

hideCore.addEventListener("change", loadFiles);
refreshFiles.addEventListener("click", loadFiles);

async function loadFiles() {
    const hide = hideCore.checked;
    fileTree.innerHTML = '<div style="padding:12px;color:var(--text-secondary);">Loading...</div>';
    try {
        const r = await fetch(`/api/files?hide_core=${hide}`);
        const data = await r.json();
        fileTree.innerHTML = "";
        renderTree(data.files, fileTree, 0);
    } catch (e) {
        fileTree.innerHTML = `<div style="padding:12px;color:var(--accent-red);">Error loading files</div>`;
    }
}

function renderTree(items, parent, depth) {
    for (const item of items) {
        const el = document.createElement("div");

        if (item.type === "dir") {
            const row = document.createElement("div");
            row.className = "tree-item" + (item.touched ? " touched" : "");
            row.style.paddingLeft = (8 + depth * 16) + "px";
            row.innerHTML = `<span class="tree-icon dir-icon">&#9654;</span><span class="tree-name">${escapeHtml(item.name)}</span>`;

            const children = document.createElement("div");
            children.className = "tree-children";
            renderTree(item.children || [], children, depth + 1);

            row.addEventListener("click", () => {
                children.classList.toggle("open");
                const icon = row.querySelector(".tree-icon");
                icon.innerHTML = children.classList.contains("open") ? "&#9660;" : "&#9654;";
            });

            el.appendChild(row);
            el.appendChild(children);
        } else {
            const row = document.createElement("div");
            row.className = "tree-item" + (item.touched ? " touched" : "");
            row.style.paddingLeft = (8 + depth * 16) + "px";

            const ext = item.name.split(".").pop();
            row.innerHTML = `<span class="tree-icon file-icon">${fileIcon(ext)}</span><span class="tree-name">${escapeHtml(item.name)}</span>`;

            row.addEventListener("click", () => openFile(item.path));
            el.appendChild(row);
        }

        parent.appendChild(el);
    }
}

function fileIcon(ext) {
    const icons = {
        py: "&#128013;",
        js: "JS",
        ts: "TS",
        json: "{}",
        md: "#",
        html: "&lt;&gt;",
        css: "*",
        txt: "T",
        yml: "Y",
        yaml: "Y",
        toml: "T",
        cfg: "C",
        sh: "$",
    };
    return icons[ext] || "&#9679;";
}

async function openFile(path) {
    try {
        const r = await fetch(`/api/file?path=${encodeURIComponent(path)}`);
        const data = await r.json();
        if (data.error) {
            alert(data.error);
            return;
        }
        viewerPath.textContent = data.path;
        currentFileContent = data.content;
        currentFileExt = data.extension;

        const codeEl = viewerContent.querySelector("code");
        const lang = hljs.getLanguage(currentFileExt) ? currentFileExt : null;
        if (lang) {
            codeEl.innerHTML = hljs.highlight(data.content, { language: lang }).value;
        } else {
            codeEl.textContent = data.content;
        }

        if (currentFileExt === "html" || currentFileExt === "htm") {
            viewerToggle.classList.remove("hidden");
            showPreview();
        } else {
            viewerToggle.classList.add("hidden");
            showCode();
        }

        fileViewer.classList.remove("hidden");
    } catch (e) {
        alert("Failed to load file");
    }
}

function showPreview() {
    viewerPreview.srcdoc = currentFileContent;
    viewerPreview.classList.remove("hidden");
    viewerContent.classList.add("hidden");
    togglePreview.classList.add("active");
    toggleCode.classList.remove("active");
}

function showCode() {
    viewerPreview.classList.add("hidden");
    viewerContent.classList.remove("hidden");
    toggleCode.classList.add("active");
    togglePreview.classList.remove("active");
}

togglePreview.addEventListener("click", showPreview);
toggleCode.addEventListener("click", showCode);

viewerClose.addEventListener("click", () => {
    fileViewer.classList.add("hidden");
    viewerPreview.srcdoc = "";
});

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        if (!modelDropdown.classList.contains("hidden")) {
            modelDropdown.classList.add("hidden");
            return;
        }
        if (!fileViewer.classList.contains("hidden")) {
            fileViewer.classList.add("hidden");
            return;
        }
        if (!filePanel.classList.contains("hidden")) {
            filePanel.classList.add("hidden");
            filesBtn.classList.remove("active");
            return;
        }
        hideCmdDropdown();
        hideCmdAutocomplete();
    }
});

cmdBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    cmdDropdown.classList.toggle("hidden");
});

document.addEventListener("click", (e) => {
    if (!cmdDropdown.contains(e.target) && e.target !== cmdBtn) {
        hideCmdDropdown();
    }
});

function hideCmdDropdown() {
    cmdDropdown.classList.add("hidden");
}

function hideCmdAutocomplete() {
    cmdAutocomplete.classList.add("hidden");
    acSelectedIndex = -1;
}

async function loadCommands() {
    try {
        const r = await fetch("/api/commands");
        const data = await r.json();
        commands = data.commands;
        renderCmdDropdown();
    } catch (e) {}
}

function renderCmdDropdown() {
    const items = commands.map(
        (c) =>
            `<div class="cmd-item" data-cmd="${escapeHtml(c.name.split(" ")[0])}">
                <span class="cmd-item-name">${escapeHtml(c.name)}</span>
                <span class="cmd-item-desc">${escapeHtml(c.description)}</span>
            </div>`
    ).join("");
    cmdDropdown.innerHTML = `<div class="cmd-dropdown-header">Commands</div>${items}`;

    cmdDropdown.querySelectorAll(".cmd-item").forEach((el) => {
        el.addEventListener("click", () => {
            const cmd = el.dataset.cmd;
            messageInput.value = cmd + " ";
            messageInput.focus();
            hideCmdDropdown();
        });
    });
}

let acSelectedIndex = -1;

messageInput.addEventListener("input", () => {
    const val = messageInput.value;
    if (val.startsWith("/") && !val.includes(" ") && commands.length > 0) {
        const query = val.toLowerCase();
        const filtered = commands.filter((c) =>
            c.name.split(" ")[0].toLowerCase().startsWith(query)
        );
        if (filtered.length > 0 && val.length > 0) {
            showAutocomplete(filtered);
            return;
        }
    }
    hideCmdAutocomplete();
});

messageInput.addEventListener("keydown", (e) => {
    if (cmdAutocomplete.classList.contains("hidden")) return;

    const items = cmdAutocomplete.querySelectorAll(".cmd-ac-item");
    if (!items.length) return;

    if (e.key === "ArrowDown") {
        e.preventDefault();
        acSelectedIndex = Math.min(acSelectedIndex + 1, items.length - 1);
        updateAcSelection(items);
    } else if (e.key === "ArrowUp") {
        e.preventDefault();
        acSelectedIndex = Math.max(acSelectedIndex - 1, 0);
        updateAcSelection(items);
    } else if (e.key === "Tab" || (e.key === "Enter" && acSelectedIndex >= 0)) {
        e.preventDefault();
        const sel = items[Math.max(acSelectedIndex, 0)];
        if (sel) {
            messageInput.value = sel.dataset.cmd + " ";
            hideCmdAutocomplete();
        }
    }
});

function updateAcSelection(items) {
    items.forEach((el, i) => {
        el.classList.toggle("selected", i === acSelectedIndex);
    });
}

function showAutocomplete(filtered) {
    acSelectedIndex = -1;
    cmdAutocomplete.innerHTML = filtered
        .map(
            (c) =>
                `<div class="cmd-ac-item" data-cmd="${escapeHtml(c.name.split(" ")[0])}">
                    <span class="cmd-ac-name">${escapeHtml(c.name)}</span>
                    <span class="cmd-ac-desc">${escapeHtml(c.description)}</span>
                </div>`
        )
        .join("");
    cmdAutocomplete.classList.remove("hidden");

    cmdAutocomplete.querySelectorAll(".cmd-ac-item").forEach((el) => {
        el.addEventListener("click", () => {
            messageInput.value = el.dataset.cmd + " ";
            messageInput.focus();
            hideCmdAutocomplete();
        });
    });
}

function onFileWritten(path) {
    if (filePanel.classList.contains("hidden")) {
        filePanel.classList.remove("hidden");
        filesBtn.classList.add("active");
    }
    loadFiles();
}

loadCommands();

modelTrigger.addEventListener("click", (e) => {
    e.stopPropagation();
    const isHidden = modelDropdown.classList.contains("hidden");
    hideCmdDropdown();
    modelDropdown.classList.toggle("hidden", !isHidden);
    if (isHidden) loadModels();
});

document.addEventListener("click", (e) => {
    if (!modelDropdown.contains(e.target) && !modelTrigger.contains(e.target)) {
        modelDropdown.classList.add("hidden");
    }
});

async function loadModels() {
    if (modelsCache) {
        renderModels(modelsCache);
        return;
    }
    modelList.innerHTML = '<div class="model-loading">Loading models...</div>';
    try {
        const r = await fetch("/api/models");
        const data = await r.json();
        modelsCache = data.models || [];
        renderModels(modelsCache);
    } catch (e) {
        modelList.innerHTML = '<div class="model-loading" style="color:var(--accent-red);">Failed to load models</div>';
    }
}

function renderModels(models) {
    const current = currentModelEl.textContent;
    modelList.innerHTML = models.map((m) => {
        const isActive = m.id === current;
        const ctx = m.context_length ? `${Math.round(m.context_length / 1024)}K` : "";
        return `<div class="model-item${isActive ? " active" : ""}" data-model="${escapeHtml(m.id)}">
            <span class="model-item-check">${isActive ? "&#10003;" : ""}</span>
            <span class="model-item-name">${escapeHtml(m.id)}</span>
            <span class="model-item-meta">${ctx}</span>
        </div>`;
    }).join("");

    modelList.querySelectorAll(".model-item").forEach((el) => {
        el.addEventListener("click", () => switchModel(el.dataset.model));
    });
}

let historyCache = null;

async function showHistory() {
    try {
        const r = await fetch("/api/history");
        const data = await r.json();
        historyCache = data.sessions;
        if (!historyCache.length) {
            addAssistantMessage("<p style='color:var(--text-secondary)'>No conversation history.</p>");
            return;
        }
        let html = '<div class="history-list"><p style="margin-bottom:12px;color:var(--text-secondary)">Past conversations (click to resume):</p><table style="width:100%;border-collapse:collapse;font-size:12px">';
        html += '<tr style="color:var(--text-secondary);text-align:left"><th style="padding:6px 8px">#</th><th style="padding:6px 8px">Preview</th><th style="padding:6px 8px">Messages</th><th style="padding:6px 8px">When</th></tr>';
        historyCache.forEach((s, i) => {
            const age = (Date.now() / 1000) - s.updated_at;
            let when;
            if (age < 3600) when = Math.floor(age / 60) + "m ago";
            else if (age < 86400) when = Math.floor(age / 3600) + "h ago";
            else when = Math.floor(age / 86400) + "d ago";
            const current = s.session_id === data.current_session ? " *" : "";
            const preview = escapeHtml(s.preview || "(empty)");
            html += `<tr class="history-row" data-idx="${i + 1}" style="cursor:pointer;border-top:1px solid var(--border-color)">`;
            html += `<td style="padding:6px 8px;color:var(--accent-cyan)">${i + 1}${current}</td>`;
            html += `<td style="padding:6px 8px">${preview}</td>`;
            html += `<td style="padding:6px 8px;text-align:center">${s.message_count}</td>`;
            html += `<td style="padding:6px 8px;color:var(--text-secondary)">${when}</td>`;
            html += `</tr>`;
        });
        html += '</table><p style="margin-top:10px;color:var(--text-secondary);font-size:11px">Type /history &lt;number&gt; to resume</p></div>';
        const el = addAssistantMessage(html);
        el.querySelectorAll(".history-row").forEach(row => {
            row.addEventListener("click", () => {
                loadHistorySession(parseInt(row.dataset.idx));
            });
        });
    } catch (e) {
        addError("Failed to load history");
    }
}

async function loadHistorySession(num) {
    if (!historyCache) {
        try {
            const r = await fetch("/api/history");
            const data = await r.json();
            historyCache = data.sessions;
        } catch (e) {
            addError("Failed to load history");
            return;
        }
    }
    const idx = num - 1;
    if (idx < 0 || idx >= historyCache.length) {
        addAssistantMessage("<p style='color:var(--text-secondary)'>Invalid session number. Use /history to see available sessions.</p>");
        return;
    }
    const session = historyCache[idx];
    try {
        const r = await fetch(`/api/history/${session.session_id}`, { method: "POST" });
        const data = await r.json();
        if (data.error) {
            addError(data.error);
            return;
        }
        messagesEl.innerHTML = `<div class="welcome-message"><p>Resumed conversation: "${escapeHtml(session.preview)}" (${data.message_count} messages)</p></div>`;
        tokenDisplay.textContent = "";
        historyCache = null;
    } catch (e) {
        addError("Failed to load session");
    }
}

async function switchModel(modelId) {
    const current = currentModelEl.textContent;
    if (modelId === current) {
        modelDropdown.classList.add("hidden");
        return;
    }
    try {
        const r = await fetch("/api/model", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ model: modelId, persist: true }),
        });
        const data = await r.json();
        if (data.model) {
            currentModelEl.textContent = data.model;
            messagesEl.innerHTML = `<div class="welcome-message"><p>Switched to <span style="color:var(--accent-cyan)">${escapeHtml(data.model)}</span>. Conversation reset.</p></div>`;
            tokenDisplay.textContent = "";
            modelsCache = null;
        }
    } catch (e) {
        addError("Failed to switch model");
    }
    modelDropdown.classList.add("hidden");
}
