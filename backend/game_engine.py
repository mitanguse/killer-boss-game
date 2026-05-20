"""
杀手组织老板模拟器 v2 — 核心游戏引擎
管理游戏状态 + DeepSeek AI 叙事生成
"""

import os
import json
import random
import re
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / '.env')

# ============================================================
# 数据池
# ============================================================

HITMAN_NAMES = [
    "陈默", "李寒", "周影", "赵刃", "孙雀",
    "吴镜", "郑鹄", "王蛇", "冯骨", "褚鸦",
    "沈鸢", "韩隼", "秦鸢", "陆蝎", "顾鸦",
]

SPECIALTIES = ["潜入", "狙击", "近战", "爆破", "黑客"]
SPECIALTY_EN = {
    "潜入": "infiltration",
    "狙击": "sniper",
    "近战": "close_combat",
    "爆破": "demolition",
    "黑客": "hacker",
}

DIFFICULTIES = ["简单", "中等", "困难", "致命"]

CONTRACT_TEMPLATES = [
    # (name, difficulty, specialty, base_reward, rep_req)
    ("夜间潜入取证", "简单", "潜入", 4000, 0),
    ("目标跟踪报告", "简单", "潜入", 3000, 0),
    ("警告任务", "简单", "近战", 5000, 0),
    ("催收债务", "简单", "近战", 3500, 0),
    ("数据窃取", "简单", "黑客", 4500, 0),

    ("资产清算", "中等", "近战", 10000, 15),
    ("信息窃取", "中等", "黑客", 9000, 10),
    ("保护证人", "中等", "狙击", 12000, 15),
    ("定点清除", "中等", "狙击", 11000, 12),
    ("仓库突袭", "中等", "爆破", 10000, 10),
    ("监听安装", "中等", "潜入", 8000, 12),

    ("双面间谍清除", "困难", "狙击", 22000, 30),
    ("走私网络瓦解", "困难", "爆破", 20000, 25),
    ("政要勒索材料", "困难", "潜入", 25000, 28),
    ("暗网据点攻破", "困难", "黑客", 18000, 25),
    ("安全屋突袭", "困难", "近战", 20000, 28),

    ("跨国暗杀", "致命", "狙击", 45000, 50),
    ("地下基地突袭", "致命", "爆破", 50000, 55),
    ("组织颠覆行动", "致命", "潜入", 55000, 60),
    ("核心防火墙突破", "致命", "黑客", 40000, 50),
    ("斩首行动", "致命", "近战", 48000, 55),
]

# ============================================================
# 武器数据
# ============================================================

WEAPON_TYPES = ["手枪", "狙击枪", "匕首", "炸药", "黑客设备"]
WEAPON_NAMES = {
    "手枪": ["格洛克-17", "伯莱塔M9", "CZ-75", "P226", "沙漠之鹰"],
    "狙击枪": ["AWM", "SVD", "M24", "巴雷特M82", "PSG-1"],
    "匕首": ["蝴蝶刀", "战术直刀", "爪刀", "军刺", "伞兵刀"],
    "炸药": ["C4塑胶炸药", "手雷", "闪光弹", "燃烧瓶", "地雷"],
    "黑客设备": ["破解终端", "信号干扰器", "数据采集器", "加密狗", "无人机"],
}
RARITIES = ["普通", "精良", "稀有", "传说"]
RARITY_BONUS = {"普通": 0, "精良": 1, "稀有": 2, "传说": 4}
RARITY_PRICE = {"普通": 3000, "精良": 8000, "稀有": 18000, "传说": 40000}
RARITY_REP = {"普通": 0, "精良": 5, "稀有": 20, "传说": 45}

# ============================================================
# 训练数据
# ============================================================

TRAINING_OPTIONS = [
    {"id": "phys", "name": "体能训练", "cost": 4000, "ap": 1, "desc": "提升基础体能，战力+1", "effect": ("skill", 1)},
    {"id": "shoot", "name": "射击训练", "cost": 7000, "ap": 1, "desc": "提升射击精度，战力+1", "effect": ("skill", 1), "min_lv": 2},
    {"id": "stealth", "name": "潜入训练", "cost": 10000, "ap": 2, "desc": "提升潜行技巧，战力+2", "effect": ("skill", 2), "min_lv": 3},
    {"id": "loyalty", "name": "忠诚培养", "cost": 3000, "ap": 1, "desc": "提升组织忠诚度，忠诚+1", "effect": ("loyalty", 1)},
    {"id": "combat", "name": "实战特训", "cost": 15000, "ap": 2, "desc": "高强度实战模拟，战力+3", "effect": ("skill", 3), "min_lv": 4},
]

