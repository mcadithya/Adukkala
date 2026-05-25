from django.db import models

class Item(models.Model):
    name = models.CharField(max_length=100)
    price = models.PositiveIntegerField()
    image = models.ImageField(upload_to="items/", blank=True, null=True)

    def __str__(self):
        return self.name
class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_borrower = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Order(models.Model):

    PAYMENT_CHOICES = [
        ("Google Pay", "Google Pay"),
        ("Cash", "Cash"),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    total_amount = models.PositiveIntegerField()
    customer_given = models.PositiveIntegerField()
    balance = models.IntegerField()

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        default="Google Pay"
    )

    is_paid = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)



class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

class Expense(models.Model):
    description = models.CharField(max_length=255)
    amount = models.PositiveIntegerField()
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.description} - ₹{self.amount}"

class ExpenseItem(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

