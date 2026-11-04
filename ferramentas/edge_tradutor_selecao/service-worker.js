const GOOGLE_TRANSLATE_ENDPOINT = "https://translate.googleapis.com/translate_a/single";
const translatingTabs = new Set();

async function notify(tabId, message, error = false) {
  try {
    await chrome.tabs.sendMessage(tabId, { type: "SHOW_NOTICE", message, error });
  } catch {
    // A página pode ter sido fechada ou não aceitar scripts de extensão.
  }
}

async function selectedText(tabId) {
  try {
    return await chrome.tabs.sendMessage(tabId, { type: "READ_SELECTION" });
  } catch {
    throw new Error("Esta página não permite que a extensão leia a seleção.");
  }
}

function extractTranslation(payload) {
  const parts = payload?.[0];
  if (!Array.isArray(parts)) throw new Error("O serviço devolveu uma resposta inesperada.");
  const translation = parts.map((part) => part?.[0] || "").join("").trim();
  if (!translation) throw new Error("O serviço não devolveu uma tradução.");
  return translation;
}

async function translate(text) {
  const parameters = new URLSearchParams({ client: "gtx", sl: "auto", tl: "pt", dt: "t", q: text });
  const response = await fetch(`${GOOGLE_TRANSLATE_ENDPOINT}?${parameters}`, {
    cache: "no-store",
    credentials: "omit"
  });
  if (!response.ok) throw new Error(`O serviço de tradução respondeu com erro ${response.status}.`);
  return extractTranslation(await response.json());
}

async function translateInTab(tabId) {
  if (translatingTabs.has(tabId)) return;
  translatingTabs.add(tabId);
  try {
    const selection = await selectedText(tabId);
    if (!selection?.text?.trim()) {
      await notify(tabId, "Selecione um texto antes de traduzir.", true);
      return;
    }
    await notify(tabId, "Traduzindo…");
    const translation = await translate(selection.text);
    await chrome.tabs.sendMessage(tabId, { type: "APPLY_TRANSLATION", selection, translation });
  } catch (error) {
    await notify(tabId, error.message || "Não foi possível traduzir a seleção.", true);
    throw error;
  } finally {
    translatingTabs.delete(tabId);
  }
}

async function translateInActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) throw new Error("Não foi encontrada uma aba ativa.");
  await translateInTab(tab.id);
}

chrome.commands.onCommand.addListener((command) => {
  if (command === "translate-selection") translateInActiveTab().catch(() => undefined);
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "TRANSLATE_ACTIVE_TAB") return undefined;
  translateInActiveTab().then(
    () => sendResponse({ ok: true }),
    (error) => sendResponse({ ok: false, error: error.message || "Falha ao traduzir." })
  );
  return true;
});