EVENTS = [
    {
        "type": "competitor",
        "title": "⚔️ 竞争对手挑衅",
        "effect": {"reputation": -5},
        "narrative_hint": "竞争对手挑衅",
    },
    {
        "type": "police",
        "title": "🚔 警方调查风声",
        "effect": {"reputation": -3},
        "narrative_hint": "警方调查",
    },
    {
        "type": "gang_party",
        "title": "🥂 黑道聚会邀请",
        "effect": {"funds": -5000, "reputation": 5},
        "narrative_hint": "黑道聚会",
    },
    {
        "type": "opportunity",
        "title": "💡 意外机遇",
        "effect": {"funds": 8000},
        "narrative_hint": "意外机遇",
    },
    {
        "type": "intel",
        "title": "📄 灰色情报",
        "effect": {"reputation": 3},
        "narrative_hint": "灰色情报",
    },
    {
        "type": "poach",
        "title": "🎣 杀手挖角传闻",
        "effect": {},
        "narrative_hint": "杀手挖角传闻",
        "special": "poach_check",
    },
    {
        "type": "windfall",
        "title": "💎 意外横财",
        "effect": {"funds": 15000},
        "narrative_hint": "意外横财",
    },
    {
        "type": "tax",
        "title": "💸 地下抽成",
        "effect": {"funds": -8000},
        "narrative_hint": "地下抽成",
    },
]


# ============================================================
# 游戏引擎
# ============================================================

