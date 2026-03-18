import requests
import json
import random
from datetime import datetime, timedelta
import os

# ─── CONFIG ───────────────────────────────────────────────────────────────────
USERNAME = os.environ.get("GITHUB_USERNAME", "borbacassi")
TOKEN    = os.environ.get("GITHUB_TOKEN", "")

# Cores do tema Gotham (igual ao seu stats card)
COLORS = {
    0: "#1a1b27",   # vazio
    1: "#0d3b2e",   # commit fraco
    2: "#0e6640",   # commit médio
    3: "#13a35a",   # commit forte
    4: "#1eff8e",   # commit máximo
}

# Peças do Tetris (formatos)
TETROMINOS = {
    "I": [(0,0),(0,1),(0,2),(0,3)],
    "O": [(0,0),(0,1),(1,0),(1,1)],
    "T": [(0,0),(0,1),(0,2),(1,1)],
    "S": [(0,1),(0,2),(1,0),(1,1)],
    "Z": [(0,0),(0,1),(1,1),(1,2)],
    "L": [(0,0),(1,0),(2,0),(2,1)],
    "J": [(0,1),(1,1),(2,1),(2,0)],
}

PIECE_COLORS = {
    "I": "#00f0f0",
    "O": "#f0f000",
    "T": "#a000f0",
    "S": "#00f000",
    "Z": "#f00000",
    "L": "#f0a000",
    "J": "#0000f0",
}

# ─── BUSCA COMMITS ────────────────────────────────────────────────────────────
def get_contributions(username, token):
    headers = {"Authorization": f"bearer {token}"} if token else {}
    query = """
    query($username: String!) {
      user(login: $username) {
        contributionsCollection {
          contributionCalendar {
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
      }
    }
    """
    resp = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": {"username": username}},
        headers=headers
    )
    data = resp.json()
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    
    grid = []
    for week in weeks[-52:]:  # últimas 52 semanas
        col = []
        for day in week["contributionDays"]:
            count = day["contributionCount"]
            if count == 0:   level = 0
            elif count <= 2: level = 1
            elif count <= 5: level = 2
            elif count <= 9: level = 3
            else:            level = 4
            col.append(level)
        # preenche até 7 dias
        while len(col) < 7:
            col.append(0)
        grid.append(col)
    return grid  # grid[col][row]

# ─── GERA FRAMES ──────────────────────────────────────────────────────────────
def generate_frames(grid, num_frames=60):
    COLS = len(grid)
    ROWS = 7
    frames = []
    
    # Estado das peças caindo
    pieces = []
    for _ in range(8):
        name = random.choice(list(TETROMINOS.keys()))
        col  = random.randint(0, COLS - 3)
        pieces.append({
            "name": name,
            "color": PIECE_COLORS[name],
            "col": col,
            "row": -2,
            "speed": random.uniform(0.3, 0.8),
            "y_float": float(random.randint(-10, -1)),
        })
    
    for f in range(num_frames):
        frame_pieces = []
        for p in pieces:
            p["y_float"] += p["speed"]
            p["row"] = int(p["y_float"])
            # reseta quando sai da tela
            if p["row"] > ROWS + 2:
                p["name"]    = random.choice(list(TETROMINOS.keys()))
                p["color"]   = PIECE_COLORS[p["name"]]
                p["col"]     = random.randint(0, COLS - 3)
                p["y_float"] = float(random.randint(-8, -1))
                p["row"]     = int(p["y_float"])
                p["speed"]   = random.uniform(0.3, 0.8)
            frame_pieces.append(dict(p))
        frames.append(frame_pieces)
    return frames

# ─── GERA SVG ────────────────────────────────────────────────────────────────
def generate_svg(grid, frames):
    COLS     = len(grid)
    ROWS     = 7
    CELL     = 11
    GAP      = 2
    PAD      = 10
    W        = COLS * (CELL + GAP) + PAD * 2
    H        = ROWS * (CELL + GAP) + PAD * 2 + 20
    DURATION = len(frames) * 0.15  # segundos totais

    svg = f'''<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}"
     xmlns="http://www.w3.org/2000/svg">
  <style>
    rect {{ rx: 2; ry: 2; }}
  </style>
  <rect width="{W}" height="{H}" fill="#1a1b27" rx="8"/>
'''

    # ── grid de commits (estático) ──
    for c, col in enumerate(grid):
        for r, level in enumerate(col):
            x = PAD + c * (CELL + GAP)
            y = PAD + 20 + r * (CELL + GAP)
            svg += f'  <rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" fill="{COLORS[level]}" rx="2"/>\n'

    # ── peças caindo (animadas) ──
    for fi, frame_pieces in enumerate(frames):
        t_start = fi * 0.15
        t_end   = t_start + 0.15
        # visibilidade: só aparece neste frame
        for p in frame_pieces:
            for (dr, dc) in TETROMINOS[p["name"]]:
                fc = p["col"] + dc
                fr = p["row"] + dr
                if 0 <= fc < COLS and 0 <= fr < ROWS:
                    x = PAD + fc * (CELL + GAP)
                    y = PAD + 20 + fr * (CELL + GAP)
                    uid = f"p{fi}_{fc}_{fr}"
                    svg += f'''  <rect id="{uid}" x="{x}" y="{y}" width="{CELL}" height="{CELL}"
        fill="{p['color']}" rx="2" opacity="0">
    <animate attributeName="opacity"
      values="0;1;0" keyTimes="0;{t_start/DURATION:.4f};{t_end/DURATION:.4f}"
      dur="{DURATION}s" repeatCount="indefinite"/>
  </rect>\n'''

    svg += "</svg>"
    return svg

# ─── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Buscando commits de {USERNAME}...")
    try:
        grid = get_contributions(USERNAME, TOKEN)
        print(f"Grid: {len(grid)} semanas x 7 dias")
    except Exception as e:
        print(f"Erro ao buscar commits: {e}. Usando grid de exemplo.")
        grid = [[random.randint(0, 4) for _ in range(7)] for _ in range(52)]

    print("Gerando frames...")
    frames = generate_frames(grid, num_frames=80)

    print("Gerando SVG...")
    svg = generate_svg(grid, frames)

    output = "tetris.svg"
    with open(output, "w") as f:
        f.write(svg)
    print(f"SVG salvo em: {output}")
