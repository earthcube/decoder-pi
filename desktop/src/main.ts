import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

type ContentBlock = { type?: string; text?: string; thinking?: string };

type PiEvent = {
  type?: string;
  id?: string;
  method?: string;
  command?: string;
  success?: boolean;
  error?: string;
  message?: string | PiMessage;
  notifyType?: string;
  title?: string;
  options?: string[];
  placeholder?: string;
  prefill?: string;
  statusText?: string;
  toolCallId?: string;
  toolName?: string;
  args?: Record<string, unknown>;
  partialResult?: { content?: ContentBlock[] };
  result?: { content?: ContentBlock[] };
  isError?: boolean;
  assistantMessageEvent?: { type?: string; delta?: string };
  data?: {
    model?: { provider?: string; id?: string; name?: string };
    thinkingLevel?: string;
  };
};

type PiMessage = {
  role?: string;
  content?: string | ContentBlock[];
  stopReason?: string;
};

type Artifact = {
  name: string;
  bytes: number;
  modifiedMs: number;
  kind: string;
};

type ArtifactBody = {
  name: string;
  kind: string;
  mime: string;
  truncated: boolean;
  text?: string;
  base64?: string;
};

type DialogRequest = {
  id: string;
  method: "confirm" | "select" | "input" | "editor";
  title?: string;
  message?: string;
  options?: string[];
  placeholder?: string;
  prefill?: string;
};

const chat = document.querySelector("#chat") as HTMLElement;
const promptEl = document.querySelector("#prompt") as HTMLTextAreaElement;
const sendBtn = document.querySelector("#send") as HTMLButtonElement;
const stopBtn = document.querySelector("#stop") as HTMLButtonElement;
const statusEl = document.querySelector("#status") as HTMLElement;
const subtitle = document.querySelector("#subtitle") as HTMLElement;
const modelEl = document.querySelector("#model") as HTMLElement;
const thinkingEl = document.querySelector("#thinking") as HTMLElement;
const stderrEl = document.querySelector("#stderr") as HTMLElement;
const artifactList = document.querySelector("#artifact-list") as HTMLElement;
const preview = document.querySelector("#preview") as HTMLElement;
const dialog = document.querySelector("#dialog") as HTMLElement;
const dialogForm = document.querySelector("#dialog-form") as HTMLFormElement;
const dialogTitle = document.querySelector("#dialog-title") as HTMLElement;
const dialogMessage = document.querySelector("#dialog-message") as HTMLElement;
const dialogBody = document.querySelector("#dialog-body") as HTMLElement;
const dialogOk = document.querySelector("#dialog-ok") as HTMLButtonElement;
const dialogCancel = document.querySelector("#dialog-cancel") as HTMLButtonElement;

let busy = false;
let thinkingLevel = "";
let assistantBody: HTMLElement | null = null;
let assistantText = "";
const toolCards = new Map<string, HTMLElement>();
const toolText = new Map<string, string>();
const dialogs: DialogRequest[] = [];
let openDialog: DialogRequest | null = null;
const stderrLines: string[] = [];

