from .pricing import total


def checkout(prices):
    return sum(total(price) for price in prices)
