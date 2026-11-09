# -*- coding: utf-8 -*-
"""
10x10 网格巡检机器人仿真后端

依赖安装:
    pip install flask flask-cors

运行:
    python app.py

接口:
    GET  /           托管前端页面 index.html
    GET  /api/state  获取地图和机器人状态
    POST /api/move   移动机器人，JSON: {"direction": "up" | "down" | "left" | "right"}
    POST /api/reset  重置机器人到起点（附加接口，方便演示）
"""

import copy
import os
import threading

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.json.ensure_ascii = False  # 让 JSON 中的中文错误信息可读

# 允许所有来源跨域访问 /api/* 接口
CORS(app, resources={r"/api/*": {"origins": "*"}})


@app.get("/")
def index():
    """托管前端页面：访问 http://localhost:5000 即可打开。"""
    return send_from_directory(BASE_DIR, "index.html")

# ---------------------------------------------------------------------------
# 地图：0 = 可通行，1 = 障碍物
# maze[y][x] 中 y 为行（上下），x 为列（左右）
# ---------------------------------------------------------------------------
MAZE = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 0, 0, 1, 1, 1, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
    [0, 1, 1, 0, 0, 0, 0, 1, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 1, 1, 0, 0, 1, 1, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 0, 0, 0, 0, 1, 0, 0],
    [0, 0, 1, 0, 0, 1, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
]

ROWS = len(MAZE)
COLS = len(MAZE[0])

# 机器人初始状态
START_STATE = {"x": 0, "y": 0, "direction": "up"}
robot_state = dict(START_STATE)

# 方向 -> (dx, dy)；y 向下为正，所以 up 是 y-1
DIRECTION_DELTAS = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}

# Flask 开发服务器默认多线程，用锁保护全局状态
state_lock = threading.Lock()


def snapshot_state():
    """返回机器人状态和地图的副本，避免外部修改内部数据。"""
    return copy.deepcopy(robot_state), copy.deepcopy(MAZE)


@app.get("/api/state")
def get_state():
    """返回当前地图与机器人状态。"""
    with state_lock:
        robot, maze = snapshot_state()

    return jsonify(
        {
            "maze": maze,
            "robot": robot,
            "rows": ROWS,
            "cols": COLS,
        }
    )


@app.post("/api/move")
def move():
    """
    接收方向并尝试移动机器人。

    请求体:
        {"direction": "up"}   # up / down / left / right

    成功: 200，返回 {"success": true, "robot": {...}, "maze": [...]}
    失败: 400/409，返回 {"success": false, "error": "...", "robot": {...}}
          失败时机器人坐标与朝向均保持不变。
    """
    data = request.get_json(silent=True) or {}
    direction = data.get("direction")

    if direction not in DIRECTION_DELTAS:
        with state_lock:
            robot, _ = snapshot_state()
        return (
            jsonify(
                {
                    "success": False,
                    "error": "无效方向，direction 必须是 up / down / left / right",
                    "robot": robot,
                }
            ),
            400,
        )

    dx, dy = DIRECTION_DELTAS[direction]

    with state_lock:
        new_x = robot_state["x"] + dx
        new_y = robot_state["y"] + dy

        # 1. 边界检查（0-9）
        if not (0 <= new_x < COLS and 0 <= new_y < ROWS):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "移动失败：前方超出地图边界",
                        "robot": copy.deepcopy(robot_state),
                    }
                ),
                400,
            )

        # 2. 障碍物检查
        if MAZE[new_y][new_x] == 1:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "移动失败：前方有障碍物",
                        "robot": copy.deepcopy(robot_state),
                    }
                ),
                409,
            )

        # 3. 移动成功：更新坐标和朝向
        robot_state["x"] = new_x
        robot_state["y"] = new_y
        robot_state["direction"] = direction
        robot, maze = snapshot_state()

    return jsonify({"success": True, "robot": robot, "maze": maze})


@app.post("/api/reset")
def reset():
    """把机器人重置到起点（0, 0），便于前端演示。"""
    with state_lock:
        robot_state.update(START_STATE)
        robot, maze = snapshot_state()

    return jsonify({"success": True, "robot": robot, "maze": maze})


if __name__ == "__main__":
    # host=0.0.0.0 让容器外可以访问；生产环境请用 gunicorn/waitress 等
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes", "on")
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=debug)
