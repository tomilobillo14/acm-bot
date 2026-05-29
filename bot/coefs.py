import math

# Coeficientes de piso según tabla
PISO_CON_ASCENSOR = {
    0: 0.90,   # PB
    1: 0.90,   # 1°
    2: 0.95,   # 2°
    3: 1.00,   # 3° y 4°
    4: 1.00,
    5: 1.05,   # 5° y 6°
    6: 1.05,
    7: 1.10,   # 7° y 8°
    8: 1.10,
}
PISO_SIN_ASCENSOR = {
    0: 1.00,   # PB
    1: 0.95,   # 1°
    2: 0.90,   # 2°
    3: 0.80,   # 3° y 4°
    4: 0.80,
}

# Coeficientes de superficie propia
SUP_COEFS = [
    (0,   30,  1.10),
    (30,  50,  1.05),
    (50,  100, 1.00),
    (100, 150, 0.95),
    (150, 250, 0.90),
]

# Categorias constructivas
ESTADO_LABELS = {
    "0.80":  "A reciclar",
    "1.00":  "Standard",
    "1.075": "Buena sin climatización",
    "1.175": "Buena con climatización",
    "1.275": "Muy buena",
    "1.10":  "Reciclado 100%",
}


def calc_piso_coef(piso: int, con_ascensor: bool = True) -> float:
    if con_ascensor:
        return PISO_CON_ASCENSOR.get(piso, 1.15)   # pisos superiores → 1.15
    else:
        return PISO_SIN_ASCENSOR.get(piso, 0.80)


def calc_sup_coef(sup_cub: float) -> float:
    if not sup_cub:
        return 1.00
    for mn, mx, coef in SUP_COEFS:
        if mn <= sup_cub < mx:
            return coef
    return 0.90


def calc_dias_coef(dias: int) -> float:
    """0.25 cada 50 días + 1"""
    if not dias:
        return 1.00
    return round(1 + math.floor(dias / 50) * 0.25, 2)


def calc_sup_homolog(sup_cub: float, sup_semi: float, sup_desc: float) -> float:
    return round(sup_cub + sup_semi * 0.5 + sup_desc / 3, 2)


def calc_coef_total(ub, piso_data, piso_coch, sup_prop, caract, edad, dias_coef) -> float:
    """Promedio de 6 componentes — igual que la fórmula del Excel"""
    total = (ub + ((piso_data + piso_coch) / 2) + sup_prop + caract + edad + dias_coef) / 6
    return round(total, 4)
