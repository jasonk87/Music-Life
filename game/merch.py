class MerchItem:
    def __init__(self, name, cost_to_make, sale_price, stock=0):
        self.name = name
        self.cost_to_make = cost_to_make
        self.sale_price = sale_price
        self.stock = stock

    def __str__(self):
        return f"{self.name} (Stock: {self.stock}) - Cost: ${self.cost_to_make}, Sell: ${self.sale_price}"

MERCH_TEMPLATES = {
    "tshirt": {"name": "Band T-Shirt", "cost": 5, "price": 20},
    "poster": {"name": "Signed Poster", "cost": 2, "price": 10},
    "vinyl": {"name": "Limited Vinyl", "cost": 15, "price": 40},
    "stickers": {"name": "Sticker Pack", "cost": 1, "price": 5}
}
