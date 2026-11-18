const dialog = document.getElementById("import-dialog");
const progress = document.getElementById("progress-dialog");
const input = document.getElementById("import-files");
const list = document.getElementById("file-list");
const message = document.getElementById("import-message");
const submit = document.getElementById("run-import");
let selection = [];

function renderSelection() {
  list.replaceChildren();
  selection.forEach((file, index) => {
    const row = document.createElement("li");
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Remove";
    remove.className = "button quiet";
    remove.setAttribute("aria-label", "Remove " + file.name);
    remove.onclick = () => {
      selection.splice(index, 1);
      renderSelection();
    };
    row.append(document.createTextNode(file.name), remove);
    list.append(row);
  });
  submit.disabled = !selection.length;
  message.textContent = selection.length ? selection.length + " selected" : "";
}

document.querySelectorAll("[data-import]").forEach(button => {
  button.onclick = () => {
    selection = [];
    renderSelection();
    dialog.showModal();
    input.click();
  };
});
document.getElementById("choose-files").onclick = () => input.click();
document.getElementById("cancel-import").onclick = () => dialog.close();
input.onchange = () => {
  selection.push(...input.files);
  input.value = "";
  renderSelection();
};
progress.oncancel = event => event.preventDefault();
submit.onclick = async () => {
  const form = new FormData();
  selection.forEach(file => form.append("documents", file));
  dialog.close();
  document.getElementById("progress-title").textContent = "Indexing your documents…";
  document.getElementById("progress-detail").textContent = "Spark is building the positional index and calculating document weights.";
  progress.showModal();
  try {
    const response = await fetch("api/import", {method: "POST", body: form});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Import failed.");
    document.getElementById("progress-title").textContent = "Collection ready";
    document.getElementById("progress-detail").textContent = "Opening your results…";
    await new Promise(resolve => setTimeout(resolve, 2000));
    location.replace(data.url);
  } catch (error) {
    progress.close();
    dialog.showModal();
    message.textContent = error.message;
  }
};
