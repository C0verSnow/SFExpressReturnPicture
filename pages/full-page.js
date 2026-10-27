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
  // Parent-child matching and explicit ambiguity handling follow the designs in
  // https://github.com/wzc570738205/smartParsePro and https://github.com/mumuy/data_location.
  // Data source, pinned revision and limitations: docs/address-parsing-research.md.
  const regions = JSON.parse(get('region-data').textContent);
  const municipalities = new Set(['北京市', '天津市', '上海市', '重庆市']);
  const shortProvinces = {'内蒙古自治区': '内蒙古', '广西壮族自治区': '广西',
    '西藏自治区': '西藏', '宁夏回族自治区': '宁夏', '新疆维吾尔自治区': '新疆'};
  function aliases(name) {
    const short = shortProvinces[name] || name.replace(/(?:省|市|区|县|特别行政区)$/, '');
    return short.length >= 2 && short !== name ? [name, short] : [name];
  }
  const paths = Object.entries(regions).flatMap(([code, county]) => {
    if (code.endsWith('00')) return [];
    const province = regions[code.slice(0, 2) + '0000'];
    const city = municipalities.has(province) ? province : regions[code.slice(0, 4) + '00'];
    // Do not invent a city for province-administered counties or missing data.
    return province && city ? [{province, city, county}] : [];
  });
  function parseRegion(address) {
    const candidates = [];
    for (const path of paths) {
      let rest = address, score = 0;
      for (const key of ['province', 'city', 'county']) {
        const match = aliases(path[key]).find(alias => rest.startsWith(alias));
        if (match) { rest = rest.slice(match.length); score += match.length; }
        else if (key === 'county') { score = 0; break; }
      }
      if (score) candidates.push({...path, detail: rest, score});
    }
    candidates.sort((a, b) => b.score - a.score);
    if (!candidates.length) throw new Error('没能识别省市区，请补全地址，或手动填写。');
    if (candidates[1]?.score === candidates[0].score) {
      throw new Error('地址有多个同名地区，请补上省、市后重新解析。');
    }
    const {province, city, county, detail} = candidates[0];
    return province + city + county + detail;
  }
  function parseContact(text) {
    if (!text.trim() || text.length > 2000) throw new Error('请粘贴一位收件人的完整信息，最多 2000 字。');
    const labels = /(收货人|收件人|收件姓名|姓名|名字|手机号码|手机号|联系电话|手机|电话|地址信息|收货地址|收件地址|详细地址|地址)\s*[:：]\s*/g;
    const pieces = [...text.matchAll(labels)];
    const values = {};
    for (let i = 0; i < pieces.length; i++) {
      const label = pieces[i][1];
      const key = /地址/.test(label) ? 'address' : /人|姓名|名字/.test(label) ? 'name' : 'phone';
      if (values[key]) throw new Error('请每次只粘贴一位收件人的信息。');
      values[key] = text.slice(pieces[i].index + pieces[i][0].length,
        pieces[i + 1]?.index ?? text.length).trim().replace(/^[,，;；]+|[,，;；]+$/g, '').trim();
    }
    const phones = [...text.matchAll(/(?<!\d)(?:\+?86[\s-]*)?(1[3-9](?:[\s-]*\d){9})(?!\d)/g)];
    if (phones.length !== 1) throw new Error('没能识别唯一的 11 位手机号，请检查后重试。');
    const phone = phones[0][1].replace(/[\s-]/g, '');
    let name = values.name, address = values.address;
    if (pieces.length) {
      if (!name || !address) throw new Error('没能识别完整信息，请写明收件人和地址，或手动填写。');
    } else {
      const before = text.slice(0, phones[0].index).trim().replace(/[,，;；]+$/, '').trim();
      const after = text.slice(phones[0].index + phones[0][0].length).trim().replace(/^[,，;；]+/, '').trim();
      // Common unlabelled order: name, phone, address (or address, phone, name).
      if (/^[\p{Script=Han}A-Za-z·.\s-]{1,40}$/u.test(before) && !/[省市区县]/.test(before)) {
        name = before; address = after;
      } else if (/^[\p{Script=Han}A-Za-z·.\s-]{1,40}$/u.test(after) && !/[省市区县]/.test(after)) {
        name = after; address = before;
      }
    }
    if (!name || !address || /[\r\n]/.test(name)) {
      throw new Error('没能识别完整信息，请写明收件人、手机号和地址，或手动填写。');
    }
    return {name, phone, address: parseRegion(address.replace(/[\s,，;；]+/g, ''))};
  }
  function splitAddress(address, ctx, width) {
    const chars = Array.from(address);
    if (chars.length < 3 || ctx.measureText(address).width > width * 3) return null;
    let best = null, bestScore = Infinity;
    // Try both cut points, so mixed Chinese/Latin text still fits all three lines.
    for (let i = 1; i < chars.length - 1; i++) {
      const first = chars.slice(0, i).join('');
      const firstWidth = ctx.measureText(first).width;
      if (firstWidth > width) break;
      for (let j = i + 1; j < chars.length; j++) {
        const lines = [first, chars.slice(i, j).join(''), chars.slice(j).join('')];
        const widths = [firstWidth, ...lines.slice(1).map(line => ctx.measureText(line).width)];
        if (widths.some(value => value > width)) continue;
        const score = Math.max(...widths) - Math.min(...widths);
        if (score < bestScore) { bestScore = score; best = lines; }
      }
    }
    return best;
  }
  function parsePastedContact() {
    if (busy) return;
    get('error').textContent = '';
    get('parse-status').textContent = '';
    try {
      const parsed = parseContact(get('paste-input').value);
      const ctx = document.createElement('canvas').getContext('2d', {alpha: false, willReadFrequently: true});
      font(ctx);
      const lines = splitAddress(parsed.address, ctx, fields.lines.width);
      if (!lines) throw new Error('地址太长或太短，无法放进三行，请手动调整；原填写内容已保留。');
      get('merchant-input').value = parsed.name;
      get('phone-input').value = parsed.phone;
      get('address-input').value = lines.join('\n');
      get('parse-status').textContent = '解析完成，请核对后点击确认修改。';
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