function stripAnsi(value: string): string {
  return value.replace(/\u001b\[[0-9;]*m/g, "");
}

function setStatus(text: string, tone: "info" | "warn" | "error" = "info") {
  statusEl.textContent = stripAnsi(text);
  statusEl.className = tone === "info" ? "" : tone;
}

function renderActivity() {
  thinkingEl.textContent = busy && thinkingLevel ? `${thinkingLevel} · working` : busy ? "working" : thinkingLevel;
}

function setBusy(next: boolean) {
  busy = next;
  sendBtn.disabled = next || openDialog !== null;
  stopBtn.disabled = !next;
  promptEl.disabled = next;
  renderActivity();
}

function scrollChat() {
  chat.scrollTop = chat.scrollHeight;
}

function addBubble(role: "user" | "assistant", text: string): HTMLElement {
  const bubble = document.createElement("article");
  bubble.className = `bubble ${role}`;
  const who = document.createElement("div");
  who.className = "who";
  who.textContent = role === "user" ? "You" : "Decoder";
  const body = document.createElement("div");
  body.className = "body";
  body.textContent = text;
  bubble.append(who, body);
  chat.append(bubble);
  scrollChat();
  return body;
}

function contentText(blocks: ContentBlock[] | undefined): string {
  if (!blocks) return "";
  return blocks
    .map((block) => {
      if (block.type === "text" && block.text) return block.text;
      if (block.type === "image") return "[image]";
      return "";
    })
    .join("");
}

function mergeToolText(previous: string, next: string): string {
  if (!next) return previous;
  if (!previous || next.startsWith(previous)) return next;
  if (previous.startsWith(next)) return previous;
  return previous + next;
}

function toolLabel(name: string | undefined, args: Record<string, unknown> | undefined): string {
  const command = args && typeof args.command === "string" ? args.command : "";
  if (name === "bash" && command) return command;
  if (!args) return name ?? "tool";
  const dumped = JSON.stringify(args);
  return `${name ?? "tool"} ${dumped.length > 240 ? `${dumped.slice(0, 240)}…` : dumped}`;
}

function ensureTool(id: string, label: string): HTMLElement {
  let card = toolCards.get(id);
  if (!card) {
    card = document.createElement("article");
    card.className = "tool";
    const name = document.createElement("div");
    name.className = "tool-name";
    const pre = document.createElement("pre");
    card.append(name, pre);
    toolCards.set(id, card);
    chat.append(card);
  }
  const name = card.querySelector(".tool-name");
  if (name) name.textContent = label;
  return card;
}

function blocksFromMessage(message: PiMessage | undefined): string {
  if (!message) return "";
  if (typeof message.content === "string") return message.content;
  if (!Array.isArray(message.content)) return "";
  return message.content
    .filter((block) => block.type === "text" && typeof block.text === "string")
    .map((block) => block.text ?? "")
    .join("");
}

function thinkingFromMessage(message: PiMessage | undefined): string {
  if (!message || !Array.isArray(message.content)) return "";
  return message.content
    .filter((block) => block.type === "thinking")
    .map((block) => block.thinking || block.text || "")
    .join("");
}

async function sendPi(message: unknown) {
  await invoke("pi_send", { message });
}

async function refreshArtifacts() {
  const items = await invoke<Artifact[]>("list_artifacts");
  artifactList.replaceChildren();
  if (items.length === 0) {
    const empty = document.createElement("li");
    empty.textContent = "No previewable files in runs/ yet.";
    artifactList.append(empty);
    return;
  }
  for (const item of items) {
    const li = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.name = item.name;
    const title = document.createElement("div");
    title.textContent = item.name;
    const meta = document.createElement("div");
    meta.className = "artifact-meta";
    meta.textContent = `${item.kind} · ${formatBytes(item.bytes)}`;
    button.append(title, meta);
    button.addEventListener("click", () => void showArtifact(item.name, button));
    li.append(button);
    artifactList.append(li);
  }
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

async function showArtifact(name: string, button: HTMLButtonElement) {
  for (const node of artifactList.querySelectorAll("button")) {
    node.removeAttribute("aria-current");
  }
  button.setAttribute("aria-current", "true");
  const body = await invoke<ArtifactBody>("read_artifact", { relative: name });
  preview.hidden = false;
  preview.replaceChildren();
  const head = document.createElement("div");
  head.className = "preview-head";
  const label = document.createElement("strong");
  label.textContent = body.name;
  const close = document.createElement("button");
  close.type = "button";
  close.textContent = "Close";
  close.addEventListener("click", () => {
    preview.hidden = true;
    preview.replaceChildren();
    button.removeAttribute("aria-current");
  });
  head.append(label, close);
  preview.append(head);
  if (body.truncated) {
    const note = document.createElement("p");
    note.className = "artifact-meta";
    note.textContent = "Preview truncated.";
    preview.append(note);
  }
  if (body.base64) {
    const img = document.createElement("img");
    img.alt = body.name;
    img.src = `data:${body.mime};base64,${body.base64}`;
    preview.append(img);
    return;
  }
  if (body.kind === "html" && body.text && !body.truncated) {
    const frame = document.createElement("iframe");
    frame.sandbox = "";
    frame.srcdoc = body.text;
    frame.title = body.name;
    preview.append(frame);
    return;
  }
  const pre = document.createElement("pre");
  pre.textContent = body.text ?? "";
  preview.append(pre);
}

function showNextDialog() {
  if (openDialog || dialogs.length === 0) return;
  openDialog = dialogs.shift() ?? null;
  if (!openDialog) return;
  dialog.hidden = false;
  dialogTitle.textContent = openDialog.title || "Pi needs a choice";
  dialogMessage.textContent = openDialog.message || "";
  dialogBody.replaceChildren();
  dialogOk.hidden = openDialog.method === "select" || openDialog.method === "confirm";
  if (openDialog.method === "confirm") {
    dialogOk.hidden = false;
    dialogOk.textContent = "Yes";
    dialogCancel.textContent = "No";
  } else if (openDialog.method === "select") {
    dialogCancel.textContent = "Cancel";
    for (const option of openDialog.options ?? []) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "choice";
      button.textContent = option;
      button.addEventListener("click", () => {
        void answerDialog({ type: "extension_ui_response", id: openDialog?.id, value: option });
      });
      dialogBody.append(button);
    }
  } else if (openDialog.method === "input") {
    dialogCancel.textContent = "Cancel";
    dialogOk.textContent = "OK";
    const input = document.createElement("input");
    input.type = "text";
    input.id = "dialog-input";
    input.placeholder = openDialog.placeholder || "";
    input.value = openDialog.prefill || "";
    dialogBody.append(input);
    input.focus();
  } else {
    dialogCancel.textContent = "Cancel";
    dialogOk.textContent = "OK";
    const area = document.createElement("textarea");
    area.id = "dialog-input";
    area.rows = 8;
    area.value = openDialog.prefill || "";
    dialogBody.append(area);
    area.focus();
  }
}

async function answerDialog(payload: Record<string, unknown>) {
  const current = openDialog;
  openDialog = null;
  dialog.hidden = true;
  dialogOk.textContent = "OK";
  if (current) await sendPi(payload);
  showNextDialog();
}

function onPi(event: PiEvent) {
  if (event.type === "extension_ui_request") {
    const method = event.method;
    if (method === "notify") {
      const tone = event.notifyType === "error" ? "error" : event.notifyType === "warning" ? "warn" : "info";
      setStatus(event.message && typeof event.message === "string" ? event.message : "notice", tone);
      return;
    }
    if (method === "setStatus") {
      if (typeof event.statusText === "string" && event.statusText.length > 0) {
        setStatus(event.statusText);
      }
      return;
    }
    if (method === "setTitle" && typeof event.title === "string") {
      document.title = event.title;
      return;
    }
    if ((method === "confirm" || method === "select" || method === "input" || method === "editor") && event.id) {
      dialogs.push({
        id: event.id,
        method,
        title: event.title,
        message: typeof event.message === "string" ? event.message : undefined,
        options: event.options,
        placeholder: event.placeholder,
        prefill: event.prefill,
      });
      showNextDialog();
    }
    return;
  }

  if (event.type === "response" && event.command === "get_state" && event.success && event.data) {
    const model = event.data.model;
    const label = model?.name || model?.id || "model unavailable";
    const provider = model?.provider ? `${model.provider} · ` : "";
    modelEl.textContent = `${provider}${label}`;
    if (event.data.thinkingLevel) thinkingLevel = event.data.thinkingLevel;
    renderActivity();
    return;
  }

  if (event.type === "response" && event.command === "prompt" && event.success === false) {
    setBusy(false);
    setStatus(event.error || "Pi rejected the prompt", "error");
    return;
  }

  if (event.type === "message_start") {
    const message = event.message as PiMessage | undefined;
    if (message?.role === "assistant") {
      assistantText = "";
      assistantBody = addBubble("assistant", "");
    }
    return;
  }

  if (event.type === "message_update" && assistantBody) {
    const update = event.assistantMessageEvent;
    if (update?.type === "text_delta" && update.delta) {
      assistantText += update.delta;
      assistantBody.textContent = assistantText;
      scrollChat();
    }
    return;
  }

  if (event.type === "message_end") {
    const message = event.message as PiMessage | undefined;
    if (message?.role === "assistant" && assistantBody) {
      const finalText = blocksFromMessage(message);
      if (finalText) {
        assistantText = finalText;
        assistantBody.textContent = finalText;
      }
      const thinking = thinkingFromMessage(message);
      if (thinking) {
        const details = document.createElement("details");
        details.className = "thinking";
        const summary = document.createElement("summary");
        summary.textContent = "Thinking";
        const pre = document.createElement("pre");
        pre.textContent = thinking;
        details.append(summary, pre);
        assistantBody.before(details);
      }
      assistantBody = null;
      scrollChat();
    }
    return;
  }

  if (event.type === "tool_execution_start" && event.toolCallId) {
    toolText.set(event.toolCallId, "");
    ensureTool(event.toolCallId, toolLabel(event.toolName, event.args));
    scrollChat();
    return;
  }

  if ((event.type === "tool_execution_update" || event.type === "tool_execution_end") && event.toolCallId) {
    const card = ensureTool(event.toolCallId, toolLabel(event.toolName, event.args));
    const incoming = contentText(event.type === "tool_execution_end" ? event.result?.content : event.partialResult?.content);
    const merged = event.type === "tool_execution_end" && event.result
      ? incoming || toolText.get(event.toolCallId) || ""
      : mergeToolText(toolText.get(event.toolCallId) || "", incoming);
    toolText.set(event.toolCallId, merged);
    const pre = card.querySelector("pre");
    if (pre) pre.textContent = merged;
    if (event.isError) card.classList.add("error");
    if (event.type === "tool_execution_end") void refreshArtifacts().catch((err: unknown) => setStatus(String(err), "error"));
    scrollChat();
    return;
  }

  if (event.type === "agent_settled") {
    setBusy(false);
    promptEl.focus();
  }
}

promptEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    document.querySelector<HTMLFormElement>("#composer")?.requestSubmit();
  }
});

