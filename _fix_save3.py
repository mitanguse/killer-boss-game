import re

with open('frontend/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find handleSave and handleLoad functions and replace them
# by position rather than text matching

# 1. handleSave
idx1 = content.find('async function handleSave()')
idx2 = content.find('async function handleLoad()', idx1)
old_save = content[idx1:idx2]

new_save = """async function handleSave() {
    const slot = 1;
    try {
        const saveData = JSON.stringify(STATE);
        localStorage.setItem('killer_boss_save_' + slot, saveData);
        localStorage.setItem('killer_boss_save_session_' + slot, SESSION_ID);
        appendNarrative('\\u{1F4BE} \\u5B58\\u6863\\u5DF2\\u4FDD\\u5B58\\uFF08localStorage\\uFF09', 'narrative');
        showToast('\\u5B58\\u6863\\u6210\\u529F \\u2705');
    } catch(e) {
        appendNarrative('\\u26A0\\uFE0F \\u5B58\\u6863\\u5931\\u8D25\\uFF1A' + e.message, 'system');
    }
    await apiCall('save', { slot });
    setLoading(false);
}

"""

content = content[:idx1] + new_save + content[idx2:]
print('1. handleSave replaced')

# 2. handleLoad
idx3 = content.find('async function handleLoad()', idx1)
idx4 = content.find('\n// --- 装备', idx3)
old_load = content[idx3:idx4]

new_load = """async function handleLoad() {
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
                appendNarrative('\\u{1F4C2} \\u4ECE\\u672C\\u5730\\u8BFB\\u53D6\\u5B58\\u6863\\u6210\\u529F', 'narrative');
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
}

"""

content = content[:idx3] + new_load + content[idx4:]
print('2. handleLoad replaced')

with open('frontend/script.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('DONE')
