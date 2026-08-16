/* Compact assistant message actions.
   Loaded after chatbot.js so existing chat rendering stays intact. */
(function () {
  "use strict";

  function installStyles() {
    if (document.getElementById("teluai-message-actions-style")) return;
    const style = document.createElement("style");
    style.id = "teluai-message-actions-style";
    style.textContent = `
      .message.assistant { flex-direction: column; align-items: flex-start; gap: 5px; }
      .message.assistant .message-content { max-width: min(75%, 680px); }
      .message-actions { display:flex; align-items:center; gap:4px; margin-left:3px; opacity:.82; }
      .message-action { border:1px solid transparent; background:transparent; color:#77777e; border-radius:7px; padding:4px 8px; min-height:28px; font:12px inherit; cursor:pointer; }
      .message-action:hover,.message-action:focus-visible { background:#171719; border-color:#29292d; color:#b1b1b7; outline:none; }
      .message-action.active { color:#d9a441; background:rgba(217,164,65,.08); border-color:rgba(217,164,65,.18); }
      .message-action:disabled { opacity:.55; cursor:default; }
      @media (max-width:760px) {
        .message.assistant .message-content { max-width:88%; }
        .message-actions { margin-left:2px; }
      }
    `;
    document.head.appendChild(style);
  }

  function makeAction(label, aria, handler) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "message-action";
    button.textContent = label;
    button.setAttribute("aria-label", aria);
    button.addEventListener("click", handler);
    return button;
  }

  async function sendFeedback(rating, button) {
    button.disabled = true;
    try {
      const response = await fetch("/feedback", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message_id: null, rating, text: "" })
      });
      if (!response.ok) throw new Error("feedback failed");
      const parent = button.parentElement;
      parent.querySelectorAll(".message-action").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
    } catch (error) {
      console.debug("TeluAI feedback unavailable", error);
    } finally {
      button.disabled = false;
    }
  }

  function addActions(wrapper, text) {
    if (!wrapper || wrapper.querySelector(".message-actions")) return;
    const actions = document.createElement("div");
    actions.className = "message-actions";
    actions.setAttribute("aria-label", "Message actions");

    const copy = makeAction("Copy", "Copy response", async () => {
      try {
        await navigator.clipboard.writeText(String(text));
        copy.textContent = "Copied";
        copy.classList.add("active");
        setTimeout(() => { copy.textContent = "Copy"; copy.classList.remove("active"); }, 1200);
      } catch (error) {
        console.debug("Clipboard unavailable", error);
      }
    });
    const good = makeAction("Good", "Good response", () => sendFeedback(5, good));
    const bad = makeAction("Not helpful", "Not helpful response", () => sendFeedback(1, bad));
    actions.append(copy, good, bad);
    wrapper.appendChild(actions);
  }

  function install() {
    installStyles();
    if (typeof window.addMessage !== "function" || window.addMessage.__messageActionsWrapped) return;
    const original = window.addMessage;
    function wrappedAddMessage(text, role, melimi, audit) {
      original(text, role, melimi, audit);
      if (role !== "assistant") return;
      const messages = document.querySelectorAll("#chatContainer .message.assistant");
      const wrapper = messages[messages.length - 1];
      addActions(wrapper, text);
    }
    wrappedAddMessage.__messageActionsWrapped = true;
    window.addMessage = wrappedAddMessage;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", install, { once: true });
  } else {
    install();
  }
})();
