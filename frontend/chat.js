document.addEventListener("DOMContentLoaded", () => {
  const widgetHtml = `
    <button id="chat-toggle">💬 Yatra Assistant</button>
    <div id="chat-window">
      <div id="chat-header">
        <span>Yatra AI Assistant</span>
        <span style="cursor:pointer" id="chat-close">✕</span>
      </div>
      <div id="chat-messages">
        <div class="msg bot">Namaste! Main Yatra Assistant hoon. Flights, hotels search karne, book/modify karne, trip plan banane ya policy poochne ke liye message karein.</div>
      </div>
      <form id="chat-form">
        <input type="text" id="chat-input" placeholder="Ask anything..." required />
        <button type="submit">Send</button>
      </form>
    </div>
  `;
  document.body.insertAdjacentHTML("beforeend", widgetHtml);

  const win = document.getElementById("chat-window");
  const msgs = document.getElementById("chat-messages");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");

  document.getElementById("chat-toggle").onclick = () => {
    win.style.display = win.style.display === "flex" ? "none" : "flex";
  };
  document.getElementById("chat-close").onclick = () => (win.style.display = "none");

  function appendMsg(text, sender, interruptData = null, toolCalls = []) {
    const div = document.createElement("div");
    div.className = `msg ${sender}`;
    div.textContent = text;

    if (toolCalls && toolCalls.length > 0) {
      const trace = document.createElement("div");
      trace.style.cssText = "font-size:0.72rem; color:#64748b; margin-top:6px; border-top:1px dashed #cbd5e1; padding-top:4px;";
      trace.textContent = `⚙️ Tools: ${toolCalls.join(" → ")}`;
      div.appendChild(trace);
    }

    if (interruptData) {
      const box = document.createElement("div");
      box.className = "confirm-box";
      box.innerHTML = `
        <p style="font-size:0.85rem; margin-bottom:6px;"><strong>Confirm Action?</strong></p>
        <button class="btn-accent" style="padding:4px 10px; font-size:0.8rem;" onclick="resumeChat(true)">Confirm</button>
        <button class="btn-danger" style="padding:4px 10px; font-size:0.8rem;" onclick="resumeChat(false)">Cancel</button>
      `;
      div.appendChild(box);
    }
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
  }

  window.resumeChat = async (approved) => {
    appendMsg(approved ? "Confirmed ✅" : "Cancelled ❌", "user");
    try {
      const res = await apiFetch("/chat", {
        method: "POST",
        body: JSON.stringify({ message: approved ? "CONFIRM" : "CANCEL", resume: approved }),
      });
      appendMsg(res.reply || JSON.stringify(res), "bot", null, res.tool_calls || []);
    } catch (err) {
      appendMsg(`Error: ${err.message}`, "bot");
    }
  };

  form.onsubmit = async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    appendMsg(text, "user");
    input.value = "";

    try {
      const res = await apiFetch("/chat", {
        method: "POST",
        body: JSON.stringify({ message: text }),
      });
      appendMsg(res.reply || "Done!", "bot", res.requires_confirmation ? res : null, res.tool_calls || []);
    } catch (err) {
      appendMsg(`Error: ${err.message}`, "bot");
    }
  };
});