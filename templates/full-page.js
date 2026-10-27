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
  function render(canvas, blob) {
    currentPNG = blob;
    get('rendered-photo').getContext('2d').drawImage(canvas, 0, 0);
    get('rendered-photo').hidden = false;
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
  // Extract labelled fields first; keep uncertain results for manual correction.
  // Parsing approach informed by docs/address-parsing-research.md.
  function parseContact(text) {
    const name = text.match(/(?:收货人|收件人|姓名|名字)\s*[:：]\s*([^\s,，;；]+)/);
    const phone = text.match(/(?<!\d)1[3-9]\d{9}(?!\d)/);
    const label = text.match(/(?:地址信息|收货地址|收件地址|地址)\s*[:：]\s*([\s\S]*)/);
    let address = label ? label[1] : text.replace(phone?.[0] || '', '').replace(name?.[0] || '', '');
    address = address.trim().replace(/\s+/g, '');
    const municipality = address.match(/^(北京|上海|天津|重庆)(?:市)?/);
    if (municipality) {
      const city = municipality[1] + '市';
      address = address.slice(municipality[0].length);
      const repeated = new RegExp('^' + municipality[1] + '(?:市)?');
      address = city + city + address.replace(repeated, '');
    }
    const district = address.match(/^(.+?(?:省|自治区|北京市北京市|上海市上海市|天津市天津市|重庆市重庆市))(.+?(?:市|自治州|地区|盟))(.+?(?:区|县|旗|市))/);
    const municipalDistrict = address.match(/^(北京市北京市|上海市上海市|天津市天津市|重庆市重庆市)(.+?(?:区|县))/);
    if (!name || !phone || !(district || municipalDistrict)) return null;
    return {name: name[1], phone: phone[0], address};
  }
  function splitAddress(address, ctx, width) {
    const chars = Array.from(address);
    if (chars.length < 3) return null;
    // Balance the lines while checking the actual font width and retaining every character.
    const lines = [];
    for (let remaining = 3; remaining > 0; remaining--) {
      let take = Math.ceil(chars.length / remaining);
      while (take > 0 && ctx.measureText(chars.slice(0, take).join('')).width > width) take--;
      if (!take || chars.length - take < remaining - 1) return null;
      lines.push(chars.splice(0, take).join(''));
    }
    return chars.length ? null : lines;
  }
  get('parse-address').onclick = async () => {
    get('error').textContent = '';
    const parsed = parseContact(get('paste-input').value);
    if (!parsed) {
      get('error').textContent = '没能识别完整信息，请写明收件人、手机号和省市区，或手动填写。'; return;
    }
    await document.fonts.ready;
    const ctx = document.createElement('canvas').getContext('2d');
    font(ctx);
    const lines = splitAddress(parsed.address, ctx, fields.lines.width);
    if (!lines) {
      get('error').textContent = '地址太长或太短，无法放进三行，请手动调整。'; return;
    }
    get('merchant-input').value = parsed.name;
    get('phone-input').value = parsed.phone;
    get('address-input').value = lines.join('\n');
    get('error').textContent = '解析完成，请核对姓名、电话和地址。';
  };
  get('edit-address').onclick = () => {
    get('paste-input').value = '';
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
      if (data.lines.length !== 3 || data.lines.some(line => !line)) {
        get('error').textContent = '地址请写满三行，每行都要填写。'; return;
      }
      const ctx = document.createElement('canvas').getContext('2d');
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
    get('edit-address').disabled = false;
    get('save-photo').disabled = false;
  }
  initialize().catch(() => {
    get('status').textContent = '图片或字体未能加载，请重新打开网页。';
  });
})();
