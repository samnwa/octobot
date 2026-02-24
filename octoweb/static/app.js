const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const resetBtn = document.getElementById("reset-btn");
const tokenDisplay = document.getElementById("token-display");
const swimmer = document.getElementById("swimming-octopus");

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

chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = messageInput.value.trim();
    if (!message || isProcessing) return;

    addUserMessage(message);
    messageInput.value = "";
    setProcessing(true);

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message }),
        });

        const reader = response.body.getReader();
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
                            break;
                        case "thinking":
                            if (data.text && data.text !== "Thinking...") {
                                addThinking(data.text);
                            }
                            break;
                        case "tool_use":
                            addToolUse(data.name, data.input);
                            break;
                        case "tool_result":
                            addToolResult(data.name, data.result);
                            break;
                        case "tokens":
                            tokenDisplay.textContent =
                                `${data.input.toLocaleString()} in / ${data.output.toLocaleString()} out`;
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
        addError("Connection error: " + err.message);
    }

    setProcessing(false);
});

resetBtn.addEventListener("click", async () => {
    await fetch("/reset", { method: "POST" });
    messagesEl.innerHTML = `<div class="welcome-message"><p>Conversation reset. Ask me anything.</p></div>`;
    tokenDisplay.textContent = "";
});

function setProcessing(val) {
    isProcessing = val;
    sendBtn.disabled = val;
    messageInput.disabled = val;
    swimmer.classList.toggle("hidden", !val);
    if (!val) messageInput.focus();
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
