TAX_RATE = 0.08


def total(price):
    return round(price * (1 + TAX_RATE), 2)
