/**
 * Nexus Voice Assistant - Frontend Realtime Dashboard Controller
 */

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements - Status & Metrics
    const statusDisplay = document.getElementById("current-status-display");
    const statusSubtext = document.getElementById("status-subtext");
    const statusPill = document.getElementById("status-pill");
    const orbVisualizer = document.getElementById("orb-visualizer");
    const connectionDot = document.getElementById("connection-dot");
    const connectionStatus = document.getElementById("connection-status");
    const activeHandlerVal = document.getElementById("active-handler-val");
    const totalCyclesVal = document.getElementById("total-cycles-val");
    const uptimeCounter = document.getElementById("uptime-counter");

    // Pipeline Step Nodes
    const nodeWake = document.getElementById("node-wake");
    const nodeRecord = document.getElementById("node-record");
    const nodeTranscribe = document.getElementById("node-transcribe");
    const nodeRoute = document.getElementById("node-route");
    const nodeSpeak = document.getElementById("node-speak");
    const stepNodes = [nodeWake, nodeRecord, nodeTranscribe, nodeRoute, nodeSpeak];

    // History Panel Elements
    const historyStream = document.getElementById("history-stream");
    const historyBadge = document.getElementById("history-badge");
    const historySearch = document.getElementById("history-search");
    const clearHistoryBtn = document.getElementById("clear-history-btn");
    const emptyState = document.getElementById("empty-state");

    // Simulator Elements
    const simForm = document.getElementById("sim-form");
    const simInput = document.getElementById("sim-input");
    const simSubmitBtn = document.getElementById("sim-submit-btn");
    const tagButtons = document.querySelectorAll(".tag-btn");

    // State cache
    let lastHistoryChecksum = "";
    let localHistoryList = [];
    let isConnected = true;

    // -------------------------------------------------------------
    // Polling Loop for Live Status & History
    // -------------------------------------------------------------
    async function pollState() {
        try {
            const [statusRes, historyRes] = await Promise.all([
                fetch("/status", { cache: "no-store" }),
                fetch("/history", { cache: "no-store" })
            ]);

            if (!statusRes.ok || !historyRes.ok) {
                throw new Error("HTTP error polling dashboard endpoints");
            }

            const statusData = await statusRes.json();
            const historyData = await historyRes.json();

            updateStatusUI(statusData);
            updateHistoryUI(historyData);
            setConnected(true);
        } catch (err) {
            console.warn("Polling error:", err);
            setConnected(false);
        }
    }

    // Stepper Items inside Live Pipeline Status card (Step 2)
    const stepperWake = document.getElementById("stepper-node-wake");
    const stepperRecord = document.getElementById("stepper-node-record");
    const stepperTranscribe = document.getElementById("stepper-node-transcribe");
    const stepperRoute = document.getElementById("stepper-node-route");
    const stepperSpeak = document.getElementById("stepper-node-speak");
    const stepperNodes = [stepperWake, stepperRecord, stepperTranscribe, stepperRoute, stepperSpeak];

    const stepperPillWake = document.getElementById("stepper-pill-wake");
    const stepperPillRecord = document.getElementById("stepper-pill-record");
    const stepperPillTranscribe = document.getElementById("stepper-pill-transcribe");
    const stepperPillRoute = document.getElementById("stepper-pill-route");
    const stepperPillSpeak = document.getElementById("stepper-pill-speak");

    function setStepperBadge(pill, text, statusType) {
        if (!pill) return;
        pill.textContent = text;
        pill.className = "stepper-pill " + statusType;
    }

    function setConnected(connected) {
        if (connected === isConnected && connectionDot.classList.contains(connected ? "active" : "error")) return;
        isConnected = connected;
        if (connected) {
            connectionDot.className = "pulse-dot active";
            connectionDot.style.removeProperty("background-color");
            connectionDot.style.removeProperty("box-shadow");
            connectionStatus.textContent = "Live Connected";
        } else {
            connectionDot.className = "pulse-dot error";
            connectionDot.style.backgroundColor = "var(--accent-rose)";
            connectionDot.style.boxShadow = "0 0 10px var(--accent-rose)";
            connectionStatus.textContent = "Reconnecting...";
        }
    }

    // -------------------------------------------------------------
    // Update Live Status & Visualizer Orb
    // -------------------------------------------------------------
    function updateStatusUI(data) {
        const rawStatus = (data.status || "Idle / Listening for wake word").trim();
        const activeModule = data.active_module || "Wake Word Engine";
        const cycles = data.total_cycles || 0;
        const uptime = data.uptime_seconds || 0;

        statusDisplay.textContent = rawStatus;
        if (activeHandlerVal) activeHandlerVal.textContent = activeModule;
        totalCyclesVal.textContent = cycles;
        uptimeCounter.textContent = formatUptime(uptime);

        // Reset step highlights for both Module Status Map and Live Pipeline Stepper
        stepNodes.forEach(n => n && n.classList.remove("active-step"));
        stepperNodes.forEach(n => n && n.classList.remove("active-step"));

        // Default stepper states
        setStepperBadge(stepperPillWake, "Ready", "pill-ready");
        setStepperBadge(stepperPillRecord, "Ready", "pill-ready");
        setStepperBadge(stepperPillTranscribe, "Ready", "pill-ready");
        setStepperBadge(stepperPillRoute, "Ready", "pill-ready");
        setStepperBadge(stepperPillSpeak, "Ready", "pill-ready");

        // State Machine Mapping
        if (rawStatus.includes("wake word") || rawStatus.toLowerCase().includes("idle")) {
            orbVisualizer.setAttribute("data-state", "idle");
            statusPill.textContent = "LISTENING";
            statusPill.style.color = "var(--accent-emerald)";
            statusPill.style.borderColor = "rgba(16, 185, 129, 0.4)";
            statusSubtext.textContent = "Waiting for wake word trigger ('Nexus')...";
            if (nodeWake) nodeWake.classList.add("active-step");
            if (stepperWake) stepperWake.classList.add("active-step");
            setStepperBadge(stepperPillWake, "Active", "pill-active");
        } else if (rawStatus.toLowerCase().includes("command") || rawStatus.toLowerCase().includes("listening for command")) {
            orbVisualizer.setAttribute("data-state", "recording");
            statusPill.textContent = "RECORDING";
            statusPill.style.color = "var(--accent-rose)";
            statusPill.style.borderColor = "rgba(244, 63, 94, 0.4)";
            statusSubtext.textContent = "Microphone open: Speak your query now...";
            if (nodeRecord) nodeRecord.classList.add("active-step");
            if (stepperRecord) stepperRecord.classList.add("active-step");
            setStepperBadge(stepperPillWake, "Active", "pill-active");
            setStepperBadge(stepperPillRecord, "Recording", "pill-recording");
        } else if (rawStatus.toLowerCase().includes("transcribing")) {
            orbVisualizer.setAttribute("data-state", "processing");
            statusPill.textContent = "TRANSCRIBING";
            statusPill.style.color = "var(--primary-cyan)";
            statusPill.style.borderColor = "rgba(0, 210, 255, 0.4)";
            statusSubtext.textContent = "Transcribing audio to text...";
            if (nodeTranscribe) nodeTranscribe.classList.add("active-step");
            if (stepperTranscribe) stepperTranscribe.classList.add("active-step");
            setStepperBadge(stepperPillWake, "Active", "pill-active");
            setStepperBadge(stepperPillRecord, "Active", "pill-active");
            setStepperBadge(stepperPillTranscribe, "Processing", "pill-processing");
        } else if (rawStatus.toLowerCase().includes("processing")) {
            orbVisualizer.setAttribute("data-state", "processing");
            statusPill.textContent = "PROCESSING";
            statusPill.style.color = "var(--primary-violet)";
            statusPill.style.borderColor = "rgba(139, 92, 246, 0.4)";
            statusSubtext.textContent = `Processing query via ${activeModule}...`;
            if (nodeRoute) nodeRoute.classList.add("active-step");
            if (stepperRoute) stepperRoute.classList.add("active-step");
            setStepperBadge(stepperPillWake, "Active", "pill-active");
            setStepperBadge(stepperPillRecord, "Active", "pill-active");
            setStepperBadge(stepperPillTranscribe, "Active", "pill-active");
            setStepperBadge(stepperPillRoute, "Processing", "pill-processing");
        } else if (rawStatus.toLowerCase().includes("speaking")) {
            orbVisualizer.setAttribute("data-state", "speaking");
            statusPill.textContent = "SPEAKING";
            statusPill.style.color = "var(--accent-emerald)";
            statusPill.style.borderColor = "rgba(16, 185, 129, 0.4)";
            statusSubtext.textContent = "Speaking synthesized response aloud...";
            if (nodeSpeak) nodeSpeak.classList.add("active-step");
            if (stepperSpeak) stepperSpeak.classList.add("active-step");
            setStepperBadge(stepperPillWake, "Active", "pill-active");
            setStepperBadge(stepperPillRecord, "Active", "pill-active");
            setStepperBadge(stepperPillTranscribe, "Active", "pill-active");
            setStepperBadge(stepperPillRoute, "Active", "pill-active");
            setStepperBadge(stepperPillSpeak, "Speaking", "pill-speaking");
        } else if (rawStatus.toLowerCase().includes("error")) {
            orbVisualizer.setAttribute("data-state", "idle");
            statusPill.textContent = "RECOVERING";
            statusPill.style.color = "var(--accent-amber)";
            statusPill.style.borderColor = "rgba(245, 158, 11, 0.4)";
            statusSubtext.textContent = "Handling error and returning to listening mode...";
        }
    }

    // -------------------------------------------------------------
    // Update Interaction History Stream
    // -------------------------------------------------------------
    function updateHistoryUI(historyList) {
        localHistoryList = historyList;
        const count = historyList.length;
        historyBadge.textContent = `${count} interaction${count === 1 ? '' : 's'}`;

        const checksum = JSON.stringify(historyList);
        if (checksum === lastHistoryChecksum) {
            return; // No changes, avoid re-rendering
        }
        lastHistoryChecksum = checksum;

        renderFilteredHistory();
    }

    function renderFilteredHistory() {
        const searchTerm = historySearch.value.trim().toLowerCase();
        const filtered = localHistoryList.filter(item => {
            if (!searchTerm) return true;
            return (
                (item.heard && item.heard.toLowerCase().includes(searchTerm)) ||
                (item.response && item.response.toLowerCase().includes(searchTerm)) ||
                (item.handler && item.handler.toLowerCase().includes(searchTerm))
            );
        });

        if (filtered.length === 0) {
            historyStream.innerHTML = "";
            if (localHistoryList.length === 0) {
                historyStream.appendChild(emptyState);
            } else {
                historyStream.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">🔍</div>
                        <h3>No Matching Results</h3>
                        <p>No voice interactions matched "${escapeHtml(searchTerm)}".</p>
                    </div>
                `;
            }
            return;
        }

        historyStream.innerHTML = "";
        filtered.forEach(item => {
            const card = document.createElement("div");
            card.className = "history-item";

            // Handler badge color
            const handler = item.handler || "Gemini";
            let badgeClass = "badge-default";
            if (handler.toLowerCase().includes("gemini")) badgeClass = "badge-gemini";
            else if (handler.toLowerCase().includes("wiki")) badgeClass = "badge-wikipedia";
            else if (handler.toLowerCase().includes("news")) badgeClass = "badge-news";

            card.innerHTML = `
                <div class="item-meta">
                    <span class="item-time">🕒 ${escapeHtml(item.timestamp || "Just now")}</span>
                    <span class="handler-badge ${badgeClass}">${escapeHtml(handler)}</span>
                </div>
                <div class="item-prompt">
                    <span class="prompt-icon">🗣️</span>
                    <span class="prompt-text">"${escapeHtml(item.heard || "")}"</span>
                </div>
                <div class="item-response">
                    <div class="response-label">
                        <span>Nexus Response</span>
                        <button class="copy-btn" data-text="${escapeHtmlAttr(item.response || '')}">Copy</button>
                    </div>
                    <div class="response-text markdown-body">${renderMarkdown(item.response || "")}</div>
                </div>
            `;
            historyStream.appendChild(card);
        });

        // Attach copy button listeners
        cardCopyListeners();
    }

    function cardCopyListeners() {
        document.querySelectorAll(".copy-btn").forEach(btn => {
            btn.onclick = () => {
                const text = btn.getAttribute("data-text") || "";
                navigator.clipboard.writeText(text).then(() => {
                    showToast("Response copied to clipboard!");
                    btn.textContent = "Copied!";
                    setTimeout(() => { btn.textContent = "Copy"; }, 1500);
                });
            };
        });
    }

    // -------------------------------------------------------------
    // Simulator & Form Submissions
    // -------------------------------------------------------------
    simForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const query = simInput.value.trim();
        if (!query) return;

        simSubmitBtn.disabled = true;
        simSubmitBtn.style.opacity = "0.5";

        try {
            showToast(`Simulating query: "${query}"...`);
            const res = await fetch("/api/test-command", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: query, speak: true })
            });
            const data = await res.json();
            if (data.success) {
                simInput.value = "";
                pollState();
            } else {
                showToast("Simulation error: " + (data.error || "Failed"));
            }
        } catch (err) {
            console.error("Test command error:", err);
            showToast("Failed to send simulation request.");
        } finally {
            simSubmitBtn.disabled = false;
            simSubmitBtn.style.opacity = "1";
        }
    });

    tagButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            simInput.value = btn.getAttribute("data-query");
            simForm.dispatchEvent(new Event("submit"));
        });
    });

    historySearch.addEventListener("input", () => {
        renderFilteredHistory();
    });

    clearHistoryBtn.addEventListener("click", async () => {
        if (!confirm("Clear all interaction history?")) return;
        try {
            await fetch("/api/clear-history", { method: "POST" });
            lastHistoryChecksum = "";
            pollState();
            showToast("Interaction history cleared.");
        } catch (err) {
            showToast("Failed to clear history.");
        }
    });

    // -------------------------------------------------------------
    // Utilities
    // -------------------------------------------------------------
    function formatUptime(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return [h, m, s].map(v => String(v).padStart(2, "0")).join(":");
    }

    function showToast(msg) {
        const container = document.getElementById("toast-container");
        const toast = document.createElement("div");
        toast.className = "toast";
        toast.textContent = msg;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transition = "opacity 0.3s";
            setTimeout(() => toast.remove(), 300);
        }, 2500);
    }

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function escapeHtmlAttr(str) {
        return String(str)
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function renderMarkdown(text) {
        if (!text) return "";
        if (typeof marked !== "undefined" && typeof marked.parse === "function") {
            try {
                return marked.parse(text, { breaks: true, gfm: true });
            } catch (err) {
                console.warn("[Markdown Error] marked.parse failed:", err);
            }
        }
        // Resilient fallback formatting
        let html = escapeHtml(text);
        html = html.replace(/^### (.*$)/gim, "<h4>$1</h4>");
        html = html.replace(/^## (.*$)/gim, "<h3>$1</h3>");
        html = html.replace(/^# (.*$)/gim, "<h2>$1</h2>");
        html = html.replace(/\*\*\*(.*?)\*\*\*/gim, "<strong><em>$1</em></strong>");
        html = html.replace(/\*\*(.*?)\*\*/gim, "<strong>$1</strong>");
        html = html.replace(/\*(.*?)\*/gim, "<em>$1</em>");
        html = html.replace(/`([^`]+)`/gim, "<code>$1</code>");
        html = html.replace(/\n/g, "<br>");
        return html;
    }

    // Start Realtime Polling every 600ms
    pollState();
    setInterval(pollState, 600);
});
