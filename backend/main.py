"""
杀手组织老板模拟器 v2 — FastAPI 后端服务
运行于 0.0.0.0:8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.game_engine import GameEngine
from backend.system_prompt import SYSTEM_PROMPT

app = FastAPI(title="杀手组织老板模拟器 v2")

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# CORS — 允许前端页面跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局游戏引擎实例
engine = GameEngine(SYSTEM_PROMPT)


# ============================================================
# 请求/响应模型
# ============================================================

class ActRequest(BaseModel):
    action: str
    params: Optional[dict] = None


class StateResponse(BaseModel):
    success: bool = True
    narrative: str = ""
    state: dict = {}
    extra: Optional[dict] = None
    error: Optional[str] = None


# ============================================================
# API 端点
# ============================================================

@app.get("/api/state")
def get_state():
    """获取当前游戏状态"""
    return StateResponse(
        state=engine.get_state(),
    )


@app.post("/api/start")
def start_game():
    """开始新游戏"""
    try:
        narrative = engine.start_game()
        # 检查主线剧情
        story = engine.check_main_story()
        extra = {}
        if story:
            extra["main_story"] = story
        return StateResponse(
            narrative=narrative,
            state=engine.get_state(),
            extra=extra if extra else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/act")
def perform_action(req: ActRequest):
    """执行游戏动作"""
    action = req.action
    params = req.params or {}

    try:
        if action == "start":
            narrative = engine.start_game()
            extra = {}
            story = engine.check_main_story()
            if story:
                extra["main_story"] = story
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
                extra=extra if extra else None,
            )

        elif action == "recruit":
            candidates, narrative = engine.show_recruit_candidates()
            if candidates is None:
                return StateResponse(
                    error=narrative,
                    state=engine.get_state(),
                )
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
                extra={"candidates": candidates},
            )

        elif action == "hire":
            candidate_index = params.get("candidate_index")
            if candidate_index is None:
                return StateResponse(error="请选择要招募的候选人。", state=engine.get_state())
            narrative, hired = engine.hire_candidate(candidate_index)
            if hired is None:
                return StateResponse(
                    narrative=narrative,
                    state=engine.get_state(),
                    extra={"hired": False},
                )
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
                extra={"hired": True, "hitman": hired},
            )

        elif action == "contracts":
            contracts, narrative = engine.show_contracts()
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
                extra={"contracts": contracts},
            )

        elif action == "assign_contract":
            contract_id = params.get("contract_id")
            contract_index = params.get("contract_index")
            hitman_id = params.get("hitman_id")
            plan_id = params.get("plan_id")
            if hitman_id is None or (contract_id is None and contract_index is None):
                return StateResponse(
                    error="请选择契约和派遣的杀手。",
                    state=engine.get_state(),
                )
            narrative, success = engine.assign_contract(contract_index, hitman_id, contract_id, plan_id)
            extra = {"success": success}
            # 检查主线剧情
            story = engine.check_main_story()
            if story:
                extra["main_story"] = story
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
                extra=extra,
            )

        elif action == "contract_plans":
            hitman_id = params.get("hitman_id")
            contract_index = params.get("contract_index")
            if not hitman_id:
                return StateResponse(error="请选择杀手。", state=engine.get_state())
            plans = engine.get_contract_plans(hitman_id, contract_index)
            return StateResponse(
                narrative="",
                state=engine.get_state(),
                extra={"plans": plans},
            )

        elif action == "fire":
            hitman_id = params.get("hitman_id")
            if hitman_id is None:
                return StateResponse(error="请选择要解雇的杀手。", state=engine.get_state())
            narrative = engine.fire_hitman(hitman_id)
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
            )

        elif action == "end_day":
            result = engine.end_day()
            narrative, event, encounter, upgrade = result
            extra = {"event": event, "encounter": encounter, "upgrade": upgrade}
            # 检查主线剧情
            story = engine.check_main_story()
            if story:
                extra["main_story"] = story
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
                extra=extra,
            )

        elif action == "save":
            slot = params.get("slot", 1)
            result = engine.save_game(slot)
            return StateResponse(
                narrative=f"💾 存档已保存（第{slot}栏）",
                state=engine.get_state(),
                extra=result,
            )

        elif action == "load":
            slot = params.get("slot", 1)
            success = engine.load_game(slot)
            if not success:
                return StateResponse(
                    error=f"存档栏 {slot} 为空",
                    state=engine.get_state(),
                )
            return StateResponse(
                narrative=f"📂 存档已读取（第{slot}栏）",
                state=engine.get_state(),
            )

        elif action == "list_saves":
            saves = engine.list_saves()
            return StateResponse(
                narrative="",
                state=engine.get_state(),
                extra={"saves": saves},
            )

        elif action == "rivals":
            rivals, narrative = engine.show_rivals()
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
                extra={"rivals": rivals},
            )

        elif action == "attack_rival":
            rival_id = params.get("rival_id")
            hitman_ids = params.get("hitman_ids", params.get("hitman_id"))
            if not rival_id or not hitman_ids:
                return StateResponse(error="请选择目标和派遣的杀手。", state=engine.get_state())
            if isinstance(hitman_ids, int):
                hitman_ids = [hitman_ids]
            narrative = engine.attack_rival(rival_id, hitman_ids)
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
            )

        elif action == "weapon_shop":
            weapons, discount, narrative = engine.show_weapon_shop()
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
                extra={"weapons": weapons, "discount": discount},
            )

        elif action == "buy_weapon":
            weapon_id = params.get("weapon_id")
            if weapon_id is None:
                return StateResponse(error="请选择要购买的武器。", state=engine.get_state())
            narrative = engine.buy_weapon(weapon_id)
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
            )

        elif action == "equip_weapon":
            hitman_id = params.get("hitman_id")
            weapon_id = params.get("weapon_id")
            if not hitman_id or not weapon_id:
                return StateResponse(error="请选择杀手和武器。", state=engine.get_state())
            narrative = engine.equip_weapon(hitman_id, weapon_id)
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
            )

        elif action == "unequip_weapon":
            hitman_id = params.get("hitman_id")
            if not hitman_id:
                return StateResponse(error="请选择杀手。", state=engine.get_state())
            narrative = engine.unequip_weapon(hitman_id)
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
            )

        elif action == "training":
            options, narrative = engine.show_training()
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
                extra={"training": options},
            )

        elif action == "do_training":
            training_id = params.get("training_id")
            hitman_id = params.get("hitman_id")
            if not training_id or not hitman_id:
                return StateResponse(error="请选择训练项目和杀手。", state=engine.get_state())
            narrative = engine.do_training(training_id, hitman_id)
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
            )

        elif action == "investigate":
            hitman_id = params.get("hitman_id")
            if not hitman_id:
                return StateResponse(error="请选择要调查的杀手。", state=engine.get_state())
            narrative = engine.investigate_mole(hitman_id)
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
            )

        elif action == "pickup":
            narrative = engine.pickup_encounter()
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
            )

        elif action == "leaderboard":
            ranking = engine.get_leaderboard()
            return StateResponse(
                narrative="",
                state=engine.get_state(),
                extra={"ranking": ranking},
            )

        elif action == "poach_leaderboard":
            npc_id = params.get("npc_id")
            if not npc_id:
                return StateResponse(error="请选择要挖角的杀手。", state=engine.get_state())
            narrative = engine.poach_leaderboard(npc_id)
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
            )

        # ---- 新功能 API ----

        elif action == "org_info":
            info = engine.get_org_level_info()
            return StateResponse(
                narrative="",
                state=engine.get_state(),
                extra=info,
            )

        elif action == "safehouse":
            upgrades, narrative = engine.show_safehouse_upgrades()
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
                extra={"upgrades": upgrades},
            )

        elif action == "upgrade_safehouse":
            upgrade_id = params.get("upgrade_id")
            if not upgrade_id:
                return StateResponse(error="请选择升级项目。", state=engine.get_state())
            narrative = engine.upgrade_safehouse(upgrade_id)
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
            )

        elif action == "factions":
            factions, error = engine.get_factions()
            if error:
                return StateResponse(error=error, state=engine.get_state())
            return StateResponse(
                narrative="枭递来一份城市势力动态报告。",
                state=engine.get_state(),
                extra={"factions": factions},
            )

        elif action == "laundry":
            options, narrative = engine.show_laundry_options()
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
                extra={"laundry_options": options},
            )

        elif action == "do_laundry":
            channel_id = params.get("channel_id")
            if not channel_id:
                return StateResponse(error="请选择洗钱渠道。", state=engine.get_state())
            narrative = engine.do_laundry(channel_id)
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
            )

        elif action == "investments":
            types, existing, error = engine.show_investments()
            if error:
                return StateResponse(error=error, state=engine.get_state())
            return StateResponse(
                narrative="枭展开一份投资项目清单。",
                state=engine.get_state(),
                extra={"invest_types": types, "existing": existing},
            )

        elif action == "make_investment":
            invest_id = params.get("invest_id")
            if not invest_id:
                return StateResponse(error="请选择投资项目。", state=engine.get_state())
            narrative = engine.make_investment(invest_id)
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
            )

        elif action == "cadres":
            info, error = engine.show_cadres()
            if error:
                return StateResponse(error=error, state=engine.get_state())
            return StateResponse(
                narrative="",
                state=engine.get_state(),
                extra={"cadres": info},
            )

        elif action == "appoint_cadre":
            role_id = params.get("role_id")
            hitman_id = params.get("hitman_id")
            if not role_id or not hitman_id:
                return StateResponse(error="请选择职位和杀手。", state=engine.get_state())
            narrative = engine.appoint_cadre(role_id, hitman_id)
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
            )

        elif action == "remove_cadre":
            role_id = params.get("role_id")
            if not role_id:
                return StateResponse(error="请选择职位。", state=engine.get_state())
            narrative = engine.remove_cadre(role_id)
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
            )

        elif action == "hitman_profile":
            hitman_id = params.get("hitman_id")
            if not hitman_id:
                return StateResponse(error="请选择杀手。", state=engine.get_state())
            profile = engine.get_hitman_profile(hitman_id)
            if not profile:
                return StateResponse(error="找不到这个杀手。", state=engine.get_state())
            return StateResponse(
                narrative="",
                state=engine.get_state(),
                extra={"profile": profile},
            )

        elif action == "main_story":
            story = engine.check_main_story()
            return StateResponse(
                narrative="",
                state=engine.get_state(),
                extra={"main_story": story},
            )

        elif action == "resolve_story":
            level = params.get("level")
            choice_index = params.get("choice_index")
            if level is None or choice_index is None:
                return StateResponse(error="参数错误。", state=engine.get_state())
            response_text, ending = engine.resolve_main_story(level, choice_index)
            extra = {"response": response_text}
            if ending:
                extra["ending"] = ending
            return StateResponse(
                narrative=response_text,
                state=engine.get_state(),
                extra=extra,
            )

        elif action == "reset":
            engine.reset_game()
            return StateResponse(
                narrative="游戏已重置。",
                state=engine.get_state(),
            )

        else:
            return StateResponse(
                error=f"未知动作：{action}",
                state=engine.get_state(),
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---- 前端静态文件 ----
import mimetypes
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")


@app.get("/{file_path:path}")
async def serve_frontend(file_path: str):
    """提供前端静态文件"""
    if not file_path or file_path == "":
        file_path = "index.html"

    # 防止路径穿越
    full_path = (FRONTEND_DIR / file_path).resolve()
    if not str(full_path).startswith(str(FRONTEND_DIR.resolve())):
        raise HTTPException(status_code=404)

    if full_path.exists() and full_path.is_file():
        return FileResponse(str(full_path))

    # fallback: 返回 index.html（SPA 兼容）
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    raise HTTPException(status_code=404)


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
