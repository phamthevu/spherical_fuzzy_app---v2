import pandas as pd

from core.model import SphericalFuzzyNumber
from core.calculate import (
    spf_sum,
    spf_mul,
    spf_coe,
    spf_pow
)

# ==========================================================
# Utils
# ==========================================================

def normalize(weights: list[float]) -> list[float]:
    total = sum(weights)
    if total == 0:
        raise ValueError("Tổng weight = 0")
    return [w / total for w in weights]


# ==========================================================
# Read weight sheet
# ==========================================================

def read_sheet_weights(excel_path: str, sheet_names: list[str]) -> list[float]:
    """
    Đọc sheet 'Weight'
    Nếu không tồn tại → mặc định weight bằng nhau
    """
    try:
        df = pd.read_excel(excel_path, sheet_name="Weight", header=None)
    except Exception:
        k = len(sheet_names)
        return [1.0 / k] * k

    weight_map = {}

    for _, row in df.iterrows():
        if pd.isna(row[0]) or pd.isna(row[1]):
            continue
        weight_map[str(row[0]).strip()] = float(row[1])

    weights = []
    for name in sheet_names:
        if name not in weight_map:
            raise ValueError(f"Thiếu weight cho sheet {name}")
        weights.append(weight_map[name])

    return normalize(weights)


# ==========================================================
# CORE AGGREGATION – MULTI SHEET
# ==========================================================

def aggregate_sheets(
    excel_path: str,
    sheet_names: list[str],
    n_rows: int,
    n_cols: int,
    method: str,                     # "SWAM" | "SWAG"
    parse_spherical_fuzzy            # hàm parse từ UI
) -> list[list[SphericalFuzzyNumber]]:
    """
    Aggregate nhiều sheet (Ans1, Ans2, ...)
    DEMATEL rule: đường chéo = (0;0;0)
    """

    # ---------- Read & normalize weights ----------
    weights = read_sheet_weights(excel_path, sheet_names)

    # ---------- Read all sheets ----------
    sheets = []
    for name in sheet_names:
        df = pd.read_excel(excel_path, sheet_name=name, header=None)
        sheets.append(df)

    # ---------- Aggregate cell-wise ----------
    result = [[None for _ in range(n_cols)] for _ in range(n_rows)]

    for i in range(n_rows):
        for j in range(n_cols):

            # 🔴 DEMATEL diagonal
            if i == j:
                result[i][j] = SphericalFuzzyNumber(0, 0, 0)
                continue

            fuzzies = []
            for s in sheets:
                cell = s.iat[i + 1, j + 1]   # dữ liệu từ row 2 col 2
                fuzzy = parse_spherical_fuzzy(str(cell))
                fuzzies.append(fuzzy)

            if method.upper() == "SWAM":
                agg = spf_swam(fuzzies, weights)
            elif method.upper() == "SWAG":
                agg = spf_swag(fuzzies, weights)
            else:
                raise ValueError("Method phải là SWAM hoặc SWAG")

            result[i][j] = agg

    return result


# ==========================================================
# SPFSWAM – Spherical Fuzzy Weighted Arithmetic Mean
# VBA:
#   res = SPFCOE(s1, w1)
#   For i = 2..k:
#       res = SPFSUM(res, SPFCOE(si, wi))
# ==========================================================

def spf_swam(
    fuzzies: list[SphericalFuzzyNumber],
    weights: list[float]
) -> SphericalFuzzyNumber:
    if not fuzzies:
        raise ValueError("Danh sách fuzzy rỗng")

    if len(fuzzies) != len(weights):
        raise ValueError("Số fuzzy và weight không khớp")

    res = spf_coe(fuzzies[0], weights[0])

    for i in range(1, len(fuzzies)):
        turn = spf_coe(fuzzies[i], weights[i])
        res = spf_sum(res, turn)

    return res


# ==========================================================
# SPFSWAG (SWGM) – Spherical Fuzzy Weighted Geometric Mean
# VBA:
#   res = SPFPOW(s1, w1)
#   For i = 2..k:
#       res = SPFMUL(res, SPFPOW(si, wi))
# ==========================================================

def spf_swag(
    fuzzies: list[SphericalFuzzyNumber],
    weights: list[float]
) -> SphericalFuzzyNumber:
    if not fuzzies:
        raise ValueError("Danh sách fuzzy rỗng")

    if len(fuzzies) != len(weights):
        raise ValueError("Số fuzzy và weight không khớp")

    res = spf_pow(fuzzies[0], weights[0])

    for i in range(1, len(fuzzies)):
        turn = spf_pow(fuzzies[i], weights[i])
        res = spf_mul(res, turn)

    return res
