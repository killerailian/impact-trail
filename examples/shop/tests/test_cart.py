from shop.cart import checkout


def test_checkout():
    assert checkout([100]) == 108
