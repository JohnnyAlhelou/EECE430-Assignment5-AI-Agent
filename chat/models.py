from django.db import models


class Item(models.Model):
    name = models.CharField(max_length=100, unique=True)
    quantity = models.IntegerField(default=0)
    price=models.DecimalField(max_digits=10,decimal_places=2,default=0.00)

    def __str__(self):
        return f"{self.name} ({self.quantity}) - $/unit{self.price}"
