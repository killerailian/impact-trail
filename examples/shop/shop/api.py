from .cart import checkout


def quote(prices):
    return {"total": checkout(prices), "currency": "USD"}
