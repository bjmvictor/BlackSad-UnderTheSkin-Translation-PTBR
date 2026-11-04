const state = { languages: ["en", "pt_br", "es"], searchLanguages: [], targetLanguage: "en", query: "", status: "", overLimit: false, page: 1, pageSize: 25, total: 0, rows: [], selected: null, dirty: false, debounce: null, translator: null, game: null };
const $ = (selector) => document.querySelector(selector);
const languageNames = {};
let statuses = [];

function escapeHtml(text) { const node = document.createElement("span"); node.textContent = text ?? ""; return node.innerHTML; }
function truncate(text, length = 180) { return text.length > length ? `${text.slice(0, length - 1)}…` : text; }
function showToast(message, error = false) { const toast = $("#toast"); toast.textContent = message; toast.className = `toast show${error ? " error" : ""}`; window.clearTimeout(showToast.timer); showToast.timer = window.setTimeout(() => toast.className = "toast", 4600); }
function setDirty(dirty) { state.dirty = dirty; const node = $("#save-state"); node.textContent = dirty ? "Alterações não salvas" : state.selected ? "Alterações salvas" : "Selecione uma mensagem para editar"; node.classList.toggle("dirty", dirty); }
function queryString() { const params = new URLSearchParams({ languages: state.languages.join(","), search_languages: state.searchLanguages.join(","), target_language: state.targetLanguage, page: String(state.page), page_size: String(state.pageSize) }); if (state.query) params.set("query", state.query); if (state.status) params.set("status", state.status); if (state.overLimit) params.set("over_limit", "1"); return params; }

