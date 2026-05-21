with open('frontend/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace handleSave with localStorage version
old_save = """async function handleSave() {
    const slot = 1;
    const data = await apiCall('save', { slot });
    if (!data) return;
    let msg = data.narrative || `\u{1F4BE} \u5B58\u6863\u5DF2\u4FDD\u5B58\uFF08\u7B2C${slot}\u680F\uFF09`;
    appendNarrative(msg, 'narrative');
    showToast('\u5B58\u6863\u6210\u529F \u2705');
    setLoading(false);
}"""

new_save = """async function handleSave() {
    const slot = 1;
    // 先用 localStorage 存档
    try {
        const saveData = JSON.stringify(STATE);
        localStorage.setItem('killer_boss_save_' + slot, saveData);
        localStorage.setItem('killer_boss_save_session_' + slot, SESSION_ID);
        appendNarrative('\u{1F4BE} \u5B58\u6863\u5DF2\u4FDD\u5B58\uFF08localStorage\uFF09', 'narrative');
        showToast('\u5B58\u6863\u6210\u529F \u2705');
    } catch(e) {
        appendNarrative('\u26A0\uFE0F \u5B58\u6863\u5931\u8D25\uFF1A' + e.message, 'system');
    }
    // 尝试服务器存档（可能被 Render 清掉，但试试无妨）
    const data = await apiCall('save', { slot });
    setLoading(false);
}"""

content = content.replace(old_save, new_save, 1)
print('1. handleSave OK')

# Replace handleLoad with localStorage version
old_load = """async function handleLoad() {
    const savesResp = await apiCall('list_saves');
    if (!savesResp) return;
    const saves = savesResp.extra?.saves || [];
    if (saves.length === 0) {
        showToast('\u6CA1\u6709\u627E\u5230\u5B58\u6863 \u274C');
        setLoading(false);
        return;
    }
    const slot = 1;
    const data = await apiCall('load', { slot });
    if (!data) return;
    updateUI(data.state, data.narrative);
    setLoading(false);
}"""

new_load = """async function handleLoad() {
    const slot = 1;
    // 优先从 localStorage 读档
    const saved = localStorage.getItem('killer_boss_save_' + slot);
    if (saved) {
        try {
            const savedState = JSON.parse(saved);
            // 恢复状态但不覆盖 gameStarted 和 session 相关
            if (savedState.hitmen) STATE = savedState;
            gameStarted = true;
            updateStats(savedState);
            // 隐藏启动画面
            dom.startScreen.classList.add('hidden');
            dom.gameUI.classList.remove('hidden');
            // 清理启动画面按钮状态
            dom.btnStart.disabled = false;
            appendNarrative('\u{1F4C2} \u4ECE\u672C\u5730\u8BFB\u53D6\u5B58\u6863\u6210\u529F', 'narrative');
            showToast('\u8BFB\u6863\u6210\u529F \u2705');
            setLoading(false);
            return;
        } catch(e) {
            appendNarrative('\u26A0\uFE0F \u8BFB\u6863\u5931\u8D25\uFF1A' + e.message, 'system');
        }
    }
    // localStorage 没有，尝试服务端
    const data = await apiCall('load', { slot });
    if (data) {
        updateUI(data.state, data.narrative);
    } else {
        showToast('\u6CA1\u6709\u627E\u5230\u5B58\u6863 \u274C');
    }
    setLoading(false);
}"""

content = content.replace(old_load, new_load, 1)
print('2. handleLoad OK')

with open('frontend/script.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('DONE')
