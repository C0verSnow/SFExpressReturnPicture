(() => {
  const get = id => document.getElementById(id);
  const state = JSON.parse(get('address-state').textContent);
  const original = ['广东省广州市增城区 永宁街道和兴路鑫耀汽',
    '车贴膜对面驿站5号箱(请用纸盒包装好，勿', '发到付)'];
  const dialog = get('editor');
  const input = get('address-input');
  function render() {
    const changed = JSON.stringify(state.lines) !== JSON.stringify(original);
    get('replacement').hidden = !changed;
    get('replacement').querySelectorAll('span').forEach((node, i) => {
      node.textContent = state.lines[i] || '';
    });
    get('address-state').textContent = JSON.stringify(state).replace(/</g, '\\u003c');
  }
  get('edit-address').onclick = () => {
    input.value = state.lines.filter(Boolean).join('\n');
    get('error').textContent = '';
    dialog.showModal();
    input.focus();
  };
  get('cancel').onclick = () => dialog.close();
  get('address-form').onsubmit = async event => {
    event.preventDefault();
    await document.fonts.ready;
    const lines = input.value.replace(/\r/g, '').split('\n').map(line => line.trim());
    if (!lines.some(Boolean) || lines.length > 3) {
      get('error').textContent = '请填写新地址，最多三行。';
      return;
    }
    // Use the actual font and letter spacing to prevent silent clipping.
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    ctx.font = '48px Address';
    if (lines.some(line => ctx.measureText(line).width - Math.max(0, Array.from(line).length - 1) * .5 > 926)) {
      get('error').textContent = '有一行太长，请换行，最多三行。';
      return;
    }
    state.lines = [...lines, ...Array(3 - lines.length).fill('')];
    render();
    dialog.close();
    get('status').textContent = '地址已更新，请保存网页以保留修改。';
  };
  function download(name, value, type) {
    const url = URL.createObjectURL(new Blob([value], {type}));
    const link = document.createElement('a');
    link.href = url; link.download = name; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  get('save').onclick = () => {
    const snapshot = document.documentElement.cloneNode(true);
    snapshot.querySelector('#editor').removeAttribute('open');
    snapshot.querySelector('#status').textContent = '';
    snapshot.querySelector('#error').textContent = '';
    snapshot.querySelector('#address-input').textContent = '';
    download('return-page-edited.html', '<!doctype html>\n' + snapshot.outerHTML, 'text/html;charset=utf-8');
  };
  get('save-json').onclick = () => download('address.json', JSON.stringify(state, null, 2) + '\n', 'application/json;charset=utf-8');
  render();
})();
