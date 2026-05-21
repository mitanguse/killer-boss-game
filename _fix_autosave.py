with open('frontend/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Add auto-save to localStorage at the end of updateStats
old = """    // Buttons
    updateButtons(state);
}"""

new = """    // Buttons
    updateButtons(state);
    // 自动存到 localStorage（防 Render 重启丢数据）
    try { localStorage.setItem('killer_boss_autosave', JSON.stringify(state)); } catch(e) {}
}"""

content = content.replace(old, new, 1)
print('1. auto-save in updateStats')

# On page load, auto-restore from localStorage
old2 = """console.log('\\u{1F5E1}\\uFE0F \\u6740\\u624B\\u7EC4\\u7EC7\\u8001\\u677F\\u6A21\\u62DF\\u5668 v2 loaded');
console.log('\\u{1F4A1} \\u4F7F\\u7528\\u7EAF\\u6309\\u94AE\\u64CD\\u4F5C\\uFF0C\\u5F00\\u542F\\u4F60\\u7684\\u6697\\u9762\\u5E1D\\u56FD\\u5427');"""

new2 = """console.log('\\u{1F5E1}\\uFE0F \\u6740\\u624B\\u7EC4\\u7EC7\\u8001\\u677F\\u6A21\\u62DF\\u5668 v2 loaded');
console.log('\\u{1F4A1} \\u4F7F\\u7528\\u7EAF\\u6309\\u94AE\\u64CD\\u4F5C\\uFF0C\\u5F00\\u542F\\u4F60\\u7684\\u6697\\u9762\\u5E1D\\u56FD\\u5427');

// 尝试从 localStorage 恢复游戏状态
try {
    const saved = localStorage.getItem('killer_boss_autosave');
    if (saved) {
        const st = JSON.parse(saved);
        if (st && st.day > 1 && st.hitmen && st.hitmen.length > 0) {
            STATE = st;
            gameStarted = true;
            setTimeout(function() {
                dom.startScreen.classList.add('hidden');
                dom.gameUI.classList.remove('hidden');
                updateStats(st);
                appendNarrative('\\u{1F4C2} \\u6062\\u590D\\u5230\\u7B2C' + st.day + '\\u5929\\uFF08\\u672C\\u5730\\u7F13\\u5B58\\uFF09', 'system');
            }, 100);
        }
    }
} catch(e) {}
"""

content = content.replace(old2, new2, 1)
print('2. auto-restore on page load')

with open('frontend/script.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('DONE')
