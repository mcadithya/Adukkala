from django.contrib import admin

from .models import (
    Item,
    Customer,
    Order,
    OrderItem,
    Expense,
    ExpenseItem
)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "total_amount",
        "payment_method",
        "is_paid",
        "created_at"
    )


admin.site.register(OrderItem)
admin.site.register(Expense)
admin.site.register(ExpenseItem)