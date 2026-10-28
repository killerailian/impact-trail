from shop.api import quote


def test_quote():
    assert quote([100])["total"] == 108