document.querySelector("#composer")?.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = promptEl.value.trim();
  if (!text || busy || openDialog) return;
  promptEl.value = "";
  addBubble("user", text);
  setBusy(true);
  void sendPi({ id: crypto.randomUUID(), type: "prompt", message: text }).catch((err: unknown) => {
    setBusy(false);
    setStatus(String(err), "error");
  });
});

stopBtn.addEventListener("click", () => {
  void sendPi({ id: crypto.randomUUID(), type: "abort" }).catch((err: unknown) => setStatus(String(err), "error"));
});

document.querySelector("#refresh")?.addEventListener("click", () => {
  void refreshArtifacts().catch((err: unknown) => setStatus(String(err), "error"));
});

const workspace = document.querySelector("#workspace") as HTMLElement;
const splitter = document.querySelector("#splitter") as HTMLElement;
const artifacts = document.querySelector("#artifacts") as HTMLElement;
const FILES_WIDTH_KEY = "decoder.filesWidth";
const FILES_MIN = 200;
const CHAT_MIN = 280;

function filesMax(): number {
  return Math.max(FILES_MIN, workspace.clientWidth - CHAT_MIN - splitter.offsetWidth);
}

function setFilesWidth(px: number): number {
  const width = Math.round(Math.min(filesMax(), Math.max(FILES_MIN, px)));
  workspace.style.setProperty("--files-width", `${width}px`);
  splitter.setAttribute("aria-valuemin", String(FILES_MIN));
  splitter.setAttribute("aria-valuemax", String(Math.round(filesMax())));
  splitter.setAttribute("aria-valuenow", String(width));
  return width;
}

