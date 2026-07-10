"""
Guru Spatial Grid (GSG) – Hierarchical Deterministic Geographic Cells
Platform Layer

Converts GPS coordinates into a multi‑level geographic cell.
Each level uses a progressively finer cell size, producing a unique
hierarchical identifier that can be fed into GSP placement.

Levels:
    0 – Earth          (CELL_SIZE * 64  ≈ 7.1 km)   ← only needed for global aggregation
    1 – Country        (CELL_SIZE * 16  ≈ 1.8 km)
    2 – State          (CELL_SIZE * 4   ≈ 444 m)
    3 – City           (CELL_SIZE       ≈ 111 m)
    4 – District       (CELL_SIZE / 4   ≈ 28 m)
    5 – Campus         (CELL_SIZE / 16  ≈ 7 m)
    6 – Building       (CELL_SIZE / 64  ≈ 1.7 m)

The base cell size (0.001°) gives ~111 m at the equator.
Each level subdivides the cell of the previous level by a factor of 4,
creating a quadtree‑like hierarchy.
"""

GSG_COLS = 26               # matches A‑Z for GSP compatibility
GSG_ROWS = 100000           # row space for GSP mapping
BASE_CELL_SIZE = 0.001      # ~111 metres at equator

# ── Level definitions ──────────────────────────────────
# Each level has a name, a subdivision factor (relative to base), and a typical use.
LEVELS = [
    {"name": "earth",    "divisor": 64},
    {"name": "country",  "divisor": 16},
    {"name": "state",    "divisor": 4},
    {"name": "city",     "divisor": 1},
    {"name": "district", "divisor": 0.25},
    {"name": "campus",   "divisor": 0.0625},
    {"name": "building", "divisor": 0.015625},
]


def gps_to_gsg_hierarchical(lat: float, lon: float, depth: int = None):
    """
    Convert GPS coordinates into a hierarchical GSG cell.

    Parameters:
        lat, lon – floating‑point coordinates
        depth    – how many levels to compute (0‑6).
                   If None, returns the deepest level (building).

    Returns:
        A dictionary with:
            - "cell_id" : string like "country.1234.5678" (unique human‑readable ID)
            - "gsp_params" : (L, S, c) tuple ready for gsp_place()
            - "levels" : list of dicts, one per level, with grid_x, grid_y, cell_size
    """
    if depth is None:
        depth = len(LEVELS) - 1   # default to building

    result = {"levels": []}
    prev_grid_x = prev_grid_y = 0   # for accumulating sub‑cell offsets

    for i, level in enumerate(LEVELS):
        cell_size = BASE_CELL_SIZE * level["divisor"]
        # Compute raw grid cell at this level
        grid_x = int((lon + 180) / cell_size)
        grid_y = int((lat + 90) / cell_size)

        # For levels below the top, we encode the offset within the parent cell.
        # The parent cell at the previous level had `prev_divisor` and thus
        # contained `(prev_divisor / level_divisor)` sub‑cells per side.
        if i == 0:
            # Earth level – store the absolute grid cell
            offset_x = grid_x
            offset_y = grid_y
        else:
            # How many sub‑cells per side inside the parent cell?
            parent_divisor = LEVELS[i-1]["divisor"]
            sub_per_side = int(parent_divisor / level["divisor"])
            # The local sub‑cell index within the parent
            local_x = grid_x % sub_per_side
            local_y = grid_y % sub_per_side
            # The absolute grid cell at this level is derived from parent + local offset
            offset_x = prev_grid_x * sub_per_side + local_x
            offset_y = prev_grid_y * sub_per_side + local_y

        prev_grid_x = offset_x
        prev_grid_y = offset_y

        level_data = {
            "name": level["name"],
            "grid_x": offset_x,
            "grid_y": offset_y,
            "cell_size": cell_size,
        }
        result["levels"].append(level_data)

        if i == depth:
            break

    # Build human‑readable cell_id (using the deepest computed level)
    final = result["levels"][-1]
    cell_id = f"{final['name']}.{final['grid_x']}.{final['grid_y']}"

    # Compute GSP placement parameters from the deepest level
    L = final["grid_y"] % GSG_ROWS
    S = final["grid_x"] % GSG_ROWS
    c = (final["grid_x"] + final["grid_y"]) % GSG_COLS
    result["cell_id"] = cell_id
    result["gsp_params"] = (L, S, c)

    return result


def gps_to_gsg(lat: float, lon: float) -> tuple:
    """
    Simple wrapper that returns the deepest (building‑level) GSG cell
    and its GSP parameters. This is backward‑compatible with the previous API.
    """
    data = gps_to_gsg_hierarchical(lat, lon, depth=None)
    gsg_cell = (data["levels"][-1]["grid_x"], data["levels"][-1]["grid_y"])
    return gsg_cell, data["gsp_params"]