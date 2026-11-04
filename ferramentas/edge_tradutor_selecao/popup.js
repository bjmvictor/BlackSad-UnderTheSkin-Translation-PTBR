const button = document.querySelector("#translate");
const status = document.querySelector("#status");

function setStatus(message, error = false) {
  status.textContent = message;
  status.classList.toggle("error", error);
}

async function translateActiveTab() {
  button.disabled = true;
  setStatus("Traduzindo…");
  try {
    const result = await chrome.runtime.sendMessage({ type: "TRANSLATE_ACTIVE_TAB" });
    if (!result?.ok) throw new Error(result?.error || "Não foi possível traduzir a seleção.");
    setStatus("Tradução aplicada. Revise antes de salvar.");
  } catch (error) {
    setStatus(error.message || "Não foi possível traduzir a seleção.", true);
  } finally {
    button.disabled = false;
  }
}

if (globalThis.chrome?.runtime?.sendMessage) {
  button.addEventListener("click", translateActiveTab);
} else {
  button.disabled = true;
  setStatus("Prévia da interface — carregue a extensão no Edge para usar.");
}
