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
        return StateResponse(
            narrative=narrative,
            state=engine.get_state(),
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
            return StateResponse(narrative=narrative, state=engine.get_state())

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
            contract_index = params.get("contract_index")
            hitman_id = params.get("hitman_id")
            if contract_index is None or hitman_id is None:
                return StateResponse(
                    error="请选择契约和派遣的杀手。",
                    state=engine.get_state(),
                )
            narrative, success = engine.assign_contract(contract_index, hitman_id)
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
                extra={"success": success},
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
            narrative, event, encounter = engine.end_day()
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
                extra={"event": event, "encounter": encounter},
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
            hitman_id = params.get("hitman_id")
            if not rival_id or not hitman_id:
                return StateResponse(error="请选择目标和派遣的杀手。", state=engine.get_state())
            narrative = engine.attack_rival(rival_id, hitman_id)
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
            )

        elif action == "weapon_shop":
            weapons, narrative = engine.show_weapon_shop()
            return StateResponse(
                narrative=narrative,
                state=engine.get_state(),
                extra={"weapons": weapons},
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

        elif action == "reset":
            engine.reset_game()
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
