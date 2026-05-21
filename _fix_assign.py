with open('backend/game_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the entire assign_contract function
idx = content.find('def assign_contract(self, contract_index: int, hitman_id: int):')
end = content.find('    def show_contracts', idx)
if idx < 0 or end < 0:
    print('FAIL - could not find function')
    exit(1)

old_func = content[idx:end]

new_func = '''    def assign_contract(self, contract_index=None, hitman_id=None, contract_id=None):
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
            # 按可用列表的 index 查
            available = [c for c in contracts if not c.get("taken")]
            if contract_index is None or contract_index < 0 or contract_index >= len(available):
                return "无效的契约。", False
            contract = available[contract_index]

        if contract.get("taken"):
            return "这个契约已经被执行了。", False

        # 找杀手
        hitman = None
        for h in self.game_state["hitmen"]:
            if h["id"] == hitman_id and h["status"] == "idle":
                hitman = h
                break
        if not hitman:
            return "找不到这个杀手，或者他已经在执行任务了。", False

        if self.game_state["ap"] <= 0:
            return "行动力不够了。", False

        if self.game_state["reputation"] < contract["reputation_req"]:
            return f"声望不够，需要有 {contract['reputation_req']} 声望才能接这个契约。", False

        # 扣AP
        self._modify_state("ap", -1)

        # 计算成功率
        base_success = 0.3
        specialty_bonus = 0.2 if hitman["specialty"] == contract["required_specialty"] else 0
        skill_bonus = hitman["skill"] * 0.08
        diff_penalty = {"简单": 0, "中等": -0.1, "困难": -0.25, "致命": -0.4}
        penalty = diff_penalty.get(contract["difficulty"], 0)

        success_rate = base_success + specialty_bonus + skill_bonus + penalty
        success_rate = max(0.1, min(0.95, success_rate))

        diced = random.random()
        success = diced < success_rate

        # 更新状态
        contract["taken"] = True
        if success:
            self._modify_state("funds", contract["reward"])
            rep_gain = {"简单": 2, "中等": 4, "困难": 7, "致命": 12}
            self._modify_state("reputation", rep_gain.get(contract["difficulty"], 3))
            hitman["status"] = "idle"
            # 任务经验
            exp_gain = {"简单": 20, "中等": 40, "困难": 80, "致命": 150}
            hitman["exp"] = hitman.get("exp", 0) + exp_gain.get(contract["difficulty"], 20)
            hitman["missions_completed"] = hitman.get("missions_completed", 0) + 1
            self._check_level_up(hitman)
            # 忠诚度可能上升
            if random.random() < 0.3:
                hitman["loyalty"] = min(10, hitman["loyalty"] + 1)
        else:
            rep_loss = {"简单": -1, "中等": -2, "困难": -4, "致命": -8}
            self._modify_state("reputation", rep_loss.get(contract["difficulty"], -2))
            # 杀手可能受伤
            if random.random() < 0.5:
                hitman["status"] = "injured"
            else:
                hitman["status"] = "idle"

        # 生成叙事
        context = (
            f"派遣{hitman['name']}执行契约「{contract['name']}」"
            f"（难度：{contract['difficulty']}，所需专长：{contract['required_specialty']}，"
            f"杀手专长：{hitman['specialty']}，成功率：{success_rate:.0%}）"
        )
        if success:
            narrative = self._call_ai("contract_success", context)
            hitman["activity_log"].append(f"完成任务：{contract['name']}")
        else:
            narrative = self._call_ai("contract_fail", context)
            hitman["activity_log"].append(f"任务失败：{contract['name']}")

        return narrative, success

'''

content = content[:idx] + new_func + content[end:]
with open('backend/game_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('OK')
