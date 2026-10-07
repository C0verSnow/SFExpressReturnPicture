(() => {
  const get = id => document.getElementById(id);
  const state = JSON.parse(get('address-state').textContent);
  const original = {merchant: '多联科技', phone: '18925023056', lines: [
    '广东省广州市增城区 永宁街道和兴路鑫耀汽',
    '车贴膜对面驿站5号箱(请用纸盒包装好，勿', '发到付)']};
  // Coordinates use the original 1182 × 2560 screenshot, not viewport pixels.
  const fields = {
    merchant: {box: [362, 1708, 204, 76], x: 368, y: 1764, width: 194, color: '#191919'},
    phone: {box: [566, 1708, 380, 76], x: 570, y: 1764, width: 372, color: '#191919'},
    lines: {box: [126, 1800, 938, 246], x: 132, y: 1858, width: 926, color: '#5d5d5d'}
  };
  const dialog = get('editor');
  let busy = false;
  function font(ctx) {
    ctx.font = '48px Address';
    ctx.letterSpacing = '-0.5px';
    ctx.textBaseline = 'alphabetic';
  }
  function changed(data) {
    return Object.keys(fields).some(key => JSON.stringify(data[key]) !== JSON.stringify(original[key]));
  }
  async function photo(data) {
    await document.fonts.ready;
    await get('source').decode();
    const canvas = document.createElement('canvas');
    canvas.width = 1182; canvas.height = 2560;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(get('source'), 0, 0);
    font(ctx);
    for (const [key, field] of Object.entries(fields)) {
      // Leave unchanged fields as their original pixels, including original glyphs.
      if (JSON.stringify(data[key]) === JSON.stringify(original[key])) continue;
      ctx.fillStyle = '#f6f6f6';
      ctx.fillRect(...field.box);
      ctx.fillStyle = field.color;
      const values = key === 'lines' ? data.lines : [data[key]];
      values.forEach((value, i) => ctx.fillText(value, field.x, field.y + i * 76));
    }
    return canvas;
  }
  function render(canvas) {
    get('rendered-photo').getContext('2d').drawImage(canvas, 0, 0);
    get('rendered-photo').hidden = !changed(state);
    get('rendered-photo').setAttribute('aria-label', `${state.merchant} ${state.phone} ${state.lines.join(' ')}`);
    get('address-state').textContent = JSON.stringify(state).replace(/</g, '\\u003c');
  }
  function download(name, blob) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = name;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  }
  function png(canvas) {
    return new Promise((resolve, reject) => canvas.toBlob(blob =>
      blob ? resolve(blob) : reject(new Error('照片生成失败')), 'image/png'));
  }
  get('edit-address').onclick = () => {
    get('merchant-input').value = state.merchant;
    get('phone-input').value = state.phone;
    get('address-input').value = state.lines.join('\n').replace(/\n+$/, '');
    get('error').textContent = '';
    dialog.showModal();
    get('merchant-input').focus();
  };
  get('cancel').onclick = () => { if (!busy) dialog.close(); };
  dialog.addEventListener('cancel', event => { if (busy) event.preventDefault(); });
  get('address-form').onsubmit = async event => {
    event.preventDefault();
    if (busy) return;
    busy = true;
    get('confirm').disabled = true;
    get('error').textContent = '';
    try {
      await document.fonts.ready;
      const data = {
        merchant: get('merchant-input').value.trim(),
        phone: get('phone-input').value.trim(),
        lines: get('address-input').value.replace(/\r/g, '').split('\n').map(line => line.trim())
      };
      if (!data.merchant || !data.phone || /[\r\n]/.test(data.merchant + data.phone)) {
        get('error').textContent = '请填写单行名字和电话。'; return;
      }
      if (!data.lines.some(Boolean) || data.lines.length > 3) {
        get('error').textContent = '请填写新地址，最多三行。'; return;
      }
      const ctx = document.createElement('canvas').getContext('2d');
      font(ctx);
      for (const [key, field] of Object.entries(fields)) {
        const values = key === 'lines' ? data.lines : [data[key]];
        // Original pixels are retained, so their text need not fit the substitute font.
        if (JSON.stringify(values) === JSON.stringify(key === 'lines' ? original.lines : [original[key]])) continue;
        if (values.some(value => ctx.measureText(value).width > field.width)) {
          get('error').textContent = key === 'lines'
            ? '有一行地址太长，请换行，最多三行。'
            : `${key === 'merchant' ? '名字' : '电话'}太长，请缩短，保持原图字号和位置。`;
          return;
        }
      }
      data.lines = [...data.lines, ...Array(3 - data.lines.length).fill('')];
      const canvas = await photo(data);
      const blob = await png(canvas);
      Object.assign(state, data);
      render(canvas);
      download('return-page-edited.png', blob);
      dialog.close();
      get('status').textContent = '已生成修改后的 PNG 照片并发起下载，请查看浏览器下载列表。';
    } catch (error) {
      get('error').textContent = '照片未能保存，请重新点击确认修改。';
    } finally {
      busy = false;
      get('confirm').disabled = false;
    }
  };
  get('save-photo').onclick = async () => {
    try {
      download('return-page-edited.png', await png(await photo(state)));
      get('status').textContent = '已发起 PNG 照片下载，请查看浏览器下载列表。';
    } catch (error) {
      get('status').textContent = '照片未能保存，请重试。';
    }
  };
  get('save').onclick = () => {
    const snapshot = document.documentElement.cloneNode(true);
    snapshot.querySelector('#editor').removeAttribute('open');
    snapshot.querySelector('#status').textContent = '';
    snapshot.querySelector('#error').textContent = '';
    snapshot.querySelector('#confirm').removeAttribute('disabled');
    snapshot.querySelector('#rendered-photo').setAttribute('hidden', '');
    snapshot.querySelector('#address-input').textContent = '';
    download('return-page-edited.html', new Blob(['<!doctype html>\n' + snapshot.outerHTML], {type: 'text/html;charset=utf-8'}));
  };
  get('save-json').onclick = () => download('address.json', new Blob([JSON.stringify(state, null, 2) + '\n'], {type: 'application/json;charset=utf-8'}));
  get('edit-address').disabled = true;
  photo(state).then(canvas => {
    render(canvas);
    get('edit-address').disabled = false;
  }).catch(() => {
    get('status').textContent = '图片或字体未能加载，请重新打开网页。';
  });
})();
