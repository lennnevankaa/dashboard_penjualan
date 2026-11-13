def rp(value):
    return "Rp " + f"{float(value):,.0f}".replace(",", ".")


def num(value):
    return f"{float(value):,.0f}".replace(",", ".")


def pct(value):
    return f"{float(value):.1f}%".replace(".", ",")