"""Shared remote browser checks for one-click clipboard parsing and safe fallback."""

SAMPLE = '张三 18888888888\n广东省深圳市南山区人才公园'
SELECTORS = ('#merchant-input', '#phone-input', '#address-input')


def values(page):
    return [page.locator(selector).input_value() for selector in SELECTORS]


def mock_clipboard(page, mode, text=SAMPLE):
    page.evaluate('''({mode, text}) => {
      window.clipboardCalls = 0;
      const clipboard = mode === 'unsupported' ? undefined
        : mode === 'missing-method' ? {}
        : {readText() {
          window.clipboardCalls++;
          if (mode === 'denied') return Promise.reject(new DOMException('Denied', 'NotAllowedError'));
          if (mode === 'failed') throw new Error('Read failed');
          if (mode === 'pending') return new Promise((resolve, reject) => {
            window.resolveClipboard = resolve; window.rejectClipboard = reject;
          });
          return Promise.resolve(text);
        }};
      Object.defineProperty(navigator, 'clipboard', {configurable: true, value: clipboard});
    }''', {'mode': mode, 'text': text})


def click_and_wait(page):
    page.locator('#parse-address').click()
    page.wait_for_function("!document.getElementById('parse-address').disabled")


def assert_sample(page):
    assert page.locator('#paste-input').input_value() == SAMPLE
    assert page.locator('#merchant-input').input_value() == '张三'
    assert page.locator('#phone-input').input_value() == '18888888888'
    lines = page.locator('#address-input').input_value().split('\n')
    assert len(lines) == 3 and all(lines)
    assert ''.join(lines) == '广东省深圳市南山区人才公园'
    assert page.locator('#parse-status').text_content().startswith('解析完成')
    assert page.locator('#error').text_content() == ''


def check_clipboard(page):
    """The caller opens a ready editor; checks never confirm or download a photo."""
    assert page.locator('#parse-address').text_content() == '粘贴并解析'
    assert page.locator('#paste-input').get_attribute('placeholder') == SAMPLE
    before = page.locator('#address-state').text_content()
    mock_clipboard(page, 'success')
    page.locator('#paste-input').fill('旧内容，需要覆盖')
    click_and_wait(page)
    assert page.evaluate('window.clipboardCalls') == 1
    assert_sample(page)
    # All three fields remain editable after parsing.
    for selector, text in zip(SELECTORS, ('李四', '13800138000', '广东省\n深圳市\n南山区手改地址')):
        page.locator(selector).fill(text)
    unchanged = values(page)
    for mode, text, message in (
        ('success', '', '剪贴板暂无内容'),
        ('success', ' \n\t ', '剪贴板暂无内容'),
        ('denied', '', '手动粘贴'),
        ('failed', '', '手动粘贴'),
        ('unsupported', '', '手动粘贴'),
        ('missing-method', '', '手动粘贴'),
    ):
        mock_clipboard(page, mode, text)
        click_and_wait(page)
        assert message in page.locator('#error').text_content()
        assert page.locator('#parse-status').text_content() == ''
        assert page.locator('#paste-input').input_value() == SAMPLE
        assert values(page) == unchanged
    # A programmatic clipboard assignment must respect the parser's 2000-character limit.
    for text in ('信息不完整', SAMPLE + '长' * 2000):
        mock_clipboard(page, 'success', text)
        click_and_wait(page)
        assert page.locator('#paste-input').input_value() == text
        assert page.locator('#error').text_content()
        assert values(page) == unchanged
    # Typing/pasting still parses immediately after unavailable or rejected access.
    for mode in ('unsupported', 'denied'):
        mock_clipboard(page, mode)
        click_and_wait(page)
        page.locator('#paste-input').fill(SAMPLE)
        assert_sample(page)
        page.locator('#paste-input').fill('旧内容')
    page.locator('#paste-input').fill(SAMPLE)
    # Repeated clicks cannot start concurrent reads.
    mock_clipboard(page, 'pending')
    page.locator('#parse-address').click()
    assert page.locator('#parse-address').is_disabled()
    page.locator('#parse-address').evaluate('button => button.click()')
    assert page.evaluate('window.clipboardCalls') == 1
    # Manual edits while a permission prompt is open win over a late result.
    page.locator('#merchant-input').fill('手改姓名')
    unchanged = values(page)
    page.evaluate('window.resolveClipboard("李四 13800138000 广东省深圳市南山区新地址")')
    assert values(page) == unchanged
    assert page.locator('#paste-input').input_value() == SAMPLE
    assert page.locator('#parse-address').is_enabled()
    # A cancelled and reopened editor cannot receive the previous session's result/error.
    for rejected in (False, True):
        mock_clipboard(page, 'pending')
        page.locator('#parse-address').click()
        page.locator('#cancel').click()
        page.locator('#edit-address').click()
        unchanged = values(page)
        if rejected:
            page.evaluate('window.rejectClipboard(new Error("late rejection"))')
        else:
            page.evaluate('window.resolveClipboard("李四 13800138000 广东省深圳市南山区新地址")')
        assert values(page) == unchanged
        assert page.locator('#paste-input').input_value() == ''
        assert page.locator('#error').text_content() == ''
        assert page.locator('#parse-address').is_enabled()
    assert page.locator('#address-state').text_content() == before
    assert page.locator('#editor').is_visible()
    # Restore native API for other checks using this page.
    page.evaluate("delete navigator.clipboard")
