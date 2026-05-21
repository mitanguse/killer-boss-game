with open('frontend/script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Add _pendingContracts variable
old_init = 'let modalState = null;     // 模态框状态: null | \'contracts\' | \'recruit\' | \'assign\''
new_init = 'let modalState = null;     // 模态框状态: null | \'contracts\' | \'recruit\' | \'assign\'\nlet _pendingContracts = null; // 当前显示的可用契约列表'
content = content.replace(old_init, new_init, 1)
print('1. _pendingContracts var OK')

# Fix handleShowContracts: store available contracts
old_show = '''    let html = '<p style="margin-bottom:12px;color:var(--text-secondary);">选择要执行的契约：</p>';
    contracts.forEach((c, idx) => {'''
new_show = '''    _pendingContracts = contracts;
    let html = '<p style="margin-bottom:12px;color:var(--text-secondary);">选择要执行的契约：</p>';
    contracts.forEach((c, idx) => {'''
content = content.replace(old_show, new_show, 1)
print('2. store _pendingContracts OK')

# Fix handleAssignContract: use _pendingContracts instead of STATE.contracts
old_assign = '''    const contract = STATE.contracts[contractIndex];'''
new_assign = '''    const available = _pendingContracts || [];
    const contract = available[contractIndex];
    if (!contract) { appendNarrative('契约数据异常。', 'system'); closeModal(); return; }'''
content = content.replace(old_assign, new_assign, 1)
print('3. handleAssignContract fix OK')

# Fix executeAssign: pass contract id
old_exec = '''async function executeAssign(contractIndex, hitmanId) {
    closeModal();
    const data = await apiCall('assign_contract', { contract_index: contractIndex, hitman_id: hitmanId });'''
new_exec = '''async function executeAssign(contractIndex, hitmanId) {
    closeModal();
    const available = _pendingContracts || [];
    const contract = available[contractIndex];
    if (!contract) { appendNarrative('契约数据异常。', 'system'); return; }
    const data = await apiCall('assign_contract', { contract_id: contract.id, hitman_id: hitmanId });'''
content = content.replace(old_exec, new_exec, 1)
print('4. executeAssign pass contract_id OK')

with open('frontend/script.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('DONE')
