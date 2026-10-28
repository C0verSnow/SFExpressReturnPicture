/* Offline contact parsing and layout. No DOM, network or drawing side effects.
 * Parent-child candidate matching follows smartParsePro and mumuy/data_location:
 * https://github.com/wzc570738205/smartParsePro
 * https://github.com/mumuy/data_location
 * Source versions, tradeoffs and limits: docs/issue-11-research.md.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.SFReturnAddress = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  function createParser(regions) {
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
      // Missing city data is not permission to invent an administrative level.
      return province && city ? [{province, city, county}] : [];
    });
    function compactAddress(address) {
      let text = '';
      const boundaries = new Set();
      for (const char of address) {
        if (/[\s,，;；]/u.test(char)) boundaries.add(text.length);
        else text += char;
      }
      return {text, boundaries};
    }
    function repeatedPaths(path) {
      // A complete repeated administrative path is stronger evidence than a
      // single place name, which could be the start of a school or road name.
      return path.province === path.city
        ? [path.province + path.city + path.county, path.province + path.county]
        : [path.province + path.city + path.county, path.city + path.county];
    }
    function stripRepeatedPath(detail, prefixes) {
      let match;
      while ((match = prefixes.find(prefix => detail.startsWith(prefix)))) {
        detail = detail.slice(match.length);
      }
      return detail;
    }
    function normalizeDetail(detail, path) {
      const prefixes = repeatedPaths(path);
      let rest = stripRepeatedPath(detail, prefixes);
      const town = rest.match(/^([\p{Script=Han}]{1,12}?(?:街道|镇|乡|苏木))/u)?.[0];
      if (!town) return rest;
      rest = rest.slice(town.length);
      while (true) {
        const next = stripRepeatedPath(rest, prefixes);
        if (next.startsWith(town)) rest = next.slice(town.length);
        else if (next !== rest) rest = next;
        else break;
      }
      return town + rest;
    }
    function normalizeRegion(address) {
      const {text, boundaries} = compactAddress(address);
      const candidates = [];
      for (const path of paths) {
        let offset = 0, score = 0, repeatedAncestor = false, hasCounty = false;
        const levels = [path.province, path.city, path.county];
        for (let level = 0; level < levels.length; level++) {
          const name = levels[level];
          const match = aliases(name).find(alias => text.startsWith(alias, offset)
            // County abbreviations must be separate input fields. Otherwise
            // 南山大道 could be silently shortened to 南山区大道.
            && (level !== 2 || alias === name || boundaries.has(offset + alias.length)
                || offset + alias.length === text.length));
          if (!match) continue;
          offset += match.length;
          score += match.length;
          if (level === 2) {
            hasCounty = true;
            // Repeated ancestor fields establish a repeated hierarchy chain.
            // A lone repeated county in detail is ambiguous, so preserve it.
            if (repeatedAncestor) {
              while (text.startsWith(name, offset)) {
                offset += name.length; score += name.length;
              }
            }
          } else {
            let count = 1;
            while (text.startsWith(name, offset)) {
              offset += name.length; score += name.length; count++;
            }
            if (count > (path.province === path.city ? 2 : 1)) repeatedAncestor = true;
          }
        }
        if (hasCounty) candidates.push({...path, detail: text.slice(offset), score});
      }
      candidates.sort((a, b) => b.score - a.score);
      if (!candidates.length) throw new Error('没能识别省市区，请补全地址，或手动填写。');
      if (candidates[1]?.score === candidates[0].score) {
        throw new Error('地址有多个同名地区，请补上省、市后重新解析。');
      }
      const path = candidates[0];
      const detail = normalizeDetail(path.detail, path);
      // These are three semantic levels, even when municipality names coincide.
      return {province: path.province, city: path.city, county: path.county, detail,
        address: path.province + path.city + path.county + detail};
    }
    function parseRegion(address) { return normalizeRegion(address).address; }
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
      return {name, phone, address: parseRegion(address)};
    }
    return {normalizeRegion, parseRegion, parseContact};
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
  function annotationRanges(address) {
    const stack = [], ranges = [];
    for (let i = 0; i < address.length; i++) {
      if ('(（'.includes(address[i])) stack.push(i);
      else if (')）'.includes(address[i]) && stack.length) {
        const start = stack.pop();
        if (!stack.length) ranges.push([start, i + 1]);
      }
    }
    return ranges;
  }
  function fitAddress(address, ctx, width) {
    let lines = splitAddress(address, ctx, width);
    const omitted = [];
    if (lines) return {lines, omitted};
    // Preserve the complete address whenever possible. Remove paired notes from
    // the end one at a time, stopping as soon as three nonempty lines fit.
    for (const [start, end] of annotationRanges(address).reverse()) {
      omitted.unshift(address.slice(start, end));
      address = address.slice(0, start) + address.slice(end);
      lines = splitAddress(address, ctx, width);
      if (lines) return {lines, omitted};
    }
    throw new Error('地址太长或太短，无法放进三行，请手动调整；原填写内容已保留。');
  }
  return {createParser, splitAddress, fitAddress};
});
