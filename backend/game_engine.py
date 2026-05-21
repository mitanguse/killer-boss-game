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

# 排行榜 NPC 杀手（全服名人）
NPC_NAMES = [
    "血剑·无名", "影舞·白狐", "阎罗·黑煞", "霜刃·寒月",
    "雷音·破军", "夜枭·鬼面", "焚天·烈阳", "千面·妖姬",
    "无痕·绝影", "铁骨·金刚", "毒蜂·尾针", "幻瞳·魅影",
    "断罪·裁决", "锈刃·老兵", "弦月·弓藏",
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

# 刺杀目标: (目标简介, 难度, 推荐专长, 基础赏金, 声望要求)
CONTRACT_TEMPLATES = [
    # 简单 - 街头级别
    ("街头毒贩「马三」·最近在城南猖獗的毒贩，身边有两个马仔", "简单", "近战", 8000, 0),
    ("高利贷老板「钱四海」·专坑穷人的吸血鬼，放账收不回来就砍手", "简单", "近战", 10000, 0),
    ("偷渡蛇头「阿坤」·把偷渡客塞进集装箱，手上好几条人命", "简单", "潜入", 9000, 0),
    ("黑市医生「刘一刀」·给通缉犯做手术的黑医，知道太多秘密", "简单", "狙击", 8500, 0),
    ("街头眼线「耗子」·给警方当线人的小混混", "简单", "潜入", 7000, 0),

    # 中等 - 组织级别
    ("帮派头目「刀疤张」·城东斧头帮的二把手，贴身保镖四个", "中等", "狙击", 22000, 15),
    ("受贿法官「陈国栋」·收钱判案的黑法官，出行有警车护送", "中等", "潜入", 25000, 18),
    ("军火贩子「老虎」·往城里倒卖军火的大贩子，仓库有重火力", "中等", "爆破", 24000, 15),
    ("地下拳场老板「铁拳」·开黑拳赌场的狠人，手下全是打手", "中等", "近战", 20000, 12),
    ("勒索犯「笑脸」·专门敲诈富商，手里有大量机密照片", "中等", "黑客", 18000, 10),
    ("黑警队长「周铁军」·跟黑帮勾结的警察队长，配枪且警觉", "中等", "潜入", 23000, 16),

    # 困难 - 大人物级别
    ("地下钱庄老板「赵百万」·几十亿黑钱的操盘手，安保森严", "困难", "潜入", 45000, 32),
    ("敌对组织军师「白狐」·计谋多端的策略家，从不单独出行", "困难", "狙击", 50000, 35),
    ("腐败市长秘书「刘文远」·帮市长收黑钱的白手套，有贴身保镖", "困难", "潜入", 48000, 30),
    ("跨国毒枭「毒蛇」·金三角过来的大毒枭，私人武装一个排", "困难", "爆破", 55000, 35),
    ("暗网军火商「军火库」·卖重武器的暗网大商人，地址成谜", "困难", "黑客", 42000, 28),

    # 致命 - 传说级别
    ("黑帮教父「维克托」·横跨三国的黑手党头目，出行装甲车", "致命", "狙击", 90000, 55),
    ("暗网王者「幽灵」·操控整个暗网的黑客之王，身份无人知晓", "致命", "黑客", 80000, 50),
    ("前特工「影子」·叛逃的前国家特工，反暗杀训练满分", "致命", "潜入", 100000, 60),
    ("军政府将军「巴颂」·东南亚军政府实权人物，一整个军营保护", "致命", "爆破", 120000, 65),
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

# ============================================================
# 组织等级系统
# ============================================================

ORG_LEVELS = [
    {"level": 1, "name": "街头暗影", "funds_req": 0, "rep_req": 0, "missions_req": 0, "xp_req": 0, "desc": "刚起步的地下势力"},
    {"level": 2, "name": "区域新秀", "funds_req": 30000, "rep_req": 20, "missions_req": 5, "xp_req": 60, "desc": "在小圈子里有了名号"},
    {"level": 3, "name": "地下势力", "funds_req": 80000, "rep_req": 40, "missions_req": 15, "xp_req": 150, "desc": "暗面世界正式接纳了你"},
    {"level": 4, "name": "城市暗流", "funds_req": 150000, "rep_req": 60, "missions_req": 30, "xp_req": 300, "desc": "整座城市都能感受到你的存在"},
    {"level": 5, "name": "暗夜贵族", "funds_req": 300000, "rep_req": 80, "missions_req": 50, "xp_req": 500, "desc": "你是夜晚的真正主人"},
    {"level": 6, "name": "幕后操盘", "funds_req": 500000, "rep_req": 100, "missions_req": 80, "xp_req": 800, "desc": "你操纵着城市的命脉"},
    {"level": 7, "name": "暗影君王", "funds_req": 800000, "rep_req": 120, "missions_req": 120, "xp_req": 1200, "desc": "暗影中的无冕之王"},
    {"level": 8, "name": "传说", "funds_req": 1200000, "rep_req": 150, "missions_req": 180, "xp_req": 1800, "desc": "你的名字将成为传说"},
]

# ============================================================
# 安全屋升级
# ============================================================

SAFEHOUSE_UPGRADES = [
    {"id": "training_ground", "name": "训练场", "desc": "训练效果+50%", "base_cost": 20000, "max_lv": 3, "cost_per_lv": 15000},
    {"id": "medical_room", "name": "医疗室", "desc": "受伤恢复加速", "base_cost": 15000, "max_lv": 3, "cost_per_lv": 10000},
    {"id": "intel_room", "name": "情报室", "desc": "情报收集增加", "base_cost": 25000, "max_lv": 3, "cost_per_lv": 18000},
    {"id": "interrogation_room", "name": "审讯室", "desc": "从俘虏获取信息", "base_cost": 20000, "max_lv": 3, "cost_per_lv": 12000},
]

# ============================================================
# 合约多方案
# ============================================================

CONTRACT_PLANS = [
    {"id": "stealth", "name": "潜入暗杀", "desc": "需潜入专精，成功率+15%，收益正常", "req_spec": "潜入", "success_bonus": 0.15, "reward_mult": 1.0, "infamy": 0},
    {"id": "sniper", "name": "狙击暗杀", "desc": "需狙击专精，风险低，收益+20%", "req_spec": "狙击", "success_bonus": 0.20, "reward_mult": 1.2, "infamy": 0},
    {"id": "assault", "name": "正面强攻", "desc": "需近战专精，成功率-10%，收益+50%但恶名增加", "req_spec": "近战", "success_bonus": -0.10, "reward_mult": 1.5, "infamy": 5},
    {"id": "accident", "name": "制造意外", "desc": "需爆破专精，收益-20%，恶名不增加", "req_spec": "爆破", "success_bonus": 0.0, "reward_mult": 0.8, "infamy": -3},
]

# ============================================================
# 阵营声望
# ============================================================

FACTIONS = {
    "police": {"name": "警方", "desc": "高→不查你，低→经常突袭", "initial": 50, "max": 100},
    "gang": {"name": "黑帮", "desc": "高→更多合约，低→被攻击", "initial": 50, "max": 100},
    "politician": {"name": "政客", "desc": "高→政治庇护，低→被施压", "initial": 50, "max": 100},
}

# ============================================================
# 洗钱渠道
# ============================================================

LAUNDRY_CHANNELS = [
    {"id": "restaurant", "name": "开餐厅", "cost_per_batch": 5000, "ap_cost": 1, "clean_per_batch": 0.3, "desc": "每消耗¥5000+1AP，洗白30%脏钱"},
    {"id": "laundry_mat", "name": "洗衣店", "cost_per_batch": 8000, "ap_cost": 1, "clean_per_batch": 0.5, "desc": "每消耗¥8000+1AP，洗白50%脏钱"},
    {"id": "casino", "name": "地下赌场", "cost_per_batch": 15000, "ap_cost": 2, "clean_per_batch": 0.8, "desc": "每消耗¥15000+2AP，洗白80%脏钱"},
]

# ============================================================
# 投资项目
# ============================================================

INVESTMENT_TYPES = [
    {"id": "nightclub", "name": "夜总会", "min_invest": 50000, "weekly_return": 0.05, "risk": 0.1, "desc": "每周回报5%，低风险"},
    {"id": "casino_underground", "name": "地下赌场", "min_invest": 80000, "weekly_return": 0.08, "risk": 0.3, "desc": "每周回报8%，高风险"},
    {"id": "real_estate", "name": "房产", "min_invest": 100000, "weekly_return": 0.03, "risk": 0.05, "desc": "每周回报3%，极稳定"},
]

# ============================================================
# 干部职位
# ============================================================

CADRE_ROLES = [
    {"id": "intel_officer", "name": "情报官", "desc": "情报收集量+50%", "bonus_type": "intel"},
    {"id": "action_commander", "name": "行动队长", "desc": "合约成功率+10%", "bonus_type": "success"},
    {"id": "tech_expert", "name": "技术专家", "desc": "武器打八折", "bonus_type": "discount"},
    {"id": "logistics_manager", "name": "后勤主管", "desc": "维护费减少50%", "bonus_type": "maintenance"},
]

# ============================================================
# 主线剧情
# ============================================================

MAIN_STORIES = {
    2: {
        "title": "初次交锋",
        "text": "你的组织引起了其他势力的注意。一个自称「灰鸽」的组织送来了一封警告信——上面画着一只染血的鸽子。\n\n枭深吸一口气：「老板，他们有备而来。」\n\n该如何回应？",
        "choices": [
            {"text": "强硬回击——派人去砸他们的场子", "effect": {"reputation": 5, "factions_gang": -5}, "response": "你选择了强硬路线。当晚，灰鸽的赌场被砸了个稀巴烂。消息传开，道上的人都在谈论你的组织。"},
            {"text": "隐秘观察——先摸清他们的底细再说", "effect": {"reputation": 3, "factions_police": 3}, "response": "选择隐忍是明智的。一周后，枭的情报网挖出了灰鸽的底牌——他们不过是条大鱼抛出的诱饵。"},
        ],
    },
    3: {
        "title": "神秘委托",
        "text": "一封没有署名的信被塞进门缝，里面是一张照片和一串地址。照片上是一个你从未见过的符号——一只衔着金币的乌鸦。\n\n枭皱眉：「这单……不太对劲。」\n\n接还是不接？",
        "choices": [
            {"text": "接下来——高风险高回报", "effect": {"funds": 30000, "reputation": 8}, "response": "任务出奇地顺利。委托人留下了丰厚的报酬和一封信：「第一次合作愉快。」署名是一个字母：'X'。"},
            {"text": "拒绝——安全第一", "effect": {"reputation": 2}, "response": "你把信烧掉了。当天夜里，隔壁街的另一个组织接了这单——然后全员失踪。"},
        ],
    },
    4: {
        "title": "前任的秘密",
        "text": "在整理前任首领留下的旧物时，你发现了一个暗格。里面有一本日记和一叠照片——前任首领并非死于仇杀，而是被组织内部的人出卖。\n\n照片上，一个你熟悉的身影出现在不该出现的地方……\n\n你该怎么做？",
        "choices": [
            {"text": "彻查内鬼——一个都不放过", "effect": {"reputation": 5, "funds": -20000}, "response": "一场血腥的内部清洗开始了。三个叛徒被揪了出来，你的组织因此变得更加纯粹——但也元气大伤。"},
            {"text": "引以为戒——加强内部管理", "effect": {"reputation": 3, "factions_politician": 5}, "response": "你没有大动干戈，而是悄悄改革了组织的管理流程。枭赞许地点了点头：「老板长大了。」"},
        ],
    },
    5: {
        "title": "暗影议会的邀请",
        "text": "一张烫金请柬送到了你的桌上。城市的暗面统治者——暗影议会——希望与你见面。\n\n地点在城郊一座废弃教堂的地下室。去，意味着正式进入权力核心；不去，意味着你的天花板就在这里。\n\n枭看着你，等待你的决定。",
        "choices": [
            {"text": "赴约——进入权力核心", "effect": {"reputation": 10, "funds": 50000}, "response": "你走入了那座教堂。黑暗中，七张面具后的眼睛注视着你。『欢迎加入游戏。』暗影议会的领袖伸出了手。"},
            {"text": "拒绝——保持独立", "effect": {"reputation": 5, "factions_gang": 10}, "response": "你拒绝了邀请。暗影议会没有动怒——反而对你产生了兴趣。一个不靠任何人上位的组织，值得拉拢。"},
        ],
    },
    6: {
        "title": "城市议会选举",
        "text": "城市议会选举在即。三位候选人各自派来了使者，希望获得你的支持——或者说，希望你不要支持他们的对手。\n\n你的选择将影响整座城市的权力格局。",
        "choices": [
            {"text": "支持改革派候选人（警方声望+20）", "effect": {"factions_police": 20, "funds": -30000, "reputation": 5}, "response": "改革派候选人上台后，警方对你的组织睁一只眼闭一只眼。当然，每年'意思'一下还是要的。"},
            {"text": "支持黑帮背景的候选人（黑帮声望+20）", "effect": {"factions_gang": 20, "funds": 40000, "reputation": 3}, "response": "黑帮背景的候选人上台后，城中地下交易更加猖獗。你的生意比任何时候都好做。"},
        ],
    },
    7: {
        "title": "国家机器的清剿",
        "text": "风声突然收紧。国安部门成立了一个特别行动组，专门针对你这样的高层次地下组织。好几个城市的大人物已经落网。\n\n枭递来一张机票：「老板，该做选择了。」",
        "choices": [
            {"text": "暂避风头——转移到新城市发展", "effect": {"reputation": -10, "funds": -100000}, "response": "你带着核心班底转移到了临市。风头过了再回来。老巢虽然空了，但人还在——一切都可以重来。"},
            {"text": "花钱消灾——买通关键人物", "effect": {"funds": -150000, "reputation": 5, "factions_politician": 15}, "response": "金钱是最好的通行证。国安特别行动组的组长在一次'偶然'的澳门之旅后，对你的调查被悄悄搁置了。"},
        ],
    },
    8: {
        "title": "终极抉择",
        "text": "你站在了城市之巅。暗影王座上，你能看到整座城市的灯火——那些灯火之下，都是你的地盘。\n\n但坐在这个位置上，你必须做一个终极抉择。",
        "choices": [
            {"text": "霸权之路——吞并所有对手，成为暗面唯一主宰", "effect": {}, "response": "你发动了全面战争。一个月内，所有对手都被碾碎。代价是伤亡惨重，但从此以后，这座城市只有一个名字在暗面流传——你的名字。结局：💰 霸权", "ending": "霸权"},
            {"text": "传奇之路——金盆洗手，留下不朽传说", "effect": {}, "response": "你在巅峰时刻选择了急流勇退。江湖上从此只有你的传说。十年后，有人写了一本书，名字叫《暗影之王》。结局：📖 传奇", "ending": "传奇"},
            {"text": "隐秘之路——转入更深的地下，成为真正的幕后操盘手", "effect": {}, "response": "你解散了表面的一切，转入更深的地下。从此没有人能找到你，但每个重大决策背后，都有你的影子。结局：🎭 隐秘", "ending": "隐秘"},
        ],
    },
}

# ============================================================
# 竞争对手数据
# ============================================================

RIVAL_NAMES = ["赤蛇帮", "暗影会", "血手团", "青鸾帮", "铁骨堂"]
RIVAL_ACTIONS = ["steal_contract", "poach", "provoke", "expand"]

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
        self._weapon_id_counter = 100
        self._total_missions_completed = 0
        self.game_state = self._default_state()
        self._action_context = {}
        self.used_names = set()

    def _default_state(self):
        return {
            "funds": 50000,
            "reputation": 10,
            "max_reputation": 200,
            "ap": 3,
            "max_ap": 3,
            "day": 1,
            "hitmen": [],
            "contracts": [],
            "weapons": self._generate_weapons(8),
            "rivals": self._generate_rivals(),
            "history": [],
            "game_over": False,
            # 组织等级
            "org_level": 1,
            "org_xp": 0,
            "org_level_name": "街头暗影",
            # 安全屋
            "safehouse": {
                "training_ground": 0,
                "medical_room": 0,
                "intel_room": 0,
                "interrogation_room": 0,
            },
            # 情报
            "intel": 0,
            "intel_level": 1,
            # 阵营声望
            "factions": {
                "police": {"value": 50, "max": 100},
                "gang": {"value": 50, "max": 100},
                "politician": {"value": 50, "max": 100},
            },
            # 洗钱
            "dirty_money": 0,
            # 投资
            "investments": [],
            # 干部
            "cadres": {
                "intel_officer": None,
                "action_commander": None,
                "tech_expert": None,
                "logistics_manager": None,
            },
            # 主线剧情标记
            "main_story_flags": {},
            # 游戏结局
            "ending": None,
        }

    # ---- 状态管理 ----

    def reset_game(self):
        self._weapon_id_counter = 100
        self._npc_leaderboard = []
        self._total_missions_completed = 0
        self.game_state = self._default_state()
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
            f"组织等级：{s['org_level_name']} (Lv.{s['org_level']})",
            f"组织经验：{s['org_xp']}",
        ]
        if s["hitmen"]:
            lines.append("杀手列表：")
            for h in s["hitmen"]:
                lines.append(
                    f"  - {h['name']} | 专长:{h['specialty']} "
                    f"| 忠诚:{h['loyalty']}/10 "
                    f"| 抽成:{int(h.get('cut',0.2)*100)}% "
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
        """生成一个随机杀手（含关系网+内奸标记）"""
        if skill_level is None:
            skill_level = random.choices([1, 2, 3, 4, 5], weights=[25, 30, 25, 15, 5])[0]
        specialty = random.choice(SPECIALTIES)
        loyalty = random.randint(6, 10)
        cut_rates = {1: 0.15, 2: 0.20, 3: 0.30, 4: 0.40, 5: 0.50}
        cut = cut_rates.get(skill_level, 0.20)
        return {
            "id": random.randint(10000, 99999),
            "name": self._random_name(),
            "specialty": specialty,
            "loyalty": loyalty,
            "cut": cut,
            "salary": 0,
            "skill": skill_level,
            "lv": 1,
            "exp": 0,
            "weapon_id": None,
            "missions_completed": 0,
            "status": "idle",
            "friends": [],
            "rivals": [],
            "_is_mole": random.random() < 0.15,
            "mole_owner": None,
            "activity_log": [],
            # 个人档案
            "mission_history": [],
            "legend_title": None,
            "epitaph": None,
        }

    def _generate_contracts(self, count=3):
        rep = self.game_state["reputation"]
        templates = [t for t in CONTRACT_TEMPLATES if t[4] <= rep]
        if len(templates) < count:
            templates = CONTRACT_TEMPLATES
        selected = random.sample(templates, min(count, len(templates)))
        contracts = []
        for i, tpl in enumerate(selected):
            desc, diff, spec, base_reward, rep_req = tpl
            name = desc.split("「")[1].split("」")[0]
            reward_var = random.randint(-2000, 2000)
            reward = max(1000, base_reward + reward_var)
            contracts.append({
                "id": i + 1,
                "name": name,
                "target_desc": desc,
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
                "cut": h["cut"],
                "recruitment_cost": recruitment_cost,
            })
        return candidates

    def _check_poach(self):
        """检查是否有杀手被挖角"""
        hitmen = self.game_state["hitmen"]
        if not hitmen:
            return None
        targets = [m for m in hitmen if m["loyalty"] <= 3]
        if not targets:
            return None
        if random.random() < 0.4:
            target = random.choice(targets)
            if random.random() < (0.6 - target["loyalty"] * 0.1):
                self.game_state["hitmen"].remove(target)
                return target
        return None

    def _trigger_random_event(self):
        """触发随机事件，返回事件信息"""
        event_template = random.choice(EVENTS)
        event = dict(event_template)

        for key, val in event["effect"].items():
            self._modify_state(key, val)

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
            "timestamp": str(Path(__file__).stat().st_mtime),
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
        self._generate_npc_hitmen()
        self._pregen_candidates = self._generate_recruit_candidates(3)
        self.game_state["contracts"] = self._generate_contracts(3)
        narrative = self._call_ai("start", "游戏开场")
        return narrative

    def show_recruit_candidates(self):
        """显示可招募的候选人"""
        if self.game_state["ap"] <= 0:
            return None, "今天的行动力已经用完了，明天再来招募吧。"
        candidates = getattr(self, '_pregen_candidates', [])
        if not candidates:
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

        self._modify_state("funds", -cost)
        self._modify_state("ap", -1)

        new_hitman = {
            "id": random.randint(10000, 99999),
            "name": candidate["name"],
            "specialty": candidate["specialty"],
            "loyalty": candidate["loyalty"],
            "cut": candidate.get("cut", 0.20),
            "salary": 0,
            "skill": candidate["skill"],
            "lv": 1,
            "exp": 0,
            "weapon_id": None,
            "missions_completed": 0,
            "status": "idle",
            "friends": [],
            "rivals": [],
            "_is_mole": random.random() < 0.15,
            "mole_owner": None,
            "activity_log": [],
            "mission_history": [],
            "legend_title": None,
            "epitaph": None,
        }

        if new_hitman["_is_mole"]:
            alive = [r for r in self.game_state["rivals"] if r["alive"]]
            if alive:
                new_hitman["mole_owner"] = random.choice(alive)["name"]

        existing = [m for m in self.game_state["hitmen"] if m["id"] != new_hitman["id"]]
        for other in existing:
            if random.random() < 0.4:
                new_hitman["friends"].append(other["id"])
                other["friends"].append(new_hitman["id"])
            elif random.random() < 0.2:
                new_hitman["rivals"].append(other["id"])
                other["rivals"].append(new_hitman["id"])

        self.game_state["hitmen"].append(new_hitman)

        narrative = self._call_ai(
            "hire",
            f"招募成功：{candidate['name']}（{candidate['specialty']}，战力{candidate['skill']}）"
        )
        self._action_context.pop("candidates", None)
        return narrative, new_hitman

    def show_contracts(self):
        """展示当前契约板"""
        contracts = self.game_state["contracts"]
        available = [c for c in contracts if not c.get("taken")]
        if not available:
            return [], "老板，今天的契约板是空的……真少见。"
        narrative = f"枭递来一份契约清单：\n"
        narrative += f"当前有 {len(available)} 个可用契约，难度从简单到致命不等。"
        return available, narrative

    def assign_contract(self, contract_index=None, hitman_id=None, contract_id=None, plan_id=None):
        """派遣杀手执行契约（支持多方案）"""
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

        # 方案加成（Lv3解锁）
        plan_mult = 1.0
        plan_success_bonus = 0.0
        plan_infamy = 0
        org_level = self.game_state["org_level"]

        if plan_id and org_level >= 3:
            plan = None
            for p in CONTRACT_PLANS:
                if p["id"] == plan_id:
                    plan = p
                    break
            if plan:
                # 检查专长匹配
                if hitman["specialty"] == plan["req_spec"]:
                    plan_mult = plan["reward_mult"]
                    plan_success_bonus = plan["success_bonus"]
                    plan_infamy = plan.get("infamy", 0)
                # 不匹配也可以用，但无加成

        # 干部加成
        cadre_bonus = 0
        if self.game_state["cadres"]["action_commander"]:
            # 有行动队长，成功率+10%
            cadre_bonus = 0.10

        # 扣AP
        self._modify_state("ap", -1)

        # 计算成功率
        base_success = 0.3
        specialty_bonus = 0.2 if hitman["specialty"] == contract["required_specialty"] else 0
        skill_bonus = hitman["skill"] * 0.08
        diff_penalty = {"简单": 0, "中等": -0.1, "困难": -0.25, "致命": -0.4}
        penalty = diff_penalty.get(contract["difficulty"], 0)

        success_rate = base_success + specialty_bonus + skill_bonus + penalty + plan_success_bonus + cadre_bonus
        success_rate = max(0.1, min(0.95, success_rate))

        diced = random.random()
        success = diced < success_rate

        # 实际报酬
        actual_reward = int(contract["reward"] * plan_mult)

        # 更新状态
        contract["taken"] = True
        if success:
            # 50%是脏钱（需要洗白）
            dirty_money = int(actual_reward * 0.5)
            clean_money = actual_reward - dirty_money
            self._modify_state("funds", clean_money)
            self.game_state["dirty_money"] = self.game_state.get("dirty_money", 0) + dirty_money

            rep_gain = {"简单": 2, "中等": 4, "困难": 7, "致命": 12}
            self._modify_state("reputation", rep_gain.get(contract["difficulty"], 3))
            hitman["status"] = "idle"
            exp_gain = {"简单": 20, "中等": 40, "困难": 80, "致命": 150}
            hitman["exp"] = hitman.get("exp", 0) + exp_gain.get(contract["difficulty"], 20)
            hitman["missions_completed"] = hitman.get("missions_completed", 0) + 1
            # 记录任务历史
            if "mission_history" not in hitman:
                hitman["mission_history"] = []
            hitman["mission_history"].append({
                "contract": contract["name"],
                "difficulty": contract["difficulty"],
                "result": "success",
                "reward": actual_reward,
                "plan": plan_id or "standard",
                "day": self.game_state["day"],
            })
            self._check_level_up(hitman)
            # 检查传奇称号（Lv8功能）
            self._check_legend_title(hitman)
            if random.random() < 0.3:
                hitman["loyalty"] = min(10, hitman["loyalty"] + 1)

            # 组织经验（成功合约增加org_xp）
            org_xp_gain = {"简单": 5, "中等": 10, "困难": 20, "致命": 40}
            self.game_state["org_xp"] = self.game_state.get("org_xp", 0) + org_xp_gain.get(contract["difficulty"], 5)
            self._total_missions_completed += 1
        else:
            rep_loss = {"简单": -1, "中等": -2, "困难": -4, "致命": -8}
            self._modify_state("reputation", rep_loss.get(contract["difficulty"], -2))
            if random.random() < 0.5:
                hitman["status"] = "injured"
            else:
                hitman["status"] = "idle"
            if "mission_history" not in hitman:
                hitman["mission_history"] = []
            hitman["mission_history"].append({
                "contract": contract["name"],
                "difficulty": contract["difficulty"],
                "result": "failed",
                "reward": 0,
                "plan": plan_id or "standard",
                "day": self.game_state["day"],
            })

        # 阵营变动
        if plan_infamy > 0:
            self._modify_faction("police", -plan_infamy)
        elif plan_infamy < 0:
            self._modify_faction("police", -plan_infamy)  # 制造意外警方查不到

        narrative_context = (
            f"派遣{hitman['name']}执行契约「{contract['name']}」"
            f"（难度：{contract['difficulty']}，所需专长：{contract['required_specialty']}，"
            f"杀手专长：{hitman['specialty']}，成功率：{success_rate:.0%}）"
            f"结果：{'✅ 成功' if success else '❌ 失败'}，"
            f"获得报酬：¥{actual_reward if success else 0}"
        )
        if plan_id and org_level >= 3:
            plan = next((p for p in CONTRACT_PLANS if p["id"] == plan_id), None)
            if plan:
                narrative_context += f"，执行方案：{plan['name']}"
        narrative = self._call_ai("assign_contract", narrative_context)

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
        # 如果是干部，先解职
        for role_id, assigned_id in self.game_state["cadres"].items():
            if assigned_id == hitman_id:
                self.game_state["cadres"][role_id] = None
        self.game_state["hitmen"].remove(hitman)
        reputation_change = -hitman["skill"]
        self._modify_state("reputation", reputation_change)
        narrative = self._call_ai(
            "fire_result",
            f"解雇了杀手{hitman['name']}（{hitman['specialty']}，战力{hitman['skill']}）"
        )
        return narrative

    def boost_loyal(self, hitman_id: int):
        """发奖金提升忠诚度"""
        hitman = None
        for h in self.game_state["hitmen"]:
            if h["id"] == hitman_id:
                hitman = h
                break
        if not hitman:
            return "找不到这个杀手。"
        if hitman["status"] != "idle":
            return "这个杀手不在空闲状态，暂时发不了奖金。"
        if self.game_state["funds"] < 5000:
            return "资金不够发奖金，最少需要 ¥5,000。"
        if self.game_state["ap"] <= 0:
            return "今天的行动力不够了。"
        
        cost = 5000
        self._modify_state("funds", -cost)
        self._modify_state("ap", -1)
        
        # 随机提升忠诚度 1-3 点
        gain = random.randint(1, 3)
        hitman["loyalty"] = min(10, hitman["loyalty"] + gain)
        
        return f"{hitman['name']} 收到了 ¥{cost} 奖金，忠诚度 +{gain}！当前忠诚度：{hitman['loyalty']}/10"

    def sell_intel(self):
        """出售情报换取资金"""
        intel = self.game_state.get("intel", 0)
        if intel < 10:
            return f"情报不够出售，当前情报 {intel}，需要至少 10 点情报。"
        if self.game_state["ap"] <= 0:
            return "今天的行动力不够了。"
        
        # 消耗10点情报换资金，每点情报价值500
        sell_amount = 10
        price_per_intel = 500 + self.game_state["org_level"] * 100
        total_gain = sell_amount * price_per_intel
        
        self.game_state["intel"] = intel - sell_amount
        self._modify_state("ap", -1)
        self._modify_state("funds", total_gain)
        
        return f"出售了 {sell_amount} 点情报，获得 ¥{total_gain}（每点 ¥{price_per_intel}）。剩余情报：{self.game_state['intel']}。"

    # ---- 组织等级系统 ----

    def check_org_upgrade(self):
        """检查组织是否可以升级，返回升级信息或None"""
        s = self.game_state
        current_level = s["org_level"]
        if current_level >= 8:
            return None  # 满级

        next_level_info = None
        for lv_info in ORG_LEVELS:
            if lv_info["level"] == current_level + 1:
                next_level_info = lv_info
                break

        if not next_level_info:
            return None

        # 检查条件
        if (s["funds"] >= next_level_info["funds_req"] and
            s["reputation"] >= next_level_info["rep_req"] and
            self._total_missions_completed >= next_level_info["missions_req"] and
            s["org_xp"] >= next_level_info["xp_req"]):

            # 升级！
            s["org_level"] = next_level_info["level"]
            s["org_level_name"] = next_level_info["name"]

            # 升级奖励
            upgrade_bonus = {
                2: {"funds": 10000},
                3: {"funds": 20000, "reputation": 5},
                4: {"funds": 40000, "reputation": 5},
                5: {"funds": 60000, "reputation": 10},
                6: {"funds": 80000, "reputation": 10},
                7: {"funds": 100000, "reputation": 15},
                8: {"funds": 150000, "reputation": 20},
            }
            bonus = upgrade_bonus.get(next_level_info["level"], {})
            for k, v in bonus.items():
                self._modify_state(k, v)

            return {
                "old_level": current_level,
                "new_level": next_level_info["level"],
                "new_name": next_level_info["name"],
                "desc": next_level_info["desc"],
                "bonus": bonus,
            }
        return None

    def get_org_level_info(self):
        """获取组织等级信息"""
        return {
            "level": self.game_state["org_level"],
            "name": self.game_state["org_level_name"],
            "xp": self.game_state["org_xp"],
            "levels": ORG_LEVELS,
        }

    # ---- 安全屋系统（Lv2解锁） ----

    def show_safehouse_upgrades(self):
        """显示安全屋升级选项"""
        if self.game_state["org_level"] < 2:
            return [], "组织等级不够（需要Lv.2区域新秀），枭还没找到合适的地方建安全屋。"

        upgrades = []
        for u in SAFEHOUSE_UPGRADES:
            current_lv = self.game_state["safehouse"].get(u["id"], 0)
            if current_lv < u["max_lv"]:
                cost = u["base_cost"] + current_lv * u["cost_per_lv"]
                upgrades.append({
                    "id": u["id"],
                    "name": u["name"],
                    "desc": u["desc"],
                    "current_lv": current_lv,
                    "max_lv": u["max_lv"],
                    "next_lv": current_lv + 1,
                    "cost": cost,
                })
        return upgrades, "枭展开了一卷安全屋改造蓝图。"

    def upgrade_safehouse(self, upgrade_id: str):
        """升级安全屋"""
        if self.game_state["org_level"] < 2:
            return "组织等级不够。"

        upgrade = None
        for u in SAFEHOUSE_UPGRADES:
            if u["id"] == upgrade_id:
                upgrade = u
                break
        if not upgrade:
            return "无效的升级项目。"

        current_lv = self.game_state["safehouse"].get(upgrade_id, 0)
        if current_lv >= upgrade["max_lv"]:
            return f"{upgrade['name']} 已经满级了。"

        cost = upgrade["base_cost"] + current_lv * upgrade["cost_per_lv"]
        if self.game_state["funds"] < cost:
            return f"资金不够，需要 ¥{cost}。"

        if self.game_state["ap"] <= 0:
            return "行动力不够。"

        self._modify_state("funds", -cost)
        self._modify_state("ap", -1)
        self.game_state["safehouse"][upgrade_id] = current_lv + 1

        # 安全屋效果
        effects = []
        if upgrade_id == "training_ground":
            effects.append("训练效果 +50%")
        elif upgrade_id == "medical_room":
            effects.append("受伤恢复加速")
        elif upgrade_id == "intel_room":
            effects.append("情报收集增加")
        elif upgrade_id == "interrogation_room":
            effects.append("可以审讯俘虏了")

        return f"{upgrade['name']} 升级到Lv.{current_lv + 1}！{'，'.join(effects)} 消耗 ¥{cost}。"

    # ---- 合约多方案（Lv3解锁） ----

    def get_contract_plans(self, hitman_id: int, contract_index: int = None):
        """获取可用方案列表"""
        if self.game_state["org_level"] < 3:
            return []  # Lv3以下不展示方案

        hitman = None
        for h in self.game_state["hitmen"]:
            if h["id"] == hitman_id:
                hitman = h
                break
        if not hitman:
            return []

        plans = []
        for p in CONTRACT_PLANS:
            is_match = hitman["specialty"] == p["req_spec"]
            plans.append({
                "id": p["id"],
                "name": p["name"],
                "desc": p["desc"],
                "is_available": is_match,
                "success_bonus": p["success_bonus"],
                "reward_mult": p["reward_mult"],
            })
        return plans

    # ---- 阵营声望系统（Lv4解锁） ----

    def get_factions(self):
        """获取阵营声望状态"""
        if self.game_state["org_level"] < 4:
            return None, "组织等级不够（需要Lv.4城市暗流）。"
        return self.game_state["factions"], None

    def _modify_faction(self, faction_id: str, amount: int):
        """修改阵营声望"""
        if faction_id not in self.game_state["factions"]:
            return
        faction = self.game_state["factions"][faction_id]
        faction["value"] = max(0, min(faction["max"], faction["value"] + amount))

    # ---- 洗钱系统（Lv4解锁） ----

    def show_laundry_options(self):
        """显示洗钱选项"""
        if self.game_state["org_level"] < 4:
            return [], "组织等级不够（需要Lv.4城市暗流）。"

        dirty = self.game_state.get("dirty_money", 0)
        if dirty <= 0:
            return [], "老板，最近账很干净，没有脏钱需要处理。"

        options = []
        for ch in LAUNDRY_CHANNELS:
            can_afford_cost = self.game_state["funds"] >= ch["cost_per_batch"]
            can_afford_ap = self.game_state["ap"] >= ch["ap_cost"]
            can_use = can_afford_cost and can_afford_ap
            clean_amount = int(dirty * ch["clean_per_batch"])
            options.append({
                "id": ch["id"],
                "name": ch["name"],
                "desc": ch["desc"],
                "cost": ch["cost_per_batch"],
                "ap_cost": ch["ap_cost"],
                "clean_amount": clean_amount,
                "can_use": can_use,
            })
        return options, f"枭递上账本：'老板，账上有 ¥{dirty} 脏钱需要处理。'"

    def do_laundry(self, channel_id: str):
        """执行洗钱"""
        if self.game_state["org_level"] < 4:
            return "组织等级不够。"

        channel = None
        for ch in LAUNDRY_CHANNELS:
            if ch["id"] == channel_id:
                channel = ch
                break
        if not channel:
            return "无效的洗钱渠道。"

        dirty = self.game_state.get("dirty_money", 0)
        if dirty <= 0:
            return "没有脏钱需要洗。"

        if self.game_state["funds"] < channel["cost_per_batch"]:
            return f"资金不够，需要 ¥{channel['cost_per_batch']} 作为运营成本。"

        if self.game_state["ap"] < channel["ap_cost"]:
            return "行动力不够。"

        clean_amount = int(dirty * channel["clean_per_batch"])
        actual_clean = min(clean_amount, dirty)

        self._modify_state("funds", -channel["cost_per_batch"])
        self._modify_state("ap", -channel["ap_cost"])
        self.game_state["dirty_money"] = dirty - actual_clean
        self._modify_state("funds", actual_clean)

        return f"通过{channel['name']}洗白了 ¥{actual_clean}，消耗 ¥{channel['cost_per_batch']}+{channel['ap_cost']}AP。剩余脏钱：¥{self.game_state['dirty_money']}。"

    # ---- 投资系统（Lv6解锁） ----

    def show_investments(self):
        """显示投资选项"""
        if self.game_state["org_level"] < 6:
            return [], None, "组织等级不够（需要Lv.6幕后操盘）。"

        existing = self.game_state.get("investments", [])
        return INVESTMENT_TYPES, existing, None

    def make_investment(self, invest_id: str):
        """进行投资"""
        if self.game_state["org_level"] < 6:
            return "组织等级不够。"

        invest_type = None
        for inv in INVESTMENT_TYPES:
            if inv["id"] == invest_id:
                invest_type = inv
                break
        if not invest_type:
            return "无效的投资项目。"

        cost = invest_type["min_invest"]
        if self.game_state["funds"] < cost:
            return f"资金不够，{invest_type['name']} 最少需要 ¥{cost}。"

        if self.game_state["ap"] <= 0:
            return "行动力不够。"

        self._modify_state("funds", -cost)
        self._modify_state("ap", -1)

        if "investments" not in self.game_state:
            self.game_state["investments"] = []

        self.game_state["investments"].append({
            "id": invest_type["id"],
            "name": invest_type["name"],
            "amount": cost,
            "week_return": invest_type["weekly_return"],
            "risk": invest_type["risk"],
            "weeks_active": 0,
        })

        return f"投资成功！{invest_type['name']}（¥{cost}），每周预定回报率 {invest_type['weekly_return']*100:.0f}%。"

    def _process_investments(self):
        """处理每周投资回报"""
        if self.game_state["org_level"] < 6:
            return []

        results = []
        investments = self.game_state.get("investments", [])
        for inv in investments[:]:  # 复制列表遍历
            inv["weeks_active"] += 1
            # 检查被查封风险
            if random.random() < inv["risk"] * 0.1:  # 每轮风险
                refund = int(inv["amount"] * 0.5)  # 查封退回50%
                self._modify_state("funds", refund)
                investments.remove(inv)
                results.append(f"⚠️ {inv['name']} 被查封了！退回 ¥{refund}。")
                continue

            # 回报
            return_amount = int(inv["amount"] * inv["week_return"])
            self._modify_state("funds", return_amount)
            results.append(f"💹 {inv['name']} 带来 ¥{return_amount} 回报。")

        return results

    # ---- 干部系统（Lv5解锁） ----

    def show_cadres(self):
        """显示干部信息"""
        if self.game_state["org_level"] < 5:
            return None, "组织等级不够（需要Lv.5暗夜贵族）。"

        cadres_info = {}
        for role in CADRE_ROLES:
            hitman_id = self.game_state["cadres"].get(role["id"])
            hitman = None
            if hitman_id:
                for h in self.game_state["hitmen"]:
                    if h["id"] == hitman_id:
                        hitman = h
                        break
            cadres_info[role["id"]] = {
                "role": role,
                "current": hitman,
                "assigned": hitman_id is not None,
            }

        return cadres_info, "枭递来组织架构表：'老板，干部位置还空着几个。'"

    def appoint_cadre(self, role_id: str, hitman_id: int):
        """任命干部"""
        if self.game_state["org_level"] < 5:
            return "组织等级不够。"

        # 检查角色
        role = None
        for r in CADRE_ROLES:
            if r["id"] == role_id:
                role = r
                break
        if not role:
            return "无效的干部职位。"

        # 检查杀手
        hitman = None
        for h in self.game_state["hitmen"]:
            if h["id"] == hitman_id:
                hitman = h
                break
        if not hitman:
            return "找不到这个杀手。"

        # 检查是否已被任命其他职位
        for rid, hid in self.game_state["cadres"].items():
            if hid == hitman_id and rid != role_id:
                return f"{hitman['name']} 已经是其他干部职位了。"

        # 任命
        self.game_state["cadres"][role_id] = hitman_id
        return f"{hitman['name']} 被任命为{role['name']}！{role['desc']}"

    def remove_cadre(self, role_id: str):
        """解除干部职务"""
        if role_id not in self.game_state["cadres"]:
            return "无效的干部职位。"
        self.game_state["cadres"][role_id] = None
        role_name = next((r["name"] for r in CADRE_ROLES if r["id"] == role_id), "未知职位")
        return f"{role_name} 已被解除职务。"

    # ---- 杀手个人档案（Lv8解锁） ----

    def get_hitman_profile(self, hitman_id: int):
        """获取杀手个人档案"""
        hitman = None
        for h in self.game_state["hitmen"]:
            if h["id"] == hitman_id:
                hitman = h
                break
        if not hitman:
            return None

        # 计算传奇级别
        missions = hitman.get("missions_completed", 0)
        legend_titles = [
            (10, "新血"),
            (25, "利刃"),
            (50, "王牌"),
            (100, "传奇"),
            (200, "活着的传说"),
        ]
        legend_title = None
        for count, title in legend_titles:
            if missions >= count:
                legend_title = title
        if not legend_title:
            legend_title = "新手"

        return {
            "id": hitman["id"],
            "name": hitman["name"],
            "specialty": hitman["specialty"],
            "skill": hitman["skill"],
            "lv": hitman.get("lv", 1),
            "loyalty": hitman["loyalty"],
            "missions_completed": missions,
            "legend_title": legend_title,
            "epitaph": hitman.get("epitaph"),
            "mission_history": hitman.get("mission_history", []),
            "status": hitman["status"],
            "weapon_id": hitman.get("weapon_id"),
            "friends": hitman.get("friends", []),
            "rivals": hitman.get("rivals", []),
        }

    def _check_legend_title(self, hitman):
        """检查并更新传奇称号"""
        missions = hitman.get("missions_completed", 0)
        titles = {
            10: "新血",
            25: "利刃",
            50: "王牌",
            100: "传奇",
            200: "活着的传说",
        }
        for count, title in titles.items():
            if missions == count:
                hitman["legend_title"] = title
                return title
        return None

    # ---- 主线剧情（依次触发） ----

    def check_main_story(self):
        """检查是否有主线剧情触发，返回剧情数据或None"""
        org_level = self.game_state["org_level"]
        flags = self.game_state.get("main_story_flags", {})

        if str(org_level) in flags:
            return None  # 已经触发过了

        if org_level in MAIN_STORIES:
            story = MAIN_STORIES[org_level]
            flags[str(org_level)] = "triggered"
            return {
                "level": org_level,
                "title": story["title"],
                "text": story["text"],
                "choices": story["choices"],
            }
        return None

    def resolve_main_story(self, level: int, choice_index: int):
        """处理主线剧情选择"""
        story = MAIN_STORIES.get(level)
        if not story:
            return "未知的剧情节点。", None

        if choice_index < 0 or choice_index >= len(story["choices"]):
            return "无效的选择。", None

        choice = story["choices"][choice_index]
        # 应用效果
        for key, val in choice["effect"].items():
            if key == "funds":
                self._modify_state("funds", val)
            elif key == "reputation":
                self._modify_state("reputation", val)
            elif key.startswith("factions_"):
                faction_id = key.replace("factions_", "")
                self._modify_faction(faction_id, val)
            else:
                self._modify_state(key, val)

        # 处理结局
        if "ending" in choice:
            self.game_state["ending"] = choice["ending"]
            self.game_state["game_over"] = True

        return choice["response"], choice.get("ending")

    # ---- 杀手自主活动 ----

    def _daily_hitman_activities(self):
        """每个空闲杀手每天随机活动，返回事件列表"""
        events = []
        # 医疗室效果：加快恢复
        med_lv = self.game_state["safehouse"].get("medical_room", 0)
        for h in self.game_state["hitmen"]:
            if h["status"] == "injured":
                # 医疗室加速恢复
                if med_lv > 0 and random.random() < 0.5 + med_lv * 0.15:
                    h["status"] = "idle"
                    events.append((h["name"], f"在医疗室休养后康复了", "activity"))
                    continue

        for h in self.game_state["hitmen"]:
            if h["status"] != "idle":
                continue
            # 内奸活动
            if h["_is_mole"] and random.random() < 0.3:
                sab = random.choice(["steal", "sabotage", "leak"])
                if sab == "steal":
                    loss = random.randint(2000, 8000)
                    self._modify_state("funds", -loss)
                    events.append((h["name"], f"偷偷挪用了 ¥{loss} 组织资金（内奸）", "mole"))
                elif sab == "sabotage":
                    if self.game_state["weapons"]:
                        owned = [x for x in self.game_state["weapons"] if x["owned"]]
                        if owned:
                            w = random.choice(owned)
                            w["owned"] = False
                            w["equipped_by"] = None
                            events.append((h["name"], f"破坏并遗失了武器「{w['name']}」（内奸）", "mole"))
                elif sab == "leak":
                    self._modify_state("reputation", -2)
                    events.append((h["name"], f"泄露了组织情报，声望-2（内奸）", "mole"))
                h["activity_log"].append("内奸活动")
                continue

            act = random.choices(
                ["drink", "fight", "gamble", "train", "lazy", "info", "social"],
                weights=[25, 10, 15, 10, 20, 10, 10]
            )[0]
            if act == "drink":
                cost = random.randint(500, 2000)
                self._modify_state("funds", -cost)
                events.append((h["name"], f"喝花酒花了 ¥{cost}", "activity"))
            elif act == "fight":
                if random.random() < 0.5:
                    h["status"] = "injured"
                    events.append((h["name"], "在街头斗殴中受伤了", "activity"))
                else:
                    gain = random.randint(2000, 5000)
                    self._modify_state("funds", gain)
                    events.append((h["name"], f"在斗殴中赢了 ¥{gain} 回来", "activity"))
            elif act == "gamble":
                if random.random() < 0.4:
                    win = random.randint(3000, 10000)
                    self._modify_state("funds", win)
                    events.append((h["name"], f"赌钱赢了 ¥{win}", "activity"))
                else:
                    loss = random.randint(2000, 6000)
                    self._modify_state("funds", -loss)
                    events.append((h["name"], f"赌钱输了 ¥{loss}", "activity"))
            elif act == "train":
                gain = random.choice(["skill", "loyalty"])
                if gain == "skill":
                    h["skill"] = min(10, h["skill"] + 1)
                    events.append((h["name"], "自己加练，战力+1", "activity"))
                else:
                    h["loyalty"] = min(10, h["loyalty"] + 1)
                    events.append((h["name"], "参加了组织忠诚培训", "activity"))
            elif act == "lazy":
                events.append((h["name"], "今天摸鱼了一天，什么也没干", "activity"))
            elif act == "info":
                # 情报室加成
                intel_bonus = self.game_state["safehouse"].get("intel_room", 0) * 1000
                info_gain = random.randint(1000, 3000) + intel_bonus
                self._modify_state("funds", info_gain)
                events.append((h["name"], f"从线人那里搞了点情报卖钱，¥{info_gain}", "activity"))
            elif act == "social":
                others = [x for x in self.game_state["hitmen"] if x["id"] != h["id"] and x["status"] == "idle"]
                if others:
                    o = random.choice(others)
                    if random.random() < 0.5:
                        if o["id"] not in h["friends"]:
                            h["friends"].append(o["id"])
                            o["friends"].append(h["id"])
                        events.append((h["name"], f"和{o['name']}一起喝酒，成了朋友", "activity"))
                    else:
                        if o["id"] not in h["rivals"]:
                            h["rivals"].append(o["id"])
                            o["rivals"].append(h["id"])
                        events.append((h["name"], f"和{o['name']}闹翻了，成了对头", "activity"))
            h["activity_log"].append(act)
        return events

    def end_day(self):
        """结束当天，推进到第二天"""
        old_day = self.game_state["day"]

        # 发工资
        total_salary = 0
        salary_narrative = ""
        if total_salary > 0:
            self._modify_state("funds", -total_salary)
            salary_narrative = f"发放工资 ¥{total_salary}。"

        # 已消灭对手的地盘收入
        dead_rivals = [r for r in self.game_state["rivals"] if not r["alive"]]
        territory_income = sum(r["territory"] * 3000 for r in dead_rivals)
        if territory_income > 0:
            self._modify_state("funds", territory_income)
            salary_narrative += f" 地盘收入 +¥{territory_income}。"

        # 触发随机事件
        event = self._trigger_random_event()
        event_narrative_hint = event.get("narrative_hint", "")

        # 恢复受伤杀手（医疗室加速）
        med_lv = self.game_state["safehouse"].get("medical_room", 0)
        med_recovery_chance = {0: 0.3, 1: 0.6, 2: 0.8, 3: 1.0}
        recovery_chance = med_recovery_chance.get(med_lv, 0.3)
        for h in self.game_state["hitmen"]:
            if h["status"] == "injured":
                if random.random() < recovery_chance:
                    h["status"] = "idle"

        # 情报系统：空闲杀手自动产生情报
        idle_count = len([h for h in self.game_state["hitmen"] if h["status"] == "idle"])
        intel_per_idle = 1 + self.game_state.get("intel_level", 1)
        intel_room_lv = self.game_state["safehouse"].get("intel_room", 0)
        intel_bonus = intel_room_lv  # 情报室每级额外+1情报/人
        intel_gained = idle_count * (intel_per_idle + intel_bonus)
        if intel_gained > 0:
            self.game_state["intel"] = self.game_state.get("intel", 0) + intel_gained

        # 刷新契约板
        self.game_state["contracts"] = self._generate_contracts(3)

        # 更新intel_level（情报室提供额外加成）
        intel_room_lv = self.game_state["safehouse"].get("intel_room", 0)
        self.game_state["intel_level"] = 1 + (self.game_state["org_level"] // 2) + intel_room_lv

        # 杀手自主活动
        activity_events = self._daily_hitman_activities()
        activity_narrative = ""
        if activity_events:
            activity_narrative = "\n\n📋 组织日志："
            for name, desc, _ in activity_events:
                activity_narrative += f"\n  {name}：{desc}"

        # 随机捡人事件
        encounter = self._random_encounter()
        encounter_narrative = ""
        encounter_data = None
        if encounter:
            encounter_data = self._action_context.get("encounter")
            encounter_narrative = encounter

        # 预生成第二天的招募候选人
        self._pregen_candidates = self._generate_recruit_candidates(3)

        # 竞争对手行动
        rival_events = self._rival_turn()
        rival_narrative = ""
        if rival_events:
            rival_narrative = "\n\n⚔️ 竞争对手动态："
            for name, action in rival_events:
                rival_narrative += f"\n  {name} {action}"

        # 处理投资回报（每7天算一周）
        invest_narrative = ""
        if self.game_state["day"] % 7 == 0:
            invest_results = self._process_investments()
            if invest_results:
                invest_narrative = "\n\n💹 投资回报："
                for r in invest_results:
                    invest_narrative += f"\n  {r}"

        # 检查组织升级
        upgrade_info = self.check_org_upgrade()
        upgrade_narrative = ""
        if upgrade_info:
            bonus_text = ""
            for k, v in upgrade_info.get("bonus", {}).items():
                bonus_text += f" {k}+{v}"
            upgrade_narrative = f"\n\n⬆️ 组织升级！{upgrade_info['new_name']}（Lv.{upgrade_info['new_level']}）！{bonus_text}"

        # 恢复AP
        self.game_state["ap"] = self.game_state["max_ap"]
        self.game_state["day"] += 1

        # 情报叙事
        intel_narrative = ""
        if intel_gained > 0:
            intel_narrative = f"\n\n📡 情报收集：空闲杀手产出 {intel_gained} 点情报（当前共 {self.game_state['intel']} 点）。"

        # 生成叙事
        context = (
            f"第{old_day}天结束。{salary_narrative} "
            f"触发事件：{event_narrative_hint}。"
            f"进入第{self.game_state['day']}天。"
            f"当前资金：¥{self.game_state['funds']}，声望：{self.game_state['reputation']}"
        )
        narrative = self._call_ai("end_day", context)

        if event.get("poached"):
            narrative += f"\n\n⚠️ {event['poached']['name']} 被竞争对手挖走了！"
        elif event.get("no_effect"):
            narrative += "\n\n所幸没有重大损失。"

        if activity_events:
            narrative += activity_narrative

        if intel_narrative:
            narrative += intel_narrative

        if rival_events:
            narrative += rival_narrative
        # 传递挖角信息给前端弹窗
        if getattr(self, '_poached_name', None):
            event["poached"] = {"name": self._poached_name}
            self._poached_name = None

        if invest_narrative:
            narrative += invest_narrative

        if upgrade_narrative:
            narrative += upgrade_narrative

        if encounter_narrative:
            narrative += encounter_narrative

        if self.game_state["funds"] <= 0 or self.game_state["reputation"] <= 0:
            game_over = self._call_ai("game_over", "组织覆灭")
            self.game_state["game_over"] = True
            narrative += f"\n\n{game_over}"

        return narrative, event, encounter_data if encounter_data else None, upgrade_info

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
        # 技术专家打折
        discount = 1.0
        if self.game_state["cadres"]["tech_expert"]:
            discount = 0.8

        available = [w for w in self.game_state["weapons"] if not w["owned"]]
        if not available:
            return [], "枭摇了摇头：'老板，武器商这边暂时没货了。'"
        return available, discount, f"枭推了推桌上的武器清单：'这是黑市上能搞到的好货。'"

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
        # 折扣
        discount = 0.8 if self.game_state["cadres"]["tech_expert"] else 1.0
        price = int(weapon["price"] * discount)
        if self.game_state["funds"] < price:
            return f"资金不够，{weapon['name']} 需要 ¥{price}。"
        if self.game_state["reputation"] < weapon["rep_required"]:
            return f"声望不够，需要 {weapon['rep_required']} 声望才能购买{weapon['name']}。"
        self._modify_state("funds", -price)
        self._modify_state("ap", -1)
        weapon["owned"] = True
        discount_text = f"（技术专家折扣：¥{weapon['price']} → ¥{price}）" if discount < 1.0 else ""
        return f"购买成功！{weapon['name']}（{weapon['rarity']}）已入库。{discount_text}"

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
        """展示训练选项（受安全屋加成）"""
        if self.game_state["ap"] <= 0:
            return [], "今天的行动力不够了，明天再练吧。"
        hitmen = [m for m in self.game_state["hitmen"] if m["status"] == "idle"]
        if not hitmen:
            return [], "没有空闲的杀手可以训练。"

        # 训练场加成：战力+1变成+1+level
        training_lv = self.game_state["safehouse"].get("training_ground", 0)

        options = []
        for t in TRAINING_OPTIONS:
            opt = dict(t)
            if training_lv > 0:
                attr, amount = opt["effect"]
                if attr == "skill":
                    opt["effect"] = (attr, amount + training_lv)
                    opt["desc"] = opt["desc"].replace(f"+{amount}", f"+{amount+training_lv}")
                opt["has_bonus"] = True
            else:
                opt["has_bonus"] = False
            options.append(opt)

        return options, "枭拿出一份训练清单：'该让这些人活动活动筋骨了。'"

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

        # 训练场加成：+1+level
        training_lv = self.game_state["safehouse"].get("training_ground", 0)

        self._modify_state("funds", -training["cost"])
        self._modify_state("ap", -training["ap"])
        attr, amount = training["effect"]
        if attr == "skill" and training_lv > 0:
            amount = amount + training_lv
        if attr == "skill":
            hitman["skill"] = min(10, hitman["skill"] + amount)
        elif attr == "loyalty":
            hitman["loyalty"] = min(10, hitman["loyalty"] + amount)
        exp_gain = training["ap"] * 20
        hitman["exp"] += exp_gain
        self._check_level_up(hitman)

        bonus_text = f"（训练场加成 +{training_lv}）" if training_lv > 0 else ""
        return f"{hitman['name']} 完成了{training['name']}，{attr} +{amount}，经验 +{exp_gain}。{bonus_text}"

    def _check_level_up(self, hitman):
        """检查杀手升级"""
        needed = hitman["lv"] * 50
        while hitman["exp"] >= needed:
            hitman["exp"] -= needed
            hitman["lv"] += 1
            hitman["skill"] = min(10, hitman["skill"] + 1)
            needed = hitman["lv"] * 50

    # ---- 竞争对手系统 ----

    def _generate_rivals(self):
        """生成初始竞争对手"""
        count = random.randint(2, 3)
        names = random.sample(RIVAL_NAMES, min(count, len(RIVAL_NAMES)))
        rivals = []
        for i, name in enumerate(names):
            rivals.append({
                "id": i + 1,
                "name": name,
                "funds": random.randint(30000, 80000),
                "reputation": random.randint(15, 35),
                "strength": random.randint(10, 30),
                "territory": random.randint(1, 4),
                "hostile": random.randint(20, 60),
                "alive": True,
            })
        return rivals

    def show_rivals(self):
        """展示竞争对手列表"""
        alive = [r for r in self.game_state["rivals"] if r["alive"]]
        return alive, f"枭展开情报地图：'城里还有 {len(alive)} 个组织在跟我们抢地盘。'"

    def attack_rival(self, rival_id: int, hitman_ids):
        """派遣多个杀手攻击竞争对手"""
        if isinstance(hitman_ids, int):
            hitman_ids = [hitman_ids]
        rival = None
        for r in self.game_state["rivals"]:
            if r["id"] == rival_id and r["alive"]:
                rival = r
                break
        if not rival:
            return "找不到这个目标。"
        hitmen = []
        for h in self.game_state["hitmen"]:
            if h["id"] in hitman_ids and h["status"] == "idle":
                hitmen.append(h)
        if not hitmen:
            return "没有可派遣的杀手。"
        if self.game_state["ap"] < len(hitmen):
            return f"行动力不够，需要{len(hitmen)}点AP，当前只有{self.game_state['ap']}点。"
        self._modify_state("ap", -len(hitmen))
        total_skill = sum(h["skill"] for h in hitmen)
        bonus = len(hitmen) * 3
        player_power = total_skill + bonus
        success_chance = player_power / (player_power + rival["strength"])
        success_chance = max(0.2, min(0.95, success_chance))
        names = "、".join(h["name"] for h in hitmen)
        if random.random() < success_chance:
            gained = rival["territory"] * 5000 + rival["reputation"] * 200
            self._modify_state("funds", gained)
            self._modify_state("reputation", 5)
            rival["alive"] = False
            for hitman in hitmen:
                hitman["exp"] = hitman.get("exp", 0) + 50
                hitman["missions_completed"] = hitman.get("missions_completed", 0) + 1
                self._check_level_up(hitman)
            # 黑帮声望增加
            self._modify_faction("gang", 5)
            return f"行动成功！{rival['name']} 已被铲除，获得 ¥{gained}，声望 +5。\n参与杀手：{names}。"
        else:
            injured = random.choice(hitmen)
            injured["status"] = "injured"
            self._modify_state("reputation", -3)
            return f"行动失败……{injured['name']} 受伤了，声望 -3。\n参与杀手：{names}。"

    def _rival_turn(self):
        """每个对手执行一次回合行动"""
        events = []
        poached_this_night = False
        for rival in self.game_state["rivals"]:
            if not rival["alive"]:
                continue
            action = random.choice(RIVAL_ACTIONS)
            if action == "steal_contract":
                contracts = [c for c in self.game_state["contracts"] if not c.get("taken")]
                if contracts:
                    stolen = random.choice(contracts)
                    stolen["taken"] = True
                    events.append((rival["name"], f"抢走了契约「{stolen['name']}」"))
            elif action == "poach" and not poached_this_night:
                hitmen = [m for m in self.game_state["hitmen"] if m["loyalty"] <= 3]
                if hitmen and random.random() < 0.3:
                    target = random.choice(hitmen)
                    self.game_state["hitmen"].remove(target)
                    events.append(("!!", f"你的杀手 {target['name']} 被{rival['name']}挖走了！（忠诚太低）"))
                    self._poached_name = target["name"]
                    poached_this_night = True
            elif action == "provoke":
                dmg = random.randint(2, 5)
                self._modify_state("reputation", -dmg)
                events.append((rival["name"], f"挑衅我们，声望 -{dmg}"))
            elif action == "expand":
                rival["territory"] += 1
                rival["strength"] += 2
                events.append((rival["name"], f"扩张了地盘"))
        return events

    # ---- 随机捡人事件 ----

    def _random_encounter(self):
        """每天有一定概率遇到野生人才"""
        if random.random() > 0.3:
            return None
        names = ["流浪刀客", "退役特种兵", "暗网黑客", "街头混混", "神秘女子", "落魄佣兵"]
        specials = ["近战", "狙击", "黑客", "近战", "潜入", "爆破"]
        idx = random.randint(0, len(names) - 1)
        name = names[idx]
        spec = specials[idx]
        skill = random.randint(1, 3)
        cost = 5000 + skill * 3000
        self._action_context["encounter"] = {
            "name": name,
            "specialty": spec,
            "skill": skill,
            "cost": cost,
        }
        return f"\n\n🤝 你在街头遇到了一个有意思的人：{name}（{spec}，战力{skill}）。花 ¥{cost} 可以招募他。"

    def get_leaderboard(self):
        """获取杀手排行榜"""
        ranking = []
        for h in self.game_state["hitmen"]:
            weapon_bonus = 0
            if h.get("weapon_id"):
                for w in self.game_state["weapons"]:
                    if w["id"] == h["weapon_id"]:
                        weapon_bonus = w.get("bonus", 0)
                        break
            power = h["skill"] + weapon_bonus + h.get("lv", 1) * 0.5
            ranking.append({
                "id": h["id"],
                "name": h["name"],
                "specialty": h["specialty"],
                "skill": h["skill"],
                "lv": h.get("lv", 1),
                "weapon_bonus": weapon_bonus,
                "power": round(power, 1),
                "missions": h.get("missions_completed", 0),
                "status": h["status"],
                "is_npc": False,
            })
        npcs = getattr(self, '_npc_leaderboard', [])
        for npc in npcs:
            if not npc.get("poached"):
                ranking.append(npc)
        ranking.sort(key=lambda x: x["power"], reverse=True)
        return ranking

    def _generate_npc_hitmen(self):
        """生成排行榜上的 NPC 杀手"""
        npcs = []
        names = random.sample(NPC_NAMES, min(len(NPC_NAMES), 12))
        for name in names:
            skill = random.choices([2, 3, 4, 5, 6, 7, 8, 9, 10], weights=[5, 8, 12, 15, 15, 15, 12, 10, 8])[0]
            specialty = random.choice(SPECIALTIES)
            lv = max(1, skill - random.randint(0, 2))
            weapon_bonus = random.choice([0, 0, 1, 1, 2, 3])
            npcs.append({
                "id": -random.randint(100000, 999999),
                "name": name,
                "specialty": specialty,
                "skill": skill,
                "lv": lv,
                "weapon_bonus": weapon_bonus,
                "power": round(skill + weapon_bonus + lv * 0.5, 1),
                "missions": random.randint(10, 200),
                "is_npc": True,
                "poached": False,
            })
        npcs.sort(key=lambda x: x["power"], reverse=True)
        self._npc_leaderboard = npcs
        return npcs

    def poach_leaderboard(self, npc_id: int):
        """从排行榜挖角 NPC 杀手"""
        npcs = getattr(self, '_npc_leaderboard', [])
        target = None
        for n in npcs:
            if n["id"] == npc_id and not n.get("poached"):
                target = n
                break
        if not target:
            return "这个杀手已经不在排行榜上了。"

        cost = 8000 + target["skill"] * 5000
        if self.game_state["funds"] < cost:
            return f"资金不够挖角 {target['name']}，需要 ¥{cost}。"
        if self.game_state["ap"] < 1:
            return "行动力不够了。"
        rep_bonus = self.game_state["reputation"] * 0.003
        success_chance = min(0.8, 0.2 + rep_bonus - target["skill"] * 0.05)

        if random.random() < success_chance:
            self._modify_state("funds", -cost)
            self._modify_state("ap", -1)
            target["poached"] = True
            new_h = self._generate_hitman(target["skill"])
            new_h["name"] = target["name"]
            new_h["specialty"] = target["specialty"]
            new_h["lv"] = target["lv"]
            new_h["missions_completed"] = target["missions"]
            if target.get("weapon_bonus", 0) > 0:
                for w in self.game_state["weapons"]:
                    if not w["owned"] and w["bonus"] == target["weapon_bonus"]:
                        w["owned"] = True
                        w["equipped_by"] = new_h["id"]
                        new_h["weapon_id"] = w["id"]
                        break
            self.game_state["hitmen"].append(new_h)
            return f"挖角成功！{target['name']} 加入了你的组织！消耗 ¥{cost}，1AP。"
        else:
            loss = cost // 2
            self._modify_state("funds", -loss)
            self._modify_state("ap", -1)
            self._modify_state("reputation", -1)
            return f"挖角失败……{target['name']} 拒绝了你。损失 ¥{loss}，声望-1。"

    def pickup_encounter(self):
        """捡人"""
        enc = self._action_context.pop("encounter", None)
        if not enc:
            return "没有可以招募的人。"
        if self.game_state["funds"] < enc["cost"]:
            return f"资金不够，需要 ¥{enc['cost']}。"
        if self.game_state["ap"] <= 0:
            return "行动力不够了。"
        self._modify_state("funds", -enc["cost"])
        self._modify_state("ap", -1)
        new_h = self._generate_hitman(enc["skill"])
        new_h["name"] = enc["name"]
        new_h["specialty"] = enc["specialty"]
        self.game_state["hitmen"].append(new_h)
        return f"招募成功！{enc['name']} 加入了组织（{enc['specialty']}，战力{enc['skill']}）。"

    def investigate_mole(self, hitman_id: int):
        """调查杀手是否是内奸"""
        if self.game_state["ap"] <= 0:
            return "行动力不够。"
        hitman = None
        for h in self.game_state["hitmen"]:
            if h["id"] == hitman_id:
                hitman = h
                break
        if not hitman:
            return "找不到这个杀手。"
        self._modify_state("ap", -1)
        if hitman["_is_mole"]:
            if random.random() < 0.7:
                hitman["_is_mole"] = False
                owner = hitman.get("mole_owner", "未知组织")
                return f"调查结果：{hitman['name']} 是{owner}安插的内奸！已清除。"
            else:
                return f"调查 {hitman['name']} 没有发现异常……"
        else:
            return f"调查 {hitman['name']} 没有发现异常。"

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
