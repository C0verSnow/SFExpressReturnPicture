(() => {
  const get = id => document.getElementById(id);
  // Device hints distinguish touch tablets from laptops; width handles resizing.
  function fitPlatform() {
    const width = window.innerWidth;
    const mobileDevice = navigator.userAgentData?.mobile ?? /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    const touchDevice = navigator.maxTouchPoints > 1 && matchMedia('(pointer: coarse)').matches;
    const platform = width < 600 ? 'mobile'
      : (((mobileDevice || touchDevice) && width < 1400) || width < 1024) ? 'tablet'
      : width < 1600 ? 'laptop' : 'desktop';
    const sizes = {desktop: '1920x1080', laptop: '1440x900', tablet: '768x1024', mobile: '390x844'};
    document.documentElement.dataset.platform = platform;
    document.documentElement.dataset.designCanvas = sizes[platform];
  }
  fitPlatform();
  window.addEventListener('resize', fitPlatform);
  const state = JSON.parse(get('address-state').textContent);
  const initialState = structuredClone(state);
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
  let currentPNG;
  let initialPhoto;
  function font(ctx) {
    ctx.font = '48px Address';
    ctx.fontKerning = 'none';
    ctx.letterSpacing = '-0.5px';
    ctx.textBaseline = 'alphabetic';
  }
  async function photo(data) {
    await document.fonts.load('48px Address');
    await document.fonts.ready;
    await get('source').decode();
    const canvas = document.createElement('canvas');
    canvas.width = 1182; canvas.height = 2560;
    // Use a consistent software surface for PNGs on every device.
    const ctx = canvas.getContext('2d', {alpha: false, willReadFrequently: true});
    ctx.drawImage(currentPNG ? get('rendered-photo') : get('source'), 0, 0);
    font(ctx);
    for (const [key, field] of Object.entries(fields)) {
      // Preserve untouched pixels: re-rasterizing identical digits after text
      // measurement can produce different antialiasing in Chromium.
      if (currentPNG && JSON.stringify(data[key]) === JSON.stringify(state[key])) continue;
      if (initialPhoto && JSON.stringify(data[key]) === JSON.stringify(initialState[key])) {
        ctx.drawImage(initialPhoto, ...field.box, ...field.box);
        continue;
      }
      if (JSON.stringify(data[key]) === JSON.stringify(original[key])) {
        ctx.drawImage(get('source'), ...field.box, ...field.box);
        continue;
      }
      ctx.fillStyle = '#f6f6f6';
      ctx.fillRect(...field.box);
      ctx.fillStyle = field.color;
      const values = key === 'lines' ? data.lines : [data[key]];
      values.forEach((value, i) => ctx.fillText(value, field.x, field.y + i * 76));
    }
    return canvas;
  }
  function render(canvas, blob) {
    currentPNG = blob;
    get('rendered-photo').getContext('2d').drawImage(canvas, 0, 0);
    get('rendered-photo').hidden = false;
    get('loading').hidden = true;
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
  const {parseContact} = SFReturnAddress.createParser(JSON.parse(get('region-data').textContent));
  const {fitAddress} = SFReturnAddress;
  function parsePastedContact() {
    if (busy) return;
    get('error').textContent = '';
    get('parse-status').textContent = '';
    try {
      const parsed = parseContact(get('paste-input').value);
      const ctx = document.createElement('canvas').getContext('2d', {alpha: false, willReadFrequently: true});
      font(ctx);
      const {lines, omitted} = fitAddress(parsed.address, ctx, fields.lines.width);
      get('merchant-input').value = parsed.name;
      get('phone-input').value = parsed.phone;
      get('address-input').value = lines.join('\n');
      get('parse-status').textContent = omitted.length
        ? `解析完成，已省略括号附注：${omitted.join('、')}。请核对后点击确认修改。`
        : '解析完成，请核对后点击确认修改。';
    } catch (error) {
      get('error').textContent = error.message;
    }
  }
  let clipboardRequest = 0;
  function cancelClipboardRead() {
    clipboardRequest++;
    get('parse-address').disabled = false;
  }
  get('parse-address').onclick = async () => {
    const button = get('parse-address');
    if (busy || button.disabled) return;
    const request = ++clipboardRequest;
    const input = get('paste-input');
    const error = get('error');
    error.textContent = '';
    get('parse-status').textContent = '';
    button.disabled = true;
    try {
      if (typeof navigator.clipboard?.readText !== 'function') {
        error.textContent = '当前浏览器无法自动读取剪贴板，请手动粘贴收件信息。';
        input.focus();
        return;
      }
      // Call from the click before any await, preserving Safari user activation.
      // Support/error handling follows VueUse useClipboard; see docs/clipboard-research.md.
      const text = await navigator.clipboard.readText();
      if (request !== clipboardRequest || !dialog.open || busy) return;
      if (!text.trim()) {
        error.textContent = '剪贴板暂无内容';
        return;
      }
      input.value = text;
      parsePastedContact();
    } catch (err) {
      if (request !== clipboardRequest || !dialog.open || busy) return;
      error.textContent = '读取剪贴板失败或权限被拒绝，请手动粘贴收件信息。';
      input.focus();
    } finally {
      if (request === clipboardRequest) button.disabled = false;
    }
  };
  // A delayed permission response must not overwrite a later edit or dialog session.
  get('address-form').addEventListener('input', cancelClipboardRead);
  dialog.addEventListener('close', cancelClipboardRead);
  // The input event runs after a paste has populated the textarea, including on mobile.
  get('paste-input').addEventListener('input', parsePastedContact);
  get('edit-address').onclick = () => {
    cancelClipboardRead();
    get('paste-input').value = '';
    get('parse-status').textContent = '';
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
    cancelClipboardRead();
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
      if (data.lines.length !== 3 || data.lines.some(line => !line)) {
        get('error').textContent = '地址请写满三行，每行都要填写。'; return;
      }
      const ctx = document.createElement('canvas').getContext('2d', {alpha: false, willReadFrequently: true});
      font(ctx);
      for (const [key, field] of Object.entries(fields)) {
        const values = key === 'lines' ? data.lines : [data[key]];
        // Original pixels are retained, so their text need not fit the substitute font.
        if (JSON.stringify(values) === JSON.stringify(key === 'lines' ? original.lines : [original[key]])) continue;
        if (values.some(value => ctx.measureText(value).width > field.width)) {
          get('error').textContent = key === 'lines'
            ? '有一行地址太长，请缩短，并保持三行。'
            : `${key === 'merchant' ? '名字' : '电话'}太长，请缩短，保持原图字号和位置。`;
          return;
        }
      }
      const canvas = await photo(data);
      const blob = await png(canvas);
      Object.assign(state, data);
      render(canvas, blob);
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
      if (!currentPNG) throw new Error('照片尚未加载');
      download('return-page-edited.png', currentPNG);
      get('status').textContent = '已发起 PNG 照片下载，请查看浏览器下载列表。';
    } catch (error) {
      get('status').textContent = '照片未能保存，请重试。';
    }
  };
  get('edit-address').disabled = true;
  async function initialize() {
    const canvas = await photo(state);
    const blob = await png(canvas);
    render(canvas, blob);
    initialPhoto = canvas;
    get('edit-address').disabled = false;
    get('save-photo').disabled = false;
  }
  initialize().catch(() => {
    get('loading').textContent = '图片或字体未能加载，请重新打开网页。';
    get('status').textContent = get('loading').textContent;
  });
})();
