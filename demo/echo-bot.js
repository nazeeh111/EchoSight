const ACTIONS = new Map([
  ["welcome", "Welcome"],
  ["connect", "Connect phones"],
  ["reconstruct", "Reconstruction"],
  ["explore", "Explore room"],
  ["start_scan", "Start a scan"],
  ["replay_echoes", "Replay echoes"],
]);
const QUESTIONS = [
  "How does EchoSight work?",
  "What is simulated?",
  "What do the confidence levels mean?",
];
const SERVER_HELP =
  "Start the demo with python3 demo/server.py to use local chat.";
const LIMIT = 2000;
let instance;

function clampMessage(content) {
  const text = content.slice(0, LIMIT);
  const last = text.charCodeAt(text.length - 1);
  // Do not leave half an emoji at the truncation boundary.
  return last >= 0xd800 && last <= 0xdbff ? text.slice(0, -1) : text;
}

function chatBody(messages, page) {
  const payload = {
    messages: messages
      .slice(-10)
      .map(({ role, content }) => ({ role, content: clampMessage(content) })),
    context: { page },
  };
  const encoder = new TextEncoder();
  let body = JSON.stringify(payload);
  while (
    payload.messages.length > 1 &&
    (payload.messages.reduce(
      (count, message) => count + message.content.length,
      0,
    ) > 10000 ||
      encoder.encode(body).byteLength > 24000)
  ) {
    payload.messages.shift();
    body = JSON.stringify(payload);
  }
  return body;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function button(className, text, label) {
  const node = element("button", className, text);
  node.type = "button";
  if (label) node.setAttribute("aria-label", label);
  return node;
}

function mark() {
  const node = element("span", "eb-mark");
  node.setAttribute("aria-hidden", "true");
  for (let i = 0; i < 5; i++) node.append(element("i"));
  return node;
}

function cleanText(value, fallback, max = 500) {
  return typeof value === "string" && value.trim()
    ? value.trim().slice(0, max)
    : fallback;
}

export function initEchoBot() {
  if (instance) return instance;
  const state = {
    open: false,
    available: false,
    checking: false,
    busy: false,
    messages: [],
    retry: null,
    request: null,
    statusRequest: null,
    previousFocus: null,
    destroyed: false,
  };

  const root = element("div", "echo-bot");
  root.id = "echo-bot";
  const launcher = button("eb-launcher", undefined, "Open Echo Bot");
  launcher.append(mark(), element("span", "", "Echo Bot"));
  launcher.setAttribute("aria-haspopup", "dialog");
  launcher.setAttribute("aria-controls", "echo-bot-panel");
  launcher.setAttribute("aria-expanded", "false");

  const panel = element("section", "eb-panel");
  panel.id = "echo-bot-panel";
  panel.hidden = true;
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-modal", "false");
  panel.setAttribute("aria-labelledby", "echo-bot-title");
  panel.setAttribute("aria-describedby", "echo-bot-description");
  const header = element("header", "eb-header");
  const heading = element("div", "eb-heading");
  const title = element("h2", "", "Echo Bot");
  title.id = "echo-bot-title";
  const description = element(
    "p",
    "",
    "Ask about EchoSight. Find your next step.",
  );
  description.id = "echo-bot-description";
  heading.append(title, description);
  const closeButton = button("eb-close", "×", "Close Echo Bot");
  header.append(mark(), heading, closeButton);

  const status = element("div", "eb-status");
  status.dataset.state = "checking";
  const statusCopy = element("div", "eb-status-copy");
  statusCopy.setAttribute("role", "status");
  const statusTitle = element("strong", "", "Local Ollama");
  const statusDetail = element(
    "span",
    "",
    "Check local availability when you open chat.",
  );
  statusCopy.append(statusTitle, statusDetail);
  const checkButton = button(
    "eb-check",
    "Check",
    "Check local Ollama availability",
  );
  status.append(element("i", "eb-status-dot"), statusCopy, checkButton);

  const scroll = element("div", "eb-scroll");
  const empty = element(
    "p",
    "eb-empty",
    "A question about the sound, the room, or the simulation?",
  );
  const log = element("div", "eb-log");
  log.setAttribute("role", "log");
  log.setAttribute("aria-label", "Conversation with Echo Bot");
  log.setAttribute("aria-live", "polite");
  log.setAttribute("aria-relevant", "additions text");
  const prompts = element("div", "eb-prompts");
  for (const question of QUESTIONS) {
    const prompt = button("eb-prompt", question);
    prompt.addEventListener("click", () => {
      input.value = question;
      updateComposer();
      if (state.available && !state.busy) submit();
      else input.focus({ preventScroll: true });
    });
    prompts.append(prompt);
  }
  const errorBox = element("div", "eb-error");
  errorBox.hidden = true;
  const errorText = element("p");
  errorText.setAttribute("role", "status");
  const retryButton = button("eb-retry", "Retry response");
  errorBox.append(errorText, retryButton);

  const navigation = element("details", "eb-navigation");
  navigation.append(element("summary", "", "Jump to a step"));
  const navigationButtons = element("div", "eb-actions");
  for (const [id, label] of ACTIONS) {
    const action = button("eb-action", label);
    action.addEventListener("click", () => navigate(id));
    navigationButtons.append(action);
  }
  navigation.append(navigationButtons);
  scroll.append(empty, log, prompts, errorBox, navigation);

  const form = element("form", "eb-composer");
  const label = element("label", "eb-sr-only", "Your question for Echo Bot");
  label.htmlFor = "echo-bot-input";
  const input = element("textarea", "eb-input");
  input.id = "echo-bot-input";
  input.rows = 2;
  input.maxLength = LIMIT;
  input.placeholder = "Ask about the demo…";
  input.autocomplete = "off";
  const sendButton = button("eb-send", "↑", "Send message");
  sendButton.type = "submit";
  const stopButton = button("eb-stop", "Stop", "Stop the current response");
  stopButton.hidden = true;
  const inputRow = element("div", "eb-input-row");
  inputRow.append(input, sendButton, stopButton);
  const composerNote = element(
    "p",
    "eb-composer-note",
    "Local Ollama · Enter to send · Shift + Enter for a new line",
  );
  form.append(label, inputRow, composerNote);
  panel.append(header, status, scroll, form);
  root.append(panel, launcher);
  document.body.append(root);

  function scrollToLatest() {
    requestAnimationFrame(() => {
      if (!state.destroyed) scroll.scrollTop = scroll.scrollHeight;
    });
  }

  function updateComposer() {
    sendButton.disabled = state.busy || !state.available || !input.value.trim();
    sendButton.hidden = state.busy;
    stopButton.hidden = !state.busy;
    retryButton.disabled = state.busy || !state.available;
    checkButton.disabled = state.checking;
    prompts.querySelectorAll("button").forEach((node) => {
      node.disabled = state.busy;
    });
    form.setAttribute("aria-busy", String(state.busy));
  }

  function open() {
    if (state.open || state.destroyed) return;
    state.previousFocus = document.activeElement;
    state.open = true;
    panel.hidden = false;
    launcher.setAttribute("aria-expanded", "true");
    launcher.setAttribute("aria-label", "Close Echo Bot");
    input.focus({ preventScroll: true });
    if (!state.busy) checkStatus();
  }

  function close() {
    if (!state.open) return;
    state.open = false;
    panel.hidden = true;
    launcher.setAttribute("aria-expanded", "false");
    launcher.setAttribute("aria-label", "Open Echo Bot");
    const target = state.previousFocus?.isConnected
      ? state.previousFocus
      : launcher;
    target.focus({ preventScroll: true });
  }

  function navigate(action) {
    if (!ACTIONS.has(action)) return;
    close();
    window.dispatchEvent(
      new CustomEvent("echobot:navigate", { detail: { action } }),
    );
  }

  async function checkStatus() {
    if (state.checking || state.destroyed) return;
    state.checking = true;
    const controller = new AbortController();
    state.statusRequest = controller;
    const timeout = setTimeout(() => controller.abort(), 8000);
    status.dataset.state = "checking";
    statusTitle.textContent = "Checking local Ollama…";
    statusDetail.textContent = "Chat stays on this computer.";
    updateComposer();
    try {
      const response = await fetch("/api/echo-bot/status", {
        signal: controller.signal,
        cache: "no-store",
      });
      if (!response.ok) throw new Error(SERVER_HELP);
      const data = await response.json();
      if (state.destroyed) return;
      state.available = data.available === true;
      status.dataset.state = state.available ? "ready" : "unavailable";
      statusTitle.textContent = state.available
        ? "Ready locally"
        : "Local model unavailable";
      statusDetail.textContent = state.available
        ? cleanText(data.model, "Ollama", 100) + " · on this computer"
        : cleanText(
            data.message,
            "Start Ollama and load the configured model.",
          );
    } catch (error) {
      if (state.destroyed) return;
      state.available = false;
      status.dataset.state = "unavailable";
      statusTitle.textContent = "Local chat is not running";
      statusDetail.textContent = SERVER_HELP;
    } finally {
      clearTimeout(timeout);
      if (!state.destroyed) {
        state.checking = false;
        state.statusRequest = null;
        updateComposer();
      }
    }
  }

  function appendMessage(role, content) {
    const article = element("article", "eb-message eb-message-" + role);
    article.append(
      element("span", "eb-speaker", role === "user" ? "You" : "Echo Bot"),
    );
    article.append(element("p", "eb-message-text", content));
    log.append(article);
    empty.hidden = true;
    prompts.hidden = true;
    scrollToLatest();
    return article;
  }

  function showFailure(message, entry) {
    state.retry = entry;
    errorText.textContent = message;
    retryButton.textContent = "Retry response";
    errorBox.hidden = false;
    scrollToLatest();
  }

  async function requestReply(entry) {
    if (state.busy || !state.available || state.destroyed) return;
    state.busy = true;
    state.retry = null;
    errorBox.hidden = true;
    entry.delivery = "pending";
    const pending = element("div", "eb-thinking", "Thinking locally…");
    pending.setAttribute("role", "status");
    log.append(pending);
    const controller = new AbortController();
    const request = { controller, stopped: false, timedOut: false };
    state.request = request;
    const timeout = setTimeout(() => {
      request.timedOut = true;
      controller.abort();
    }, 125000);
    const messages = state.messages
      .filter((message) => message.delivery === "complete" || message === entry)
      .slice(-10)
      .map(({ role, content }) => ({ role, content }));
    updateComposer();
    scrollToLatest();
    try {
      const response = await fetch("/api/echo-bot/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: chatBody(messages, document.body.dataset.page || "welcome"),
      });
      let data;
      try {
        data = await response.json();
      } catch {
        throw new Error(
          response.status === 404
            ? SERVER_HELP
            : "Local chat returned an unreadable response. Please retry.",
        );
      }
      if (!response.ok) {
        if (response.status === 503) checkStatus();
        throw new Error(
          cleanText(data.error, "Local chat could not answer. Please retry."),
        );
      }
      if (typeof data.message !== "string" || !data.message.trim()) {
        throw new Error(
          "The local model returned an empty answer. Please retry.",
        );
      }
      if (state.destroyed || request !== state.request || request.stopped)
        return;
      pending.remove();
      entry.delivery = "complete";
      const content = data.message.trim();
      state.messages.push({ role: "assistant", content, delivery: "complete" });
      const article = appendMessage("assistant", content);
      if (Array.isArray(data.actions)) {
        const actions = element("div", "eb-actions");
        const seen = new Set();
        for (const action of data.actions) {
          if (!action || !ACTIONS.has(action.id) || seen.has(action.id))
            continue;
          seen.add(action.id);
          const chip = button(
            "eb-action",
            cleanText(action.label, ACTIONS.get(action.id), 64),
          );
          chip.addEventListener("click", () => navigate(action.id));
          actions.append(chip);
        }
        if (actions.childElementCount) {
          actions.setAttribute("aria-label", "Suggested steps");
          article.append(actions);
        }
      }
    } catch (error) {
      if (state.destroyed || request !== state.request) return;
      entry.delivery = request.stopped ? "stopped" : "failed";
      showFailure(
        request.stopped
          ? "Response stopped."
          : request.timedOut
            ? "The local model took too long. You can retry."
            : cleanText(
                error.message,
                "Could not reach local chat. Please retry.",
              ),
        entry,
      );
    } finally {
      clearTimeout(timeout);
      pending.remove();
      if (request === state.request) {
        state.request = null;
        state.busy = false;
        updateComposer();
        scrollToLatest();
      }
    }
  }

  function submit() {
    const content = clampMessage(input.value.trim());
    if (!content || state.busy || !state.available) return;
    const entry = { role: "user", content, delivery: "pending" };
    state.messages.push(entry);
    appendMessage("user", content);
    input.value = "";
    updateComposer();
    requestReply(entry);
  }

  function onKeyDown(event) {
    if (
      event.key === "Escape" &&
      state.open &&
      !event.defaultPrevented &&
      (panel.contains(document.activeElement) ||
        document.activeElement === launcher)
    ) {
      event.preventDefault();
      event.stopPropagation();
      close();
    }
  }
  launcher.addEventListener("click", () => (state.open ? close() : open()));
  closeButton.addEventListener("click", close);
  checkButton.addEventListener("click", checkStatus);
  retryButton.addEventListener("click", () => {
    if (state.retry) requestReply(state.retry);
  });
  input.addEventListener("input", updateComposer);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      submit();
    }
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    submit();
  });
  stopButton.addEventListener("click", () => {
    if (!state.request) return;
    state.request.stopped = true;
    state.request.controller.abort();
  });
  root.addEventListener("keydown", onKeyDown);
  updateComposer();
  instance = {
    open,
    close,
    destroy() {
      close();
      state.destroyed = true;
      state.request?.controller.abort();
      state.statusRequest?.abort();
      root.remove();
      instance = undefined;
    },
  };
  return instance;
}
