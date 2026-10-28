/* Remote-only regression tests for complete normalized addresses, before layout. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const root = path.resolve(__dirname, '..');
const core = require('../src/sf_return/address/contact.js');
const regions = JSON.parse(fs.readFileSync(path.join(root, 'src/sf_return/address/data/list.json'), 'utf8'));
const api = {...core, ...core.createParser(regions)};
const cases = [
  ['Howard repeat', '北京 北京市 通州区 宋庄镇 北京市通州区宋庄镇宋庄南路北京工商大学嘉华学院',
    '北京市北京市通州区宋庄镇宋庄南路北京工商大学嘉华学院'],
  ['Beijing single', '北京市通州区宋庄镇1号', '北京市北京市通州区宋庄镇1号'],
  ['Beijing canonical', '北京市北京市通州区宋庄镇1号', '北京市北京市通州区宋庄镇1号'],
  ['Tianjin alias', '天津和平区南京路1号', '天津市天津市和平区南京路1号'],
  ['Shanghai single', '上海市浦东新区新地址100号', '上海市上海市浦东新区新地址100号'],
  ['Chongqing repeated', '重庆市重庆市渝中区重庆市渝中区解放碑1号', '重庆市重庆市渝中区解放碑1号'],
  ['Ordinary aliases', '广东 深圳 南山 科技园1号', '广东省深圳市南山区科技园1号'],
  ['Missing unique province', '深圳市南山区科技园1号', '广东省深圳市南山区科技园1号'],
  ['Autonomous region', '广西南宁青秀区民族大道1号', '广西壮族自治区南宁市青秀区民族大道1号'],
  ['Repeated levels', '广东省 广东省 深圳市 深圳市 南山区 南山区 科技园1号', '广东省深圳市南山区科技园1号'],
  ['Repeated full path', '广东省深圳市南山区广东省深圳市南山区科技园1号', '广东省深圳市南山区科技园1号'],
  ['Repeated town and path', '广东省深圳市南山区粤海街道广东省深圳市南山区粤海街道科技园1号', '广东省深圳市南山区粤海街道科技园1号'],
  ['Repeated town', '广东省深圳市南山区粤海街道 粤海街道 科技园1号', '广东省深圳市南山区粤海街道科技园1号'],
  ['Names in detail', '广东省深圳市南山区南山大道北京银行南山学校1号楼', '广东省深圳市南山区南山大道北京银行南山学校1号楼'],
  ['Beijing school', '北京市通州区宋庄南路北京工商大学嘉华学院', '北京市北京市通州区宋庄南路北京工商大学嘉华学院'],
  ['Foreign place at detail start', '广东省深圳市南山区北京市实验学校1号', '广东省深圳市南山区北京市实验学校1号'],
  ['County school at detail start', '北京市通州区通州区实验学校1号', '北京市北京市通州区通州区实验学校1号'],
  ['County road at detail start', '广东省深圳市南山区南山区大道1号', '广东省深圳市南山区南山区大道1号'],
  ['Administrative levels without detail', '广东省深圳市南山区', '广东省深圳市南山区'],
  ['County school after repeated province', '广东省广东省深圳市南山区南山区实验学校1号', '广东省深圳市南山区南山区实验学校1号'],
  ['Town school at detail start', '北京市通州区宋庄镇宋庄镇中心小学1号', '北京市北京市通州区宋庄镇宋庄镇中心小学1号'],
  ['Concatenated county preserved', '广东省广东省深圳市深圳市南山区南山区科技园1号', '广东省深圳市南山区南山区科技园1号'],
  ['Concatenated town preserved', '广东省深圳市南山区粤海街道粤海街道科技园1号', '广东省深圳市南山区粤海街道粤海街道科技园1号'],
  ['Town field followed by town-named school', '北京市通州区宋庄镇 宋庄镇中心小学1号', '北京市北京市通州区宋庄镇宋庄镇中心小学1号'],
  ['Keep notes', '广东省深圳市南山区科技园（东门）1号', '广东省深圳市南山区科技园（东门）1号'],
];
for (const [label, input, expected] of cases) {
  test(label + ': normalize then lay out without losing the body', () => {
    const result = api.parseContact('收货人:Howard\n手机号码:13800138000\n地址信息: ' + input);
    assert.equal(result.name, 'Howard');
    assert.equal(result.phone, '13800138000');
    assert.equal(result.address, expected);
    assert.equal(api.parseRegion(expected), expected, 'Normalization must be idempotent');
    const ctx = {measureText: text => ({width: Array.from(text).length})};
    const laidOut = api.fitAddress(result.address, ctx, Math.ceil(Array.from(expected).length / 3));
    assert.equal(laidOut.lines.length, 3);
    assert.ok(laidOut.lines.every(Boolean));
    assert.equal(laidOut.lines.join(''), expected);
    assert.equal(laidOut.omitted.length, 0);
  });
}
for (const address of ['鼓楼区中山路1号', '广东省北京市通州区1号', '广东省深圳市科技园1号',
  '海南省文昌市文城镇1号', '广东省深圳市南山大道1号', '广东省深圳市南山科技园1号']) {
  test('Uncertain hierarchy requires manual correction: ' + address, () => {
    assert.throws(() => api.parseContact('张三 13800138000 ' + address), /省市区|同名地区/);
  });
}
test('Municipality fields represent distinct administrative levels', () => {
  const result = api.normalizeRegion('北京 通州区 通州区实验学校1号');
  assert.deepEqual(result, {province: '北京市', city: '北京市', county: '通州区',
    detail: '通州区实验学校1号', address: '北京市北京市通州区通州区实验学校1号'});
});
test('Phone normalization and labels remain compatible', () => {
  const result = api.parseContact('地址：深圳市南山区科技园1号；电话：+86 138-0013-8000；收件人：张三');
  assert.equal(result.phone, '13800138000');
  assert.equal(result.address, '广东省深圳市南山区科技园1号');
  assert.throws(() => api.parseContact('张三 13800138000 13900139000 广东省深圳市南山区1号'), /唯一/);
});
test('Layout never truncates a body; only paired notes may be omitted with notice', () => {
  const ctx = {measureText: text => ({width: Array.from(text).length})};
  const body = '广东省深圳市南山区科技园1号';
  const fitted = api.fitAddress(body + '（' + '说明'.repeat(40) + '）', ctx, 8);
  assert.equal(fitted.lines.join(''), body);
  assert.equal(fitted.omitted.length, 1);
  assert.throws(() => api.fitAddress(body + '正文'.repeat(40), ctx, 8), /地址太长/);
  assert.throws(() => api.fitAddress(body + '(' + '说明'.repeat(40), ctx, 8), /地址太长/);
});
