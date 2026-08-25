/* Compact assistant message actions and object-safe rendering.
   Loaded after chatbot.js so existing chat rendering stays intact. */
(function () {
  "use strict";

  function displayText(value) {
    if (value == null) return "";
    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    if (Array.isArray(value)) return value.map(displayText).filter(Boolean).join("\n");
    if (typeof value === "object") {
      for (const key of ["reply", "answer", "content", "text", "message", "detail"]) {
        if (value[key] != null) return displayText(value[key]);
      }
      try { return JSON.stringify(value, null, 2); } catch (_) { return String(value); }
    }
    return String(value);
  }

  function install() {
    if (typeof window.addMessage === "function" && !window.addMessage.__objectSafe) {
      const originalAddMessage = window.addMessage;
      function wrappedAddMessage(text, role, melimi, audit) {
        originalAddMessage(displayText(text), role, melimi, audit);
      }
      wrappedAddMessage.__objectSafe = true;
      window.addMessage = wrappedAddMessage;
    }
    if (typeof window.addError === "function" && !window.addError.__objectSafe) {
      const originalAddError = window.addError;
      function wrappedAddError(value) { originalAddError(displayText(value)); }
      wrappedAddError.__objectSafe = true;
      window.addError = wrappedAddError;
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", install, { once: true });
  } else {
    install();
  }
})();
