/* DocMind frontend - plain JavaScript, no build step. */
(() => {
  "use strict";

  // ---------- Small helpers ----------
  const $ = (sel) => document.querySelector(sel);
  const els = {
    sidebar: $("#sidebar"), overlay: $("#overlay"), menuBtn: $("#menuBtn"),
    newChat: $("#newChatBtn"), history: $("#historyList"), clearBtn: $("#clearBtn"),
    themeBtn: $("#themeBtn"), docDot: $("#docDot"), docName: $("#docName"), docMeta: $("#docMeta"),
    title: $("#chatTitle"), select: $("#patternSelect"), hint: $("#patternHint"),
    banner: $("#banner"), chat: $("#chat"), inner: $("#chatInner"),
    form: $("#chatForm"), input: $("#input"), send: $("#sendBtn"), toast: $("#toast"),
  };

  const CHATS_KEY = "docmind.chats.v1";
  const PREFS_KEY = "docmind.prefs.v1";
  const HISTORY_SENT = 6;

  const state = {
    chats: [], activeId: null, busy: false,
    pattern: "Zero-Shot", config: null, status: { state: "idle" }, pollTimer: null,
  };

  const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 7);

  function readJSON(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; }
  }
  function writeJSON(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* storage full or blocked */ }
  }

  function h(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  const ICONS = {
    logo: '<svg viewBox="0 0 24 24" width="20" height="20"><path d="M7 5h6.2a4.6 4.6 0 0 1 0 9.2H11V19H7z" fill="#fff"/></svg>',
    logoBig: '<svg viewBox="0 0 24 24" width="34" height="34"><path d="M7 5h6.2a4.6 4.6 0 0 1 0 9.2H11V19H7z" fill="#fff"/></svg>',
    book: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 19V5"/></svg>',
    bulb: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/></svg>',
    list: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01"/></svg>',
    child: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M5 21a7 7 0 0 1 14 0"/></svg>',
    copy: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>',
    chevron: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 6 6 6-6 6"/></svg>',
    x: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>',
    alert: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h.01"/></svg>',
  };

  // ---------- Safe, tiny Markdown renderer (escapes HTML first) ----------
  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function inline(s) {
    s = esc(s);
    s = s.replace(/`([^`\n]+)`/g, "<code>$1</code>");
    s = s.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/(^|[^*\w])\*([^*\n]+)\*(?!\w)/g, "$1<em>$2</em>");
    return s;
  }
  function markdown(src) {
    const lines = String(src).replace(/\r/g, "").split("\n");
    let html = "", para = [], list = null, code = null;
    const flushPara = () => { if (para.length) { html += "<p>" + para.map(inline).join("<br>") + "</p>"; para = []; } };
    const closeList = () => { if (list) { html += `</${list}>`; list = null; } };

    for (const line of lines) {
      if (code !== null) {
        if (/^```/.test(line)) { html += "<pre><code>" + esc(code.join("\n")) + "</code></pre>"; code = null; }
        else code.push(line);
        continue;
      }
      if (/^```/.test(line)) { flushPara(); closeList(); code = []; continue; }
      if (!line.trim()) { flushPara(); closeList(); continue; }

      let m;
      if ((m = line.match(/^(#{1,4})\s+(.*)$/))) {
        flushPara(); closeList();
        const level = Math.min(m[1].length + 2, 5);
        html += `<h${level}>${inline(m[2])}</h${level}>`;
      } else if ((m = line.match(/^\s*[-*•]\s+(.*)$/))) {
        flushPara();
        if (list !== "ul") { closeList(); html += "<ul>"; list = "ul"; }
        html += `<li>${inline(m[1])}</li>`;
      } else if ((m = line.match(/^\s*\d+[.)]\s+(.*)$/))) {
        flushPara();
        if (list !== "ol") { closeList(); html += "<ol>"; list = "ol"; }
        html += `<li>${inline(m[1])}</li>`;
      } else {
        closeList();
        para.push(line);
      }
    }
    if (code !== null) html += "<pre><code>" + esc(code.join("\n")) + "</code></pre>";
    flushPara(); closeList();
    return html;
  }

  // ---------- Storage ----------
  const saveChats = () => writeJSON(CHATS_KEY, { chats: state.chats, activeId: state.activeId });
  const activeChat = () => state.chats.find((c) => c.id === state.activeId);

  function newChat() {
    const current = activeChat();
    if (current && current.messages.length === 0) { closeSidebar(); els.input.focus(); return; }
    const chat = { id: uid(), title: "New chat", created: Date.now(), messages: [] };
    state.chats.unshift(chat);
    state.activeId = chat.id;
    saveChats(); renderAll(); closeSidebar(); els.input.focus();
  }

  function openChat(id) {
    state.activeId = id;
    saveChats(); renderAll(); closeSidebar();
  }

  function deleteChat(id) {
    state.chats = state.chats.filter((c) => c.id !== id);
    if (state.activeId === id) state.activeId = state.chats[0]?.id ?? null;
    if (!state.chats.length) { newChat(); return; }
    saveChats(); renderAll();
  }

  // ---------- Rendering ----------
  function renderAll() { renderSidebar(); renderChat(); updateSendState(); }

  function renderSidebar() {
    els.history.replaceChildren();
    const chats = state.chats.filter((c) => c.messages.length > 0);
    if (!chats.length) {
      els.history.append(h("div", "history-empty", "No conversations yet. Ask your first question to get started."));
    }
    for (const chat of chats) {
      const row = h("div", "history-item" + (chat.id === state.activeId ? " active" : ""));
      const open = h("button", "history-open", chat.title);
      open.type = "button"; open.title = chat.title;
      open.addEventListener("click", () => openChat(chat.id));
      const del = h("button", "history-del"); del.type = "button";
      del.setAttribute("aria-label", "Delete chat"); del.innerHTML = ICONS.x;
      del.addEventListener("click", (e) => { e.stopPropagation(); deleteChat(chat.id); });
      row.append(open, del);
      els.history.append(row);
    }
    const chat = activeChat();
    els.title.textContent = chat && chat.messages.length ? chat.title : "New chat";
    document.title = (chat && chat.messages.length ? chat.title + " - " : "") + (state.config?.app_name || "DocMind");
  }

  function renderChat() {
    els.inner.replaceChildren();
    const chat = activeChat();
    if (!chat || !chat.messages.length) { els.inner.append(welcomeEl()); return; }
    for (const msg of chat.messages) els.inner.append(messageEl(msg));
    scrollToBottom(false);
  }

  function welcomeEl() {
    const wrap = h("div", "welcome");
    const logo = h("div", "hero-logo"); logo.innerHTML = ICONS.logoBig;
    const title = h("h2");
    title.append("Understand the law, ", Object.assign(h("span"), { textContent: "section by section" }));
    const lead = h("p", "lead",
       "Ask about any offence, definition or punishment in the Pakistan Penal Code, 1860, " +
       "and get a clear answer based on the actual text of the law.");

    const label = h("div", "suggest-title", "Try asking");
    const grid = h("div", "suggestions");
    const ready = state.status.state === "ready";
    for (const s of state.config?.suggestions || []) {
      const btn = h("button", "suggestion"); btn.type = "button"; btn.disabled = !ready;
      const icon = h("span", "s-icon"); icon.innerHTML = ICONS[s.icon] || ICONS.book;
      btn.append(icon, h("span", "", s.text));
      btn.addEventListener("click", () => submit(s.text));
      grid.append(btn);
    }
    wrap.append(logo, title, lead, label, grid);
    return wrap;
  }

  function messageEl(msg) {
    if (msg.role === "user") {
      const row = h("div", "msg user");
      row.append(h("div", "bubble", msg.content));
      return row;
    }
    const row = h("div", "msg ai");
    const avatar = h("div", "avatar"); avatar.innerHTML = ICONS.logo;
    const body = h("div", "msg-body");
    const card = h("div", "ai-card");
    const prose = h("div", "prose"); prose.innerHTML = markdown(msg.content);
    card.append(prose);
    body.append(card);

    const meta = msg.meta || {};
    const metaRow = h("div", "meta-row");
    if (meta.pattern) metaRow.append(h("span", "tag", meta.pattern));
    if (meta.ms) metaRow.append(h("span", "", (meta.ms / 1000).toFixed(1) + "s"));
    const copy = h("button", "meta-btn"); copy.type = "button";
    copy.innerHTML = ICONS.copy + "<span>Copy</span>";
    copy.addEventListener("click", () => copyText(msg.content));
    metaRow.append(copy);
    body.append(metaRow);

    if (meta.sources && meta.sources.length) {
      const det = h("details", "sources");
      const sum = h("summary"); sum.innerHTML = ICONS.chevron + "<span>Sources (" + meta.sources.length + ")</span>";
      det.append(sum);
      for (const s of meta.sources) {
        const item = h("div", "source-item");
        const head = h("div", "source-head");
        head.append(h("span", "tag", s.technique), h("span", "", "score " + s.score.toFixed(2)));
        item.append(head, h("div", "source-text", s.text + (s.text.length >= 400 ? "..." : "")));
        det.append(item);
      }
      body.append(det);
    }
    row.append(avatar, body);
    return row;
  }

  function typingEl() {
    const row = h("div", "msg ai typing"); row.id = "typing";
    const avatar = h("div", "avatar"); avatar.innerHTML = ICONS.logo;
    const dots = h("div", "dots"); dots.append(h("i"), h("i"), h("i"));
    row.append(avatar, dots, h("span", "label", "Searching the document..."));
    return row;
  }

  function errorEl(message, retry) {
    const row = h("div", "msg ai"); row.id = "errorMsg";
    const avatar = h("div", "avatar"); avatar.innerHTML = ICONS.logo;
    const body = h("div", "msg-body");
    const card = h("div", "ai-card error");
    const t = h("div", "err-title"); t.innerHTML = ICONS.alert + "<span>Couldn't get an answer</span>";
    card.append(t, h("div", "", message));
    if (retry) {
      const btn = h("button", "retry-btn", "Try again"); btn.type = "button";
      btn.addEventListener("click", retry);
      card.append(btn);
    }
    body.append(card); row.append(avatar, body);
    return row;
  }

  function scrollToBottom(smooth = true) {
    requestAnimationFrame(() => els.chat.scrollTo({ top: els.chat.scrollHeight, behavior: smooth ? "smooth" : "auto" }));
  }

  // ---------- Sending ----------
  async function submit(text) {
    text = (text || "").trim();
    if (!text || state.busy) return;
    if (state.status.state !== "ready") { toast("The knowledge base is still getting ready..."); return; }

    const chat = activeChat();
    chat.messages.push({ role: "user", content: text });
    if (chat.messages.length === 1) chat.title = text.length > 48 ? text.slice(0, 48) + "..." : text;
    saveChats();
    els.input.value = ""; autosize();
    renderAll();
    await requestAnswer(chat.id, text);
  }

  async function requestAnswer(chatId, question) {
    const chat = state.chats.find((c) => c.id === chatId);
    if (!chat) return;
    state.busy = true; updateSendState();
    document.getElementById("errorMsg")?.remove();

    const history = chat.messages.slice(0, -1).slice(-HISTORY_SENT)
      .map((m) => ({ role: m.role, content: m.content }));
    els.inner.append(typingEl());
    scrollToBottom();

    let result, failure = null;
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, pattern: state.pattern, history }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) failure = data.error || "Something went wrong. Please try again.";
      else result = data;
    } catch {
      failure = "Could not reach the server. Is the app still running?";
    }

    document.getElementById("typing")?.remove();
    state.busy = false;

    if (failure) {
      if (state.activeId === chatId) { els.inner.append(errorEl(failure, () => requestAnswer(chatId, question))); scrollToBottom(); }
    } else {
      chat.messages.push({
        role: "assistant", content: result.answer,
        meta: { pattern: result.pattern, ms: result.elapsed_ms, sources: result.sources },
      });
      saveChats();
      if (state.activeId === chatId) {
        els.inner.append(messageEl(chat.messages[chat.messages.length - 1]));
        scrollToBottom();
      }
    }
    updateSendState();
    if (state.activeId === chatId) els.input.focus();
  }

  // ---------- Composer ----------
  function autosize() {
    els.input.style.height = "auto";
    els.input.style.height = Math.min(els.input.scrollHeight, 160) + "px";
  }
  function updateSendState() {
    const ready = state.status.state === "ready";
    els.send.disabled = !(ready && !state.busy && els.input.value.trim());
    els.input.placeholder = ready ? "Ask anything about your document..." : "Preparing the knowledge base...";
  }

  // ---------- Pattern dropdown ----------
  function setupPatterns() {
    const patterns = state.config.patterns;
    els.select.replaceChildren(...patterns.map((p) => Object.assign(document.createElement("option"), { value: p.name, textContent: p.name })));
    const saved = readJSON(PREFS_KEY, {}).pattern;
    state.pattern = patterns.some((p) => p.name === saved) ? saved : state.config.default_pattern;
    els.select.value = state.pattern;
    updateHint();
  }
  function updateHint() {
    const info = state.config.patterns.find((p) => p.name === state.pattern);
    els.hint.replaceChildren(h("b", "", state.pattern), h("span", "", info ? info.description : ""));
  }

  // ---------- Status / banner ----------
  function showBanner(kind, text, actionLabel, action) {
    els.banner.className = "banner" + (kind === "info" ? "" : " " + kind);
    els.banner.replaceChildren();
    if (kind === "info") els.banner.append(h("span", "spinner"));
    els.banner.append(h("span", "banner-text", text));
    if (actionLabel) {
      const b = h("button", "", actionLabel); b.type = "button"; b.addEventListener("click", action);
      els.banner.append(b);
    }
    els.banner.hidden = false;
  }

  function applyStatus(s) {
    const previous = state.status.state;
    state.status = s;
    els.docDot.className = "dot " + (s.state === "ready" ? "ready" : s.state === "error" ? "error" : "loading");

    if (s.state === "ready") {
      els.docName.textContent = s.document || "Document";
      els.docMeta.textContent = s.chunks.toLocaleString() + " chunks indexed";
      if (!s.api_key_set) showBanner("warn", "OpenRouter API key is missing. Add OPENROUTER_API_KEY to your .env file and restart the app.");
      else els.banner.hidden = true;
    } else if (s.state === "error") {
      els.docName.textContent = "Not ready";
      els.docMeta.textContent = "See message above";
      showBanner("error", s.error || "The knowledge base could not be prepared.", "Retry", retryInit);
    } else {
      els.docName.textContent = "Preparing...";
      els.docMeta.textContent = "Building knowledge base";
      showBanner("info", "Preparing the knowledge base. The first start can take a few minutes while the model loads and the document is indexed - later starts are fast.");
    }
    if (previous !== s.state && !activeChat()?.messages.length) renderChat();
    updateSendState();
  }

  async function pollStatus() {
    clearTimeout(state.pollTimer);
    try {
      const res = await fetch("/api/status");
      applyStatus(await res.json());
    } catch {
      showBanner("error", "Cannot reach the server. Make sure the app is still running.");
    }
    if (state.status.state !== "ready" && state.status.state !== "error") {
      state.pollTimer = setTimeout(pollStatus, 1500);
    }
  }

  async function retryInit() {
    try { await fetch("/api/init", { method: "POST" }); } catch { /* handled by polling */ }
    pollStatus();
  }

  // ---------- UI utilities ----------
  let toastTimer;
  function toast(text) {
    els.toast.textContent = text; els.toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => els.toast.classList.remove("show"), 1800);
  }
  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); toast("Copied to clipboard"); }
    catch { toast("Copy is not available in this browser"); }
  }
  const openSidebar = () => { els.sidebar.classList.add("open"); els.overlay.classList.add("show"); };
  function closeSidebar() { els.sidebar.classList.remove("open"); els.overlay.classList.remove("show"); }

  function toggleTheme() {
    const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    writeJSON(PREFS_KEY, { ...readJSON(PREFS_KEY, {}), theme: next });
  }

  // ---------- Events ----------
  els.form.addEventListener("submit", (e) => { e.preventDefault(); submit(els.input.value); });
  els.input.addEventListener("input", () => { autosize(); updateSendState(); });
  els.input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); submit(els.input.value); }
  });
  els.select.addEventListener("change", () => {
    state.pattern = els.select.value;
    writeJSON(PREFS_KEY, { ...readJSON(PREFS_KEY, {}), pattern: state.pattern });
    updateHint();
  });
  els.newChat.addEventListener("click", newChat);
  els.menuBtn.addEventListener("click", openSidebar);
  els.overlay.addEventListener("click", closeSidebar);
  els.themeBtn.addEventListener("click", toggleTheme);
  els.clearBtn.addEventListener("click", () => {
    if (!state.chats.some((c) => c.messages.length)) { toast("Nothing to clear"); return; }
    if (!confirm("Delete all chats? This cannot be undone.")) return;
    state.chats = []; state.activeId = null; newChat();
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeSidebar(); });

  // ---------- Start ----------
  async function init() {
    const saved = readJSON(CHATS_KEY, { chats: [], activeId: null });
    state.chats = Array.isArray(saved.chats) ? saved.chats : [];
    state.activeId = saved.activeId;
    if (!activeChat()) {
      const empty = state.chats.find((c) => c.messages.length === 0);
      if (empty) state.activeId = empty.id;
      else {
        const chat = { id: uid(), title: "New chat", created: Date.now(), messages: [] };
        state.chats.unshift(chat); state.activeId = chat.id;
      }
    }
    try {
      state.config = await (await fetch("/api/config")).json();
    } catch {
      state.config = { app_name: "DocMind", default_pattern: "Zero-Shot", patterns: [{ name: "Zero-Shot", description: "" }], suggestions: [] };
      showBanner("error", "Cannot reach the server. Make sure the app is running.");
    }
    setupPatterns();
    renderAll();
    pollStatus();
    els.input.focus();
  }
  init();
})();
