"""Guru Spatial Grid (GSG) – Deterministic Geographic Cells (Platform Layer)

Converts GPS coordinates into a deterministic geographic cell that can be fed into GSP placement.
Used for location‑aware search, merchant placement, and future hierarchical spatial queries.
"""

GSG_COLS = 26               # matches A‑Z for naming consistency
GSG_ROWS = 100000
CELL_SIZE = 0.001           # ~111 metres per cell at the equator

def gps_to_gsg(lat: float, lon: float):
    """
    Convert a GPS coordinate to a GSG cell and its GSP‑compatible (L, S, c) tuple.

    Returns:
        gsg_cell : (grid_x, grid_y)   – raw GSG coordinates
        gsp_params : (L, S, c)        – ready for gsp_place()
    """
    # 1. Raw GSG cell indices
    grid_x = int((lon + 180) / CELL_SIZE)
    grid_y = int((lat + 90) / CELL_SIZE)

    # 2. Map to GSP parameters within the 26×100k virtual grid
    L = grid_y % GSG_ROWS          # latitude component → row
    S = grid_x % GSG_ROWS          # longitude component → row
    c = (grid_x + grid_y) % GSG_COLS  # column 0‑25 (A‑Z)

    return (grid_x, grid_y), (L, S, c)