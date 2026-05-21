with open('frontend/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find handleSave - replace only the body inside { }
idx = content.find('async function handleSave')
brace1 = content.find('{', idx)
brace2 = content.find('}', brace1)
if idx > 0 and brace1 > 0 and brace2 > 0:
    new_body = ''' {
    const slot = 1;
    try {
        const saveData = JSON.stringify(STATE);
        localStorage.setItem('killer_boss_save_' + slot, saveData);
        appendNarrative('\\u{1F4BE} \\u5B58\\u6863\\u6210\\u529F\\uFF08localStorage\\uFF09', 'narrative');
        showToast('\\u5B58\\u6863\\u6210\\u529F \\u2705');
    } catch(e) {
        appendNarrative('\\u26A0\\uFE0F \\u5B58\\u6863\\u5931\\u8D25\\uFF1A' + e.message, 'system');
    }
    await apiCall('save', { slot });
    setLoading(false);
}'''
    content = content[:brace1] + new_body + content[brace2+1:]
    print('1. handleSave OK')
else:
    print('1. FAIL')

# Find handleLoad - replace only the body
idx = content.find('async function handleLoad')
brace1 = content.find('{', idx)
brace2 = content.find('}', brace1)
# Find the second } (end of function body)
# count braces
depth = 1
pos = brace1 + 1
while depth > 0 and pos < len(content):
    if content[pos] == '{': depth += 1
    elif content[pos] == '}': depth -= 1
    pos += 1
brace2 = pos - 1

if idx > 0:
    new_body = ''' {
    const slot = 1;
    const saved = localStorage.getItem('killer_boss_save_' + slot);
    if (saved) {
        try {
            const savedState = JSON.parse(saved);
            if (savedState && savedState.hitmen) {
                STATE = savedState;
                gameStarted = true;
                updateStats(savedState);
                dom.startScreen.classList.add('hidden');
                dom.gameUI.classList.remove('hidden');
                dom.btnStart.disabled = false;
                appendNarrative('\\u{1F4C2} \\u8BFB\\u6863\\u6210\\u529F', 'narrative');
                showToast('\\u8BFB\\u6863\\u6210\\u529F \\u2705');
                setLoading(false);
                return;
            }
        } catch(e) {
            appendNarrative('\\u26A0\\uFE0F \\u8BFB\\u6863\\u5931\\u8D25\\uFF1A' + e.message, 'system');
        }
    }
    const data = await apiCall('load', { slot });
    if (data) {
        updateUI(data.state, data.narrative);
    } else {
        showToast('\\u6CA1\\u6709\\u627E\\u5230\\u5B58\\u6863 \\u274C');
    }
    setLoading(false);
}'''
    content = content[:brace1] + new_body + content[brace2+1:]
    print('2. handleLoad OK')
else:
    print('2. FAIL')

with open('frontend/script.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('DONE')
