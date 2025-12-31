class SphericalFuzzyNumber:
    def __init__(self, mu: float, nu: float, pi: float):
        self.mu = mu
        self.nu = nu
        self.pi = pi

    def is_valid(self) -> bool:
        return (self.mu**2 + self.nu**2 + self.pi**2) <= 1 + 1e-9

    def __str__(self):
        return f"({self.mu:.3f}; {self.nu:.3f}; {self.pi:.3f})"
