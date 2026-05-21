with open('frontend/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Insert localStorage save BEFORE the existing save logic
old_save = "async function handleSave() {\n    const slot = 1;\n    const data = await apiCall('save', { slot });"
new_save = "async function handleSave() {\n    const slot = 1;\n    // localStorage存档\n    try {\n        localStorage.setItem('killer_boss_save_' + slot, JSON.stringify(STATE));\n        showToast('\\u5B58\\u6863\\u6210\\u529F \\u2705');\n    } catch(e) {}\n    const data = await apiCall('save', { slot });"

content = content.replace(old_save, new_save, 1)
print('1. handleSave injected')

# Insert localStorage load BEFORE the existing load logic
old_load = "async function handleLoad() {\n    const savesResp = await apiCall('list_saves');\n    if (!savesResp) return;\n    const saves = savesResp.extra?.saves || [];\n    if (saves.length === 0) {\n        showToast('\\u6CA1\\u6709\\u627E\\u5230\\u5B58\\u6863 \\u274C');\n        setLoading(false);\n        return;\n    }"
new_load = "async function handleLoad() {\n    const slot = 1;\n    try {\n        const saved = localStorage.getItem('killer_boss_save_' + slot);\n        if (saved) {\n            const st = JSON.parse(saved);\n            if (st && st.hitmen) {\n                STATE = st; gameStarted = true;\n                updateStats(st);\n                dom.startScreen.classList.add('hidden');\n                dom.gameUI.classList.remove('hidden');\n                appendNarrative('\\u{1F4C2} \\u8BFB\\u6863\\u6210\\u529F', 'narrative');\n                setLoading(false); return;\n            }\n        }\n    } catch(e) {}\n    const savesResp = await apiCall('list_saves');\n    if (!savesResp) return;\n    const saves = savesResp.extra?.saves || [];\n    if (saves.length === 0) {\n        showToast('\\u6CA1\\u6709\\u627E\\u5230\\u5B58\\u6863 \\u274C');\n        setLoading(false);\n        return;\n    }"

content = content.replace(old_load, new_load, 1)
print('2. handleLoad injected')

with open('frontend/script.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('DONE')