class GameEngine:
    def __init__(self, system_prompt: str):
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )
        self.system_prompt = system_prompt
        self.game_state = {
            "funds": 50000,
            "reputation": 10,
            "max_reputation": 100,
            "ap": 3,
            "max_ap": 3,
            "day": 1,
            "hitmen": [],
            "contracts": [],
            "weapons": self._generate_weapons(8),
            "history": [],
            "game_over": False,
        }
        self._action_context = {}
        self._weapon_id_counter = 100
        self.used_names = set()

    # ---- 状态管理 ----

    def reset_game(self):
        self.game_state = {
            "funds": 50000,
            "reputation": 10,
            "max_reputation": 100,
            "ap": 3,
            "max_ap": 3,
            "day": 1,
            "hitmen": [],
            "contracts": [],
            "weapons": self._generate_weapons(8),
            "history": [],
            "game_over": False,
        }
        self._action_context = {}
        self._weapon_id_counter = 100
        self.used_names = set()

    def get_state(self):
        """返回面向前端的游戏状态"""
        if self.game_state is None:
            self.reset_game()
        return dict(self.game_state)

    def _get_state_summary(self) -> str:
        """生成给 AI 看的当前状态摘要"""
        s = self.game_state
        lines = [
            f"日期：第 {s['day']} 天",
            f"资金：¥{s['funds']}",
            f"声望：{s['reputation']}/{s['max_reputation']}",
            f"行动力：{s['ap']}/{s['max_ap']}",
            f"杀手数量：{len(s['hitmen'])} 人",
        ]
        if s["hitmen"]:
            lines.append("杀手列表：")
            for h in s["hitmen"]:
                lines.append(
                    f"  - {h['name']} | 专长:{h['specialty']} "
                    f"| 忠诚:{h['loyalty']}/10 "
                    f"| 月薪:¥{h['salary']} "
                    f"| 战力:{h['skill']}/5 "
                    f"| 状态:{h['status']}"
                )
        return "\n".join(lines)

    # ---- 数据生成 ----

    def _random_name(self):
        """生成不重复的杀手名字"""
        pool = [n for n in HITMAN_NAMES if n not in self.used_names]
        if not pool:
            pool = HITMAN_NAMES
        name = random.choice(pool)
        self.used_names.add(name)
        return name

    def _generate_hitman(self, skill_level=None):
        """生成一个随机杀手（含等级、经验、武器栏）"""
        if skill_level is None:
            skill_level = random.choices([1, 2, 3, 4, 5], weights=[25, 30, 25, 15, 5])[0]
        specialty = random.choice(SPECIALTIES)
        loyalty = random.randint(4, 9)
        salary = 3000 + skill_level * 2000
        return {
            "id": random.randint(10000, 99999),
            "name": self._random_name(),
            "specialty": specialty,
            "loyalty": loyalty,
            "salary": salary,
            "skill": skill_level,
            "lv": 1,
            "exp": 0,
            "weapon_id": None,
            "missions_completed": 0,
            "status": "idle",
        }

    def _generate_contracts(self, count=3):
        """生成一组随机契约"""
        rep = self.game_state["reputation"]
        templates = [t for t in CONTRACT_TEMPLATES if t[4] <= rep]
        if len(templates) < count:
            templates = CONTRACT_TEMPLATES
        selected = random.sample(templates, min(count, len(templates)))
        contracts = []
        for i, (name, diff, spec, base_reward, rep_req) in enumerate(selected):
            reward_variance = random.randint(-2000, 2000)
            reward = max(1000, base_reward + reward_variance)
            contracts.append({
                "id": i + 1,
                "name": name,
                "difficulty": diff,
                "required_specialty": spec,
                "reputation_req": rep_req,
                "reward": reward,
                "taken": False,
            })
        return contracts

    def _generate_recruit_candidates(self, count=3):
        """生成招募候选人"""
        candidates = []
        for _ in range(count):
            skill = random.choices([1, 2, 3, 4, 5], weights=[20, 30, 30, 15, 5])[0]
            recruitment_cost = 8000 + skill * 4000
            h = self._generate_hitman(skill)
            candidates.append({
                "index": len(candidates),
                "name": h["name"],
                "specialty": h["specialty"],
                "skill": h["skill"],
                "loyalty": h["loyalty"],
                "salary": h["salary"],
                "recruitment_cost": recruitment_cost,
            })
        return candidates

    def _check_poach(self):
        """检查是否有杀手被挖角"""
        hitmen = self.game_state["hitmen"]
        if not hitmen:
            return None
        # 忠诚度低的更容易被挖
        targets = [h for h in hitmen if h["loyalty"] <= 5]
        if not targets:
            return None
        if random.random() < 0.4:  # 40%概率触发
            target = random.choice(targets)
            if random.random() < (0.6 - target["loyalty"] * 0.1):
                # 被挖走了
                self.game_state["hitmen"].remove(target)
                return target
        return None

    def _trigger_random_event(self):
        """触发随机事件，返回事件信息"""
        event_template = random.choice(EVENTS)
        event = dict(event_template)

        # 应用效果
        for key, val in event["effect"].items():
            self._modify_state(key, val)

        # 特别事件处理
        if event.get("special") == "poach_check":
            poached = self._check_poach()
            if poached:
                event["poached"] = poached
            else:
                event["no_effect"] = True

        return event

    def _modify_state(self, key, amount):
        """安全地修改游戏状态，带范围限制"""
        if key == "funds":
            self.game_state["funds"] = max(0, self.game_state["funds"] + amount)
            if self.game_state["funds"] <= 0:
                self.game_state["game_over"] = True
        elif key == "reputation":
            self.game_state["reputation"] = max(
                0, min(self.game_state["max_reputation"],
                       self.game_state["reputation"] + amount)
            )
        elif key == "ap":
            self.game_state["ap"] = max(
                0, min(self.game_state["max_ap"],
                       self.game_state["ap"] + amount)
            )
        else:
            self.game_state[key] = self.game_state.get(key, 0) + amount

    # ---- 存档系统 ----

    def save_game(self, slot: int = 1) -> dict:
        """保存游戏到文件"""
        save_dir = BASE_DIR / "saves"
        save_dir.mkdir(exist_ok=True)
        save_path = save_dir / f"save_{slot}.json"

        save_data = {
            "slot": slot,
            "timestamp": str(Path(__file__).stat().st_mtime),  # 写死的兼容写法
            "state": self.game_state,
            "used_names": list(self.used_names),
        }

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        return {"slot": slot, "day": self.game_state["day"], "funds": self.game_state["funds"]}

    def load_game(self, slot: int = 1) -> bool:
        """从文件读取存档"""
        save_path = BASE_DIR / "saves" / f"save_{slot}.json"
        if not save_path.exists():
            return False

        with open(save_path, "r", encoding="utf-8") as f:
            save_data = json.load(f)

        self.game_state = save_data["state"]
        self.used_names = set(save_data.get("used_names", []))
        self._action_context = {}
        return True

    def list_saves(self) -> list:
        """列出所有存档"""
        save_dir = BASE_DIR / "saves"
        if not save_dir.exists():
            return []
        saves = []
        for f in sorted(save_dir.glob("save_*.json")):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                saves.append({
                    "slot": data["slot"],
                    "day": data["state"]["day"],
                    "funds": data["state"]["funds"],
                    "reputation": data["state"]["reputation"],
                })
            except Exception:
                continue
        return saves

    # ---- 核心操作 ----

    def start_game(self):
        """初始化并开始新游戏"""
        self.reset_game()
        self.game_state["contracts"] = self._generate_contracts(3)
        narrative = self._call_ai("start", "游戏开场")
        return narrative

    def show_recruit_candidates(self):
        """显示可招募的候选人（直接返回，不调 AI）"""
        if self.game_state["ap"] <= 0:
            return None, "今天的行动力已经用完了，明天再来招募吧。"
        candidates = self._generate_recruit_candidates(3)
        self._action_context["candidates"] = candidates
        names = "、".join([c["name"] for c in candidates])
        narrative = f"枭带来了三份档案：{names}。\n看看他们的资料吧。"
        return candidates, narrative

    def hire_candidate(self, candidate_index: int):
        """招募指定的候选人"""
        candidates = self._action_context.get("candidates", [])
        if not candidates or candidate_index < 0 or candidate_index >= len(candidates):
            return "数据异常，请重新尝试招募。", None

        candidate = candidates[candidate_index]
        cost = candidate["recruitment_cost"]

        if self.game_state["funds"] < cost:
            narrative = self._call_ai("recruit_denied", f"资金不足，招募{candidate['name']}需要¥{cost}")
            return narrative, None

        if self.game_state["ap"] <= 0:
            return "今天的行动力不够了。", None

        # 扣钱、加人、扣AP
        self._modify_state("funds", -cost)
        self._modify_state("ap", -1)

        new_hitman = {
            "id": random.randint(10000, 99999),
            "name": candidate["name"],
            "specialty": candidate["specialty"],
            "loyalty": candidate["loyalty"],
            "salary": candidate["salary"],
            "skill": candidate["skill"],
            "lv": 1,
            "exp": 0,
            "weapon_id": None,
            "missions_completed": 0,
            "status": "idle",
        }
        self.game_state["hitmen"].append(new_hitman)

        narrative = self._call_ai(
            "hire",
            f"招募成功：{candidate['name']}（{candidate['specialty']}，战力{candidate['skill']}）"
        )
        self._action_context.pop("candidates", None)
        return narrative, new_hitman

    def show_contracts(self):
        """展示当前契约板（直接返回，不调 AI）"""
        contracts = self.game_state["contracts"]
        available = [c for c in contracts if not c.get("taken")]
        if not available:
            return [], "老板，今天的契约板是空的……真少见。"
        narrative = f"枭递来一份契约清单：\n"
        narrative += f"当前有 {len(available)} 个可用契约，难度从简单到致命不等。"
        return available, narrative

    def assign_contract(self, contract_index: int, hitman_id: int):
        """派遣杀手执行契约"""
        contracts = self.game_state["contracts"]
        if contract_index < 0 or contract_index >= len(contracts):
            return "无效的契约。", False

        contract = contracts[contract_index]
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
            f"结果：{'✅ 成功' if success else '❌ 失败'}，"
            f"获得报酬：¥{contract['reward'] if success else 0}"
        )
        narrative = self._call_ai("assign_contract", context)

        # 检查游戏结束
        if self.game_state["reputation"] <= 0:
            game_over_narrative = self._call_ai("game_over", "声望归零，组织覆灭")
            self.game_state["game_over"] = True
            self.game_state["history"].append({
                "type": "game_over", "text": game_over_narrative,
            })
            return f"{narrative}\n\n{game_over_narrative}", success

        return narrative, success

    def fire_hitman(self, hitman_id: int):
        """解雇杀手"""
        hitman = None
        for h in self.game_state["hitmen"]:
            if h["id"] == hitman_id:
                hitman = h
                break
        if not hitman:
            return "找不到这个杀手。"

        if hitman["status"] == "on_mission":
            return "这个杀手正在执行任务，不能解雇。"

        self.game_state["hitmen"].remove(hitman)

        if self.game_state["ap"] <= 0:
            return "行动力不够了。"

        self._modify_state("ap", -1)

        reputation_change = -hitman["skill"]  # 解雇高手影响声望
        self._modify_state("reputation", reputation_change)

        narrative = self._call_ai(
            "fire_result",
            f"解雇了杀手{hitman['name']}（{hitman['specialty']}，战力{hitman['skill']}）"
        )
        return narrative

    def end_day(self):
        """结束当天，推进到第二天"""
        # 保存旧天数用于比较
        old_day = self.game_state["day"]

        # 发工资
        total_salary = sum(h["salary"] for h in self.game_state["hitmen"] if h["status"] != "dead")
        salary_narrative = ""
        if total_salary > 0:
            self._modify_state("funds", -total_salary)
            salary_narrative = f"发放工资 ¥{total_salary}。"

        # 触发随机事件
        event = self._trigger_random_event()
        event_narrative_hint = event.get("narrative_hint", "")

        # 恢复受伤杀手
        for h in self.game_state["hitmen"]:
            if h["status"] == "injured":
                h["status"] = "idle"

        # 刷新契约板
        self.game_state["contracts"] = self._generate_contracts(3)

        # 恢复AP
        self.game_state["ap"] = self.game_state["max_ap"]
        self.game_state["day"] += 1

        # 生成叙事
        context = (
            f"第{old_day}天结束。{salary_narrative} "
            f"触发事件：{event_narrative_hint}。"
            f"进入第{self.game_state['day']}天。"
            f"当前资金：¥{self.game_state['funds']}，声望：{self.game_state['reputation']}"
        )
        narrative = self._call_ai("end_day", context)

        # 添加事件详情
        if event.get("poached"):
            narrative += f"\n\n⚠️ {event['poached']['name']} 被竞争对手挖走了！"
        elif event.get("no_effect"):
            narrative += "\n\n所幸没有重大损失。"

        # 检查游戏结束
        if self.game_state["funds"] <= 0 or self.game_state["reputation"] <= 0:
            game_over = self._call_ai("game_over", "组织覆灭")
            self.game_state["game_over"] = True
            narrative += f"\n\n{game_over}"

        return narrative, event

    # ---- AI 叙事生成 ----

    # ---- 武器系统 ----

    def _generate_weapons(self, count=8):
        """生成武器商店的初始库存"""
        weapons = []
        for _ in range(count):
            wtype = random.choice(list(WEAPON_NAMES.keys()))
            wname = random.choice(WEAPON_NAMES[wtype])
            rarity = random.choices(RARITIES, weights=[40, 30, 20, 10])[0]
            self._weapon_id_counter += 1
            weapons.append({
                "id": self._weapon_id_counter,
                "name": wname,
                "type": wtype,
                "rarity": rarity,
                "bonus": RARITY_BONUS[rarity],
                "price": RARITY_PRICE[rarity],
                "rep_required": RARITY_REP[rarity],
                "owned": False,
                "equipped_by": None,
            })
        return weapons

    def show_weapon_shop(self):
        """展示武器商店"""
        available = [w for w in self.game_state["weapons"] if not w["owned"]]
        if not available:
            return [], "枭摇了摇头：'老板，武器商这边暂时没货了。'"
        return available, f"枭推了推桌上的武器清单：'这是黑市上能搞到的好货。'"

    def buy_weapon(self, weapon_id: int):
        """购买武器"""
        if self.game_state["ap"] <= 0:
            return "行动力不够，下次吧。"
        weapon = None
        for w in self.game_state["weapons"]:
            if w["id"] == weapon_id and not w["owned"]:
                weapon = w
                break
        if not weapon:
            return "找不到这件武器。"
        if self.game_state["funds"] < weapon["price"]:
            return f"资金不够，{weapon['name']} 需要 ¥{weapon['price']}。"
        if self.game_state["reputation"] < weapon["rep_required"]:
            return f"声望不够，需要 {weapon['rep_required']} 声望才能购买{weapon['name']}。"
        self._modify_state("funds", -weapon["price"])
        self._modify_state("ap", -1)
        weapon["owned"] = True
        return f"购买成功！{weapon['name']}（{weapon['rarity']}）已入库。"

    def equip_weapon(self, hitman_id: int, weapon_id: int):
        """给杀手装备武器"""
        hitman = None
        for h in self.game_state["hitmen"]:
            if h["id"] == hitman_id:
                hitman = h
                break
        if not hitman:
            return "找不到这个杀手。"
        weapon = None
        for w in self.game_state["weapons"]:
            if w["id"] == weapon_id and w["owned"]:
                weapon = w
                break
        if not weapon:
            return "找不到这件武器。"
        # 先卸下当前装备的武器
        if hitman["weapon_id"]:
            for w in self.game_state["weapons"]:
                if w["id"] == hitman["weapon_id"]:
                    w["equipped_by"] = None
        weapon["equipped_by"] = hitman["id"]
        hitman["weapon_id"] = weapon["id"]
        return f"{hitman['name']} 已装备 {weapon['name']}（战力+{weapon['bonus']}）。"

    def unequip_weapon(self, hitman_id: int):
        """卸下杀手武器"""
        hitman = None
        for h in self.game_state["hitmen"]:
            if h["id"] == hitman_id:
                hitman = h
                break
        if not hitman or not hitman["weapon_id"]:
            return "这个杀手没有装备武器。"
        for w in self.game_state["weapons"]:
            if w["id"] == hitman["weapon_id"]:
                w["equipped_by"] = None
                break
        hitman["weapon_id"] = None
        return f"已从 {hitman['name']} 身上卸下武器。"

    def show_training(self):
        """展示训练选项"""
        if self.game_state["ap"] <= 0:
            return [], "今天的行动力不够了，明天再练吧。"
        hitmen = [h for h in self.game_state["hitmen"] if h["status"] == "idle"]
        if not hitmen:
            return [], "没有空闲的杀手可以训练。"
        return TRAINING_OPTIONS, "枭拿出一份训练清单：'该让这些人活动活动筋骨了。'"

    def do_training(self, training_id: str, hitman_id: int):
        """执行训练"""
        hitman = None
        for h in self.game_state["hitmen"]:
            if h["id"] == hitman_id and h["status"] == "idle":
                hitman = h
                break
        if not hitman:
            return "找不到这个杀手，或者他正在执行任务。"
        training = None
        for t in TRAINING_OPTIONS:
            if t["id"] == training_id:
                training = t
                break
        if not training:
            return "无效的训练项目。"
        if hitman["lv"] < training.get("min_lv", 1):
            return f"{hitman['name']} 等级不够（需要 Lv.{training['min_lv']}），先练点基础的吧。"
        if self.game_state["funds"] < training["cost"]:
            return f"资金不够，{training['name']} 需要 ¥{training['cost']}。"
        if self.game_state["ap"] < training["ap"]:
            return "行动力不够完成这项训练。"
        self._modify_state("funds", -training["cost"])
        self._modify_state("ap", -training["ap"])
        attr, amount = training["effect"]
        if attr == "skill":
            hitman["skill"] = min(10, hitman["skill"] + amount)
        elif attr == "loyalty":
            hitman["loyalty"] = min(10, hitman["loyalty"] + amount)
        # 获得经验
        exp_gain = training["ap"] * 20
        hitman["exp"] += exp_gain
        self._check_level_up(hitman)
        return f"{hitman['name']} 完成了{training['name']}，{attr} +{amount}，经验 +{exp_gain}。"

    def _check_level_up(self, hitman):
        """检查杀手升级"""
        needed = hitman["lv"] * 50
        while hitman["exp"] >= needed:
            hitman["exp"] -= needed
            hitman["lv"] += 1
            hitman["skill"] = min(10, hitman["skill"] + 1)
            needed = hitman["lv"] * 50

    def _call_ai(self, scene_type: str, context: str) -> str:
        """调用 DeepSeek 生成叙事"""
        summary = self._get_state_summary()
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": f"【当前游戏状态】\n{summary}"},
            {"role": "user", "content": f"场景类型：{scene_type}\n上下文：{context}\n\n请根据场景类型和上下文，生成一段沉浸式的叙事文本。"},
        ]

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.85,
                max_tokens=512,
            )
            text = response.choices[0].message.content.strip()
        except Exception as e:
            text = f"（枭的通讯似乎受到了干扰……）\n[系统提示：AI 调用失败 - {str(e)}]"

        self.game_state["history"].append({
            "type": "narrative",
            "text": text,
            "scene": scene_type,
        })
        return text