function rememberFilesWidth(width: number) {
  localStorage.setItem(FILES_WIDTH_KEY, String(width));
}

const savedFilesWidth = Number(localStorage.getItem(FILES_WIDTH_KEY));
if (Number.isFinite(savedFilesWidth) && savedFilesWidth > 0) setFilesWidth(savedFilesWidth);

splitter.addEventListener("pointerdown", (event) => {
  if (event.button !== 0) return;
  event.preventDefault();
  const startX = event.clientX;
  const startWidth = artifacts.getBoundingClientRect().width;
  splitter.setPointerCapture(event.pointerId);
  splitter.classList.add("dragging");
  document.body.classList.add("resizing");

  const move = (ev: PointerEvent) => {
    setFilesWidth(startWidth - (ev.clientX - startX));
  };
  const finish = (ev: PointerEvent) => {
    if (splitter.hasPointerCapture(ev.pointerId)) splitter.releasePointerCapture(ev.pointerId);
    splitter.classList.remove("dragging");
    document.body.classList.remove("resizing");
    splitter.removeEventListener("pointermove", move);
    splitter.removeEventListener("pointerup", finish);
    splitter.removeEventListener("pointercancel", finish);
    rememberFilesWidth(Math.round(artifacts.getBoundingClientRect().width));
  };
  splitter.addEventListener("pointermove", move);
  splitter.addEventListener("pointerup", finish);
  splitter.addEventListener("pointercancel", finish);
});

