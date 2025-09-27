// app.js - handle file UI, upload to server, show progress and result

const fileInput = document.getElementById('fileinput');
const dropzone = document.getElementById('dropzone');
const preview = document.getElementById('preview');
const uploadBtn = document.getElementById('uploadBtn');
const statusEl = document.getElementById('status');
const outputEl = document.getElementById('output');
const saveBtn = document.getElementById('saveBtn');
const downloadLink = document.getElementById('downloadLink');
const useAi = document.getElementById('useAi');

let currentFile = null;

dropzone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', ev => {
  const f = ev.target.files[0];
  if (!f) return;
  showPreview(f);
});

dropzone.addEventListener('dragover', ev => {
  ev.preventDefault();
  dropzone.style.borderColor = '#214';
});
dropzone.addEventListener('dragleave', ev => {
  dropzone.style.borderColor = '';
});
dropzone.addEventListener('drop', ev => {
  ev.preventDefault();
  dropzone.style.borderColor = '';
  const f = ev.dataTransfer.files[0];
  if (!f) return;
  showPreview(f);
});

function showPreview(file) {
  currentFile = file;
  const url = URL.createObjectURL(file);
  preview.src = url;
  preview.style.display = 'block';
  document.querySelector('.drop-hint').style.display = 'none';
  statusEl.textContent = `Ready - ${file.name}`;
}

uploadBtn.addEventListener('click', () => {
  if (!currentFile) {
    statusEl.textContent = 'No image selected';
    return;
  }
  processFile(currentFile, useAi.checked);
});

// send file to backend upload endpoint
async function processFile(file, aiFallback) {
  statusEl.textContent = 'Uploading...';
  outputEl.value = '';
  const form = new FormData();
  form.append('image', file);
  form.append('use_ai', aiFallback ? '1' : '0');

  try {
    const resp = await fetch('/api/upload', {
      method: 'POST',
      body: form
    });

    if (!resp.ok) {
      const txt = await resp.text();
      statusEl.textContent = 'Server error';
      outputEl.value = txt || 'Error';
      return;
    }

    // stream response if server sends incremental progress - fallback to final json
    const data = await resp.json();
    statusEl.textContent = data.status || 'Done';
    outputEl.value = data.result || '';
    statusEl.textContent = 'Completed';
  } catch (err) {
    statusEl.textContent = 'Network or server error';
    outputEl.value = String(err);
  }
}

saveBtn.addEventListener('click', () => {
  const txt = outputEl.value;
  if (!txt) {
    statusEl.textContent = 'Nothing to save';
    return;
  }
  const blob = new Blob([txt], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  downloadLink.href = url;
  downloadLink.download = 'output.txt';
  downloadLink.click();
  URL.revokeObjectURL(url);
});