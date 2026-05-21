with open('backend/game_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('def assign_contract(self, contract_index: int, hitman_id: int):')
end = content.find('        # 找杀手', idx)
if idx < 0 or end < 0:
    print('FAIL')
    exit(1)

old_section = content[idx:end+50]

new_section = '''def assign_contract(self, contract_index=None, hitman_id=None, contract_id=None):
        """派遣杀手执行契约"""
        contracts = self.game_state["contracts"]
        if contract_id is not None:
            contract = None
            for c in contracts:
                if c["id"] == contract_id:
                    contract = c
                    break
            if not contract:
                return "找不到这个契约。", False
        else:
            available = [c for c in contracts if not c.get("taken")]
            if contract_index is None or contract_index < 0 or contract_index >= len(available):
                return "无效的契约。", False
            contract = available[contract_index]

        if contract.get("taken"):
            return "这个契约已经被执行了。", False

        # 找杀手'''

content = content.replace(old_section, new_section, 1)
with open('backend/game_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('OK')