splitter.addEventListener("keydown", (event) => {
  if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
  event.preventDefault();
  const current = artifacts.getBoundingClientRect().width;
  const delta = event.key === "ArrowLeft" ? 24 : -24;
  rememberFilesWidth(setFilesWidth(current + delta));
});

window.addEventListener("resize", () => {
  if (getComputedStyle(splitter).display === "none") return;
  setFilesWidth(artifacts.getBoundingClientRect().width);
});

dialogForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!openDialog) return;
  if (openDialog.method === "confirm") {
    void answerDialog({ type: "extension_ui_response", id: openDialog.id, confirmed: true });
    return;
  }
  const field = document.querySelector("#dialog-input") as HTMLInputElement | HTMLTextAreaElement | null;
  void answerDialog({ type: "extension_ui_response", id: openDialog.id, value: field?.value ?? "" });
});

dialogCancel.addEventListener("click", () => {
  if (!openDialog) return;
  if (openDialog.method === "confirm") {
    void answerDialog({ type: "extension_ui_response", id: openDialog.id, confirmed: false });
    return;
  }
  void answerDialog({ type: "extension_ui_response", id: openDialog.id, cancelled: true });
});

window.addEventListener("DOMContentLoaded", () => {
  void (async () => {
    await listen<PiEvent>("pi-event", (event) => onPi(event.payload));
    await listen<string>("pi-stderr", (event) => {
      stderrLines.push(event.payload);
      stderrEl.textContent = stderrLines.slice(-40).join("\n");
    });
    await listen<string>("pi-exit", (event) => {
      setBusy(false);
      setStatus(event.payload, "error");
    });
    try {
      const info = await invoke<{ root?: string; running: boolean; error?: string }>("start_harness");
      subtitle.textContent = info.root ? info.root : info.error || "Harness did not start";
      if (info.error) setStatus(info.error, "error");
      await sendPi({ id: "boot-state", type: "get_state" });
      await refreshArtifacts();
    } catch (err) {
      subtitle.textContent = "Harness did not start";
      setStatus(String(err), "error");
    }
    promptEl.focus();
  })();
});
