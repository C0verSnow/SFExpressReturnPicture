function readAddress() {
  const text = id => document.getElementById(id).textContent;
  return {merchant: text('merchant'), phone: text('phone'),
    lines: [0, 1, 2].map(i => text(`line${i}`))};
}
function download(name, content, type) {
  const url = URL.createObjectURL(new Blob([content], {type}));
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
document.getElementById('save').onclick = () => {
  // Save the current text, with the embedded font and editing controls intact.
  const snapshot = document.documentElement.cloneNode(true);
  snapshot.querySelector('#status').textContent = '';
  download('address-edited.html', '<!doctype html>\n' + snapshot.outerHTML,
    'text/html;charset=utf-8');
};
document.getElementById('save-json').onclick = () => {
  download('address.json', JSON.stringify(readAddress(), null, 2) + '\n',
    'application/json;charset=utf-8');
};
document.getElementById('copy').onclick = async () => {
  const data = readAddress();
  const value = `${data.merchant} ${data.phone}\n${data.lines.join('')}`;
  const status = document.getElementById('status');
  try {
    await navigator.clipboard.writeText(value);
    status.textContent = '已复制';
  } catch {
    // file:// clipboard permissions vary between browsers.
    const area = document.createElement('textarea');
    area.value = value;
    document.body.append(area);
    area.select();
    let copied = false;
    try { copied = document.execCommand('copy'); } catch { /* show manual fallback */ }
    area.remove();
    status.textContent = copied ? '已复制' : '请选中地址文字，按 Ctrl+C 或 Command+C 复制。';
  }
};
document.querySelectorAll('[contenteditable]').forEach(field => {
  field.addEventListener('keydown', event => {
    if (event.key === 'Enter') event.preventDefault();
  });
  field.addEventListener('paste', event => {
    event.preventDefault();
    const text = event.clipboardData.getData('text/plain').replace(/[\r\n]+/g, ' ');
    const selection = window.getSelection();
    if (!selection.rangeCount) return;
    const range = selection.getRangeAt(0);
    if (!field.contains(range.commonAncestorContainer)) return;
    range.deleteContents();
    const node = document.createTextNode(text);
    range.insertNode(node);
    range.setStartAfter(node);
    range.collapse(true);
    selection.removeAllRanges();
    selection.addRange(range);
  });
});
