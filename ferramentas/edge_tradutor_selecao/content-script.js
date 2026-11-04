let lastSelection = null;
let fallbackCooldown = false;

function isTextControl(element) {
  return element instanceof HTMLTextAreaElement || (element instanceof HTMLInputElement && /^(text|search|url|tel|email|password)$/i.test(element.type));
}

function catalogTargetFor(source) {
  if (source?.id !== "source-text") return null;
  const target = document.querySelector("#ptbr-text");
  return isTextControl(target) && !target.disabled && !target.readOnly ? target : null;
}

function readSelection() {
  const active = document.activeElement;
  if (isTextControl(active)) {
    const start = active.selectionStart ?? 0;
    const end = active.selectionEnd ?? 0;
    const text = active.value.slice(start, end);
    if (!text.trim()) return null;
    const catalogTarget = catalogTargetFor(active);
    if (catalogTarget) lastSelection = { kind: "catalog", source: active, target: catalogTarget, text };
    else if (!active.disabled && !active.readOnly) lastSelection = { kind: "field", field: active, start, end, text };
    else lastSelection = { kind: "clipboard", text };
    return { text };
  }

  const text = window.getSelection()?.toString() || "";
  if (!text.trim()) return null;
  lastSelection = { kind: "clipboard", text };
  return { text };
}

function dispatchInput(field, translation) {
  field.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: translation }));
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const helper = document.createElement("textarea");
    helper.value = text;
    helper.setAttribute("readonly", "");
    helper.style.cssText = "position:fixed;left:-9999px;top:0";
    document.documentElement.append(helper);
    helper.select();
    const copied = document.execCommand("copy");
    helper.remove();
    return copied;
  }
}

function showNotice(message, error = false) {
  let host = document.querySelector("#ptbr-selection-translator-notice");
  if (!host) {
    host = document.createElement("div");
    host.id = "ptbr-selection-translator-notice";
    host.setAttribute("role", "status");
    host.setAttribute("aria-live", "polite");
    const shadow = host.attachShadow({ mode: "open" });
    shadow.innerHTML = `<style>:host{all:initial}p{box-sizing:border-box;position:fixed;z-index:2147483647;right:20px;bottom:20px;max-width:min(430px,calc(100vw - 40px));margin:0;padding:12px 15px;border:1px solid #82b6a2;border-radius:10px;background:#10281f;color:#f2fff8;font:600 14px/1.35 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;box-shadow:0 14px 34px #0004}p.error{border-color:#ed8f8f;background:#421d22}</style><p></p>`;
    document.documentElement.append(host);
  }
  const paragraph = host.shadowRoot?.querySelector("p");
  paragraph.textContent = message;
  paragraph.className = error ? "error" : "";
  window.clearTimeout(showNotice.timeout);
  showNotice.timeout = window.setTimeout(() => host.remove(), error ? 5200 : 3000);
}

async function applyTranslation(translation) {
  const selection = lastSelection;
  if (!selection) {
    await copyText(translation);
    showNotice("Tradução copiada. Escolha o campo de destino e cole.");
    return;
  }
  if (selection.kind === "catalog") {
    if (!selection.target.isConnected) throw new Error("O campo PT-BR não está mais disponível.");
    selection.target.value = translation;
    selection.target.focus();
    selection.target.setSelectionRange(0, translation.length);
    dispatchInput(selection.target, translation);
    showNotice("Tradução aplicada ao campo PT-BR. Revise antes de salvar.");
    return;
  }
  if (selection.kind === "field") {
    const unchanged = selection.field.isConnected && selection.field.value.slice(selection.start, selection.end) === selection.text;
    if (!unchanged) throw new Error("O texto selecionado mudou; selecione-o novamente.");
    selection.field.setRangeText(translation, selection.start, selection.end, "end");
    selection.field.focus();
    dispatchInput(selection.field, translation);
    showNotice("Tradução aplicada ao campo. Revise antes de enviar.");
    return;
  }
  const copied = await copyText(translation);
  showNotice(copied ? "Tradução copiada. Escolha o campo de destino e cole." : "Não foi possível acessar a área de transferência.", !copied);
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "READ_SELECTION") sendResponse(readSelection());
  else if (message?.type === "APPLY_TRANSLATION") {
    applyTranslation(message.translation).catch((error) => showNotice(error.message || "Não foi possível aplicar a tradução.", true));
    sendResponse({ ok: true });
  } else if (message?.type === "SHOW_NOTICE") {
    showNotice(message.message, message.error);
    sendResponse({ ok: true });
  } else return undefined;
  return true;
});

document.addEventListener("keydown", (event) => {
  if (!event.ctrlKey || event.shiftKey || event.altKey || event.metaKey || event.code !== "Space" || fallbackCooldown) return;
  fallbackCooldown = true;
  window.setTimeout(() => { fallbackCooldown = false; }, 700);
  event.preventDefault();
  event.stopImmediatePropagation();
  chrome.runtime.sendMessage({ type: "TRANSLATE_ACTIVE_TAB" });
}, true);
