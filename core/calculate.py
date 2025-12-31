import math
from core.model import SphericalFuzzyNumber


# ==========================================================
# SPFSUM
# ==========================================================
def spf_sum(s1: SphericalFuzzyNumber,
            s2: SphericalFuzzyNumber) -> SphericalFuzzyNumber:
    A1, B1, Y1 = s1.mu, s1.nu, s1.pi
    A2, B2, Y2 = s2.mu, s2.nu, s2.pi

    A = round(math.sqrt(A1**2 + A2**2 - A1**2 * A2**2), 3)
    B = round(B1 * B2, 3)
    Y = round(
        math.sqrt(
            (1 - A2**2) * Y1**2
            + (1 - A1**2) * Y2**2
            - Y1**2 * Y2**2
        ),
        3
    )

    return SphericalFuzzyNumber(A, B, Y)


# ==========================================================
# SPFMUL
# ==========================================================
def spf_mul(s1: SphericalFuzzyNumber,
            s2: SphericalFuzzyNumber) -> SphericalFuzzyNumber:
    A1, B1, Y1 = s1.mu, s1.nu, s1.pi
    A2, B2, Y2 = s2.mu, s2.nu, s2.pi

    A = round(A1 * A2, 3)
    B = round(math.sqrt(B1**2 + B2**2 - B1**2 * B2**2), 3)
    Y = round(
        math.sqrt(
            (1 - B2**2) * Y1**2
            + (1 - B1**2) * Y2**2
            - Y1**2 * Y2**2
        ),
        3
    )

    return SphericalFuzzyNumber(A, B, Y)


# ==========================================================
# SPFCOE
# ==========================================================
def spf_coe(s: SphericalFuzzyNumber,
            n: float) -> SphericalFuzzyNumber:
    A1, B1, Y1 = s.mu, s.nu, s.pi

    A = round(math.sqrt(1 - (1 - A1**2)**n), 3)
    B = round(B1**n, 3)
    Y = round(
        math.sqrt(
            (1 - A1**2)**n
            - (1 - A1**2 - Y1**2)**n
        ),
        3
    )

    return SphericalFuzzyNumber(A, B, Y)


# ==========================================================
# SPFPOW
# ==========================================================
def spf_pow(s: SphericalFuzzyNumber,
            n: float) -> SphericalFuzzyNumber:
    A1, B1, Y1 = s.mu, s.nu, s.pi

    A = round(A1**n, 3)
    B = round(math.sqrt(1 - (1 - B1**2)**n), 3)
    Y = round(
        math.sqrt(
            (1 - B1**2)**n
            - (1 - B1**2 - Y1**2)**n
        ),
        3
    )

    return SphericalFuzzyNumber(A, B, Y)


# ==========================================================
# SPFDEF
# ==========================================================
def spf_def(s: SphericalFuzzyNumber) -> float:
    A1, B1, Y1 = s.mu, s.nu, s.pi
    return (2 * A1 - Y1)**2 - (B1 - Y1)**2

