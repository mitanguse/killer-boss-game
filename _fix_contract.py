with open('backend/game_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix: assign_contract uses available-list index but looks up in full list
old = '''    def assign_contract(self, contract_index: int, hitman_id: int):
        """派遣杀手执行契约"""
        contracts = self.game_state["contracts"]
        if contract_index < 0 or contract_index >= len(contracts):
            return "无效的契约。", False

        contract = contracts[contract_index]
        if contract.get("taken"):
            return "这个契约已经被执行了。", False'''

new = '''    def assign_contract(self, contract_index: int, hitman_id: int):
        """派遣杀手执行契约"""
        contracts = self.game_state["contracts"]
        # 获取可用（未完成）的契约
        available = [c for c in contracts if not c.get("taken")]
        if contract_index < 0 or contract_index >= len(available):
            return "无效的契约。", False

        contract = available[contract_index]
        if contract.get("taken"):
            return "这个契约已经被执行了。", False'''

if old in content:
    content = content.replace(old, new, 1)
    print('1. assign_contract index fix OK')
else:
    print('1. FAIL')
    idx = content.find('def assign_contract')
    if idx >= 0:
        import json
        end = content.find('\n        contract = contracts[contract_index]')
        if end > 0:
            print('  Up to:', json.dumps(content[idx:end+45]))

with open('backend/game_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('DONE')