async function loadMessages() {
  $("#message-body").innerHTML = `<tr><td colspan="10" class="loading">Carregando…</td></tr>`;
  try {
    const response = await fetch(`/api/messages?${queryString()}`, { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Não foi possível consultar o catálogo.");
    state.rows = data.rows; state.total = data.total; state.languages = data.languages; state.searchLanguages = data.search_languages; state.targetLanguage = data.target_language;
    renderTable(); renderPagination();
    const resultLabel = data.total === 1 ? "texto unificado" : "textos unificados";
    $("#total-side").textContent = data.total.toLocaleString("pt-BR");
    $("#total-side-label").textContent = resultLabel;
    $("#result-summary").textContent = `${data.total.toLocaleString("pt-BR")} ${resultLabel} · ${state.languages.map((key) => languageNames[key]).join(" · ")}`;
  } catch (error) { $("#message-body").innerHTML = `<tr><td class="loading">Erro ao carregar.</td></tr>`; showToast(error.message, true); }
}
function renderTable() {
  $("#message-head").innerHTML = `<tr><th>Ocorrências</th>${state.languages.map((key) => `<th>${escapeHtml(languageNames[key])}</th>`).join("")}<th>Status</th></tr>`;
  const body = $("#message-body"); const empty = $("#empty-state");
  empty.hidden = state.rows.length !== 0;
  body.innerHTML = state.rows.map((row, index) => `<tr data-row-index="${index}" class="${state.selected?.source === row.source ? "selected" : ""}"><td><div class="row-id">${escapeHtml(row.ids.slice(0, 2).join(" · "))}${row.occurrences > 2 ? ` +${row.occurrences - 2}` : ""}</div><span class="occurrence-count">${row.occurrences} ocorrência${row.occurrences === 1 ? "" : "s"}</span></td>${state.languages.map((key) => `<td>${escapeHtml(truncate(row.values[key] || "—"))}</td>`).join("")}<td><span class="status ${escapeHtml(row.status)}">${escapeHtml(row.status || "sem status")}</span></td></tr>`).join("");
  body.querySelectorAll("tr[data-row-index]").forEach((row) => row.addEventListener("click", () => selectRow(state.rows[Number(row.dataset.rowIndex)])));
}
function pageCount() { return Math.max(1, Math.ceil(state.total / state.pageSize)); }
function renderPagination() { const pages = pageCount(); if (state.page > pages) { state.page = pages; loadMessages(); return; } $("#page-summary").textContent = `Página ${state.page} de ${pages}`; $("#previous-page").disabled = state.page <= 1; $("#next-page").disabled = state.page >= pages; const jump = $("#page-jump"); jump.max = String(pages); jump.value = String(state.page); }
function goToPage() { const jump = $("#page-jump"); const target = Number(jump.value); const pages = pageCount(); if (!Number.isInteger(target) || target < 1 || target > pages) { showToast(`Informe uma página entre 1 e ${pages}.`, true); jump.value = String(state.page); jump.focus(); jump.select(); return; } if (target !== state.page) { state.page = target; loadMessages(); } }
function selectRow(row) {
  if (state.dirty && !window.confirm("Descartar as alterações não salvas desta mensagem?")) return;
  state.selected = row; $("#editor-modal").hidden = false; document.body.classList.add("modal-open"); $("#editor-id").textContent = `${row.occurrences} ocorrência${row.occurrences === 1 ? "" : "s"} · uma tradução`; $("#editor-offset").textContent = row.ids.join(" · ");
  $("#source-text").value = row.values.en || ""; $("#ptbr-text").value = row.values.pt_br || "";
  const reference = state.languages.find((key) => key !== "en" && key !== "pt_br") || "es"; $("#reference-label").textContent = `${languageNames[reference]} · referência`; $("#reference-text").value = row.values[reference] || "";
  const statusSelect = $("#edit-status"); const mixedOption = statusSelect.querySelector("option[value='mixed']"); if (mixedOption) mixedOption.remove(); if (row.status === "mixed") statusSelect.insertAdjacentHTML("afterbegin", `<option value="mixed" disabled>mixed — escolha um status</option>`); statusSelect.value = row.status || "pending"; $("#edit-notes").value = row.notes || "";
  const warning = $("#variation-warning"); const different = row.variations.filter((language) => language !== "en"); warning.hidden = !different.length; warning.textContent = different.length ? `Há versões diferentes entre as ocorrências em: ${different.map((language) => languageNames[language]).join(", ")}. Ao salvar, o valor acima será aplicado a todas.` : "";
  updateCharacterCount(); setDirty(false); renderTable(); $("#ptbr-text").focus();
}
function closeEditor() { if (!state.selected || !state.dirty || window.confirm("Descartar alterações não salvas?")) { $("#editor-modal").hidden = true; document.body.classList.remove("modal-open"); setDirty(false); renderTable(); $("#search").focus(); } }
function updateCharacterCount() { const text = $("#ptbr-text").value; const bytes = new TextEncoder().encode(text).length; const limit = state.selected?.byte_limit; const counter = $("#character-count"); const exceeded = Number.isFinite(limit) && bytes > limit; counter.textContent = Number.isFinite(limit) ? `${text.length.toLocaleString("pt-BR")} caracteres · ${bytes.toLocaleString("pt-BR")} / ${limit.toLocaleString("pt-BR")} bytes${exceeded ? ` · excede ${bytes - limit}` : ` · sobram ${limit - bytes}`}` : `${text.length.toLocaleString("pt-BR")} caracteres · ${bytes.toLocaleString("pt-BR")} bytes · limite indisponível`; counter.classList.toggle("byte-limit-exceeded", exceeded); $("#ptbr-text").classList.toggle("byte-limit-exceeded", exceeded); }
async function saveSelected() {
  if (!state.selected || !state.dirty) return;
  const payload = { source: state.selected.source, ids: state.selected.ids, revision: state.selected.revision, pt_br: $("#ptbr-text").value, status: $("#edit-status").value, notes: $("#edit-notes").value };
  const button = $("#save-message"); button.disabled = true; button.textContent = "Salvando…";
  try {
    const response = await fetch("/api/messages", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const data = await response.json(); if (!response.ok) throw new Error(data.error || "Não foi possível salvar.");
    const bytes = new TextEncoder().encode(payload.pt_br).length; const updated = { ...state.selected, ...payload, values: { ...state.selected.values, pt_br: payload.pt_br }, pt_br_bytes: bytes, over_limit: Number.isFinite(state.selected.byte_limit) && bytes > state.selected.byte_limit, revision: data.revision }; state.selected = updated; const index = state.rows.findIndex((row) => row.source === updated.source); if (index >= 0) state.rows[index] = updated; const table = $(".table-wrap"); const scrollTop = table.scrollTop; renderTable(); table.scrollTop = scrollTop; setDirty(false); showToast(`${data.message} Backup: ${data.backup}`);
  } catch (error) { showToast(error.message, true); } finally { button.disabled = false; button.textContent = "Salvar no CSV"; }
}
async function translateSelected() {
  if (!state.selected || !state.translator?.configured) return;
  const field = $("#ptbr-text");
  if (field.value.trim() && !window.confirm("Substituir o texto PT-BR atual por uma tradução automática? Você poderá revisar antes de salvar.")) return;
  const button = $("#translate-message"); button.disabled = true; button.textContent = "Traduzindo…";
  try {
    const response = await fetch("/api/translate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: $("#source-text").value }) });
    const data = await response.json(); if (!response.ok) throw new Error(data.error || "Não foi possível traduzir.");
    field.value = data.translation; updateCharacterCount(); setDirty(true); showToast("Rascunho automático inserido. Revise antes de salvar."); field.focus();
  } catch (error) { showToast(error.message, true); } finally { button.disabled = false; button.textContent = "Traduzir do inglês"; }
}
function scheduleSearch() { window.clearTimeout(state.debounce); state.debounce = window.setTimeout(() => { state.query = $("#search").value.trim(); state.page = 1; loadMessages(); }, 220); }
async function gameRequest(path, payload = {}) { const response = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); const data = await response.json(); if (!response.ok) throw new Error(data.error || "Não foi possível concluir a operação no jogo."); return data; }
function targetLanguageLabel() { return state.targetLanguage === "es" ? "Español" : "English"; }
function renderGame(game) {
  if (!game) return;
  state.game = game; const path = $("#game-path"); if (document.activeElement !== path) path.value = game.selected || "";
  const status = $("#game-status"); status.className = `game-status${game.valid ? " ready" : " error"}`; status.textContent = game.valid ? "Instalação validada. A build será conferida antes da cópia." : game.detected?.length ? "Instalação detectada. Confirme a pasta antes de aplicar." : "Não encontrei a instalação. Informe ou escolha a pasta manualmente.";
  const backups = $("#game-backups"); backups.innerHTML = game.backups?.length ? game.backups.map((backup) => `<option value="${escapeHtml(backup.id)}">${escapeHtml(backup.created_at)} · ${escapeHtml(backup.reason.replaceAll("_", " "))}</option>`).join("") : `<option value="">Nenhum backup disponível</option>`; backups.disabled = !game.backups?.length;
  $("#restore-backup").disabled = !game.valid || !game.backups?.length; $("#apply-game").disabled = !game.valid || !game.can_apply; $("#apply-game").title = game.can_apply ? "Gera o bundle a partir do CSV atual pelo UABEA, cria backup e aplica no jogo." : "Empacotador UABEA indisponível no projeto."; $("#restore-original").disabled = !game.valid || !game.can_build;
}
async function setGamePath() { const game = await gameRequest("/api/game/path", { path: $("#game-path").value.trim() }); renderGame(game); showToast("Pasta do jogo validada."); }
async function detectGame() { const game = await gameRequest("/api/game/detect"); renderGame(game); showToast(game.valid ? "Instalação detectada." : "Não encontrei o jogo automaticamente.", !game.valid); }
async function browseGame() { const game = await gameRequest("/api/game/browse"); renderGame(game); showToast("Pasta do jogo validada."); }
async function gameAction(action) {
  const path = $("#game-path").value.trim(); const labels = { apply: `gerar o bundle PT-BR no slot ${targetLanguageLabel()} e aplicar`, restore_backup: "restaurar o backup escolhido", restore_original: "restaurar o arquivo original" }; if (!path) { showToast("Informe a pasta que contém Blacksad.exe.", true); return; }
  if (!window.confirm(`Confirma ${labels[action]}?\n\nDestino: ${path}\n\nNo jogo, selecione: ${targetLanguageLabel()}.\n\nO jogo deve estar fechado. O arquivo atual será salvo em um backup antes da troca.`)) return;
  const buttons = [...document.querySelectorAll(".game-tools button")]; const actionButton = action === "apply" ? $("#apply-game") : action === "restore_backup" ? $("#restore-backup") : $("#restore-original"); const originalLabel = actionButton.textContent; if (action === "apply") actionButton.textContent = "Empacotando PT-BR pelo UABEA…"; buttons.forEach((button) => button.disabled = true);
  try { const data = await gameRequest("/api/game/action", { action, path, backup_id: $("#game-backups").value, target_language: state.targetLanguage, confirmed: true }); renderGame(data.game); showToast(`${data.message}. Backup criado: ${data.backup}`); } catch (error) { showToast(error.message, true); } finally { actionButton.textContent = originalLabel; renderGame(state.game); }
}
async function init() {
  const response = await fetch("/api/config"); const config = await response.json(); Object.assign(languageNames, config.languages); statuses = config.statuses; state.translator = config.translator; $("#catalog-path").textContent = config.catalog; renderGame(config.game);
  const languageOptions = (selected) => Object.entries(languageNames).map(([key, name]) => `<label class="language-option"><input type="checkbox" value="${key}" ${selected.includes(key) ? "checked" : ""}><span>${escapeHtml(name)}</span></label>`).join("");
  state.searchLanguages = Object.keys(languageNames); $("#search-language-filter").innerHTML = `<legend>Pesquisar em</legend>${languageOptions(state.searchLanguages)}`; $("#language-filter").innerHTML = `<legend>Colunas exibidas</legend>${languageOptions(state.languages)}`;
  $("#status-filter").insertAdjacentHTML("beforeend", statuses.map((status) => `<option value="${status}">${status}</option>`).join("")); $("#edit-status").innerHTML = statuses.map((status) => `<option value="${status}">${status}</option>`).join("");
  $("#language-filter").addEventListener("change", () => { const checked = [...$("#language-filter").querySelectorAll("input:checked")].map((input) => input.value); if (!checked.length) { showToast("Escolha pelo menos um idioma para exibir.", true); $("#language-filter input[value='en']").checked = true; return; } state.languages = checked; state.page = 1; loadMessages(); });
  $("#search-language-filter").addEventListener("change", () => { const checked = [...$("#search-language-filter").querySelectorAll("input:checked")].map((input) => input.value); if (!checked.length) { showToast("Escolha pelo menos um idioma para pesquisar.", true); $("#search-language-filter input[value='pt_br']").checked = true; return; } state.searchLanguages = checked; state.page = 1; loadMessages(); });
  $("#target-language").addEventListener("change", (event) => { state.targetLanguage = event.target.value; state.page = 1; loadMessages(); });
  $("#search").addEventListener("input", scheduleSearch); $("#status-filter").addEventListener("change", (event) => { state.status = event.target.value; state.page = 1; loadMessages(); }); $("#over-limit-filter").addEventListener("change", (event) => { state.overLimit = event.target.checked; state.page = 1; loadMessages(); }); $("#page-size").addEventListener("change", (event) => { state.pageSize = Number(event.target.value); state.page = 1; loadMessages(); });
  $("#refresh").addEventListener("click", () => { if (!state.dirty || window.confirm("Descartar alterações não salvas e recarregar?")) { state.selected = null; $("#editor-modal").hidden = true; document.body.classList.remove("modal-open"); setDirty(false); loadMessages(); } }); $("#reset-filters").addEventListener("click", () => { $("#search").value = ""; $("#status-filter").value = ""; $("#over-limit-filter").checked = false; state.query = ""; state.status = ""; state.overLimit = false; state.searchLanguages = Object.keys(languageNames); document.querySelectorAll("#search-language-filter input").forEach((input) => input.checked = true); state.page = 1; loadMessages(); });
  $("#previous-page").addEventListener("click", () => { state.page--; loadMessages(); }); $("#next-page").addEventListener("click", () => { state.page++; loadMessages(); }); $("#go-to-page").addEventListener("click", goToPage); $("#page-jump").addEventListener("keydown", (event) => { if (event.key === "Enter") { event.preventDefault(); goToPage(); } }); $("#close-editor").addEventListener("click", closeEditor); $("#editor-modal").addEventListener("click", (event) => { if (event.target === event.currentTarget) closeEditor(); });
  $("#use-game-path").addEventListener("click", () => setGamePath().catch((error) => showToast(error.message, true))); $("#detect-game").addEventListener("click", () => detectGame().catch((error) => showToast(error.message, true))); $("#browse-game").addEventListener("click", () => browseGame().catch((error) => showToast(error.message, true))); $("#apply-game").addEventListener("click", () => gameAction("apply")); $("#restore-backup").addEventListener("click", () => gameAction("restore_backup")); $("#restore-original").addEventListener("click", () => gameAction("restore_original"));
  const translateButton = $("#translate-message"); translateButton.disabled = !state.translator?.configured; translateButton.title = state.translator?.configured ? "Gera um rascunho PT-BR local a partir do texto em inglês" : "Instale o pacote English -> Portuguese do Argos Translate e reinicie o editor"; $("#translator-note").textContent = state.translator?.configured ? "Argos Translate local gera um rascunho revisável, sem API externa." : "Argos Translate local: pacote English -> Portuguese não encontrado.";
  ["#ptbr-text", "#edit-status", "#edit-notes"].forEach((selector) => $(selector).addEventListener("input", () => { updateCharacterCount(); setDirty(true); })); translateButton.addEventListener("click", translateSelected); $("#save-message").addEventListener("click", saveSelected); window.addEventListener("keydown", (event) => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s" && state.selected) { event.preventDefault(); saveSelected(); } else if (event.key === "Escape" && !$("#editor-modal").hidden) { closeEditor(); } });
  await loadMessages();
}
init().catch((error) => showToast(error.message, true));
