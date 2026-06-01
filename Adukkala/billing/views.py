from django.shortcuts import render
from django.http import JsonResponse
from .models import Item, Order, OrderItem, Customer, Expense, ExpenseItem
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

from django.contrib.auth import login as auth_login, logout, authenticate

def user_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect("dashboard")
    else:
        form = AuthenticationForm()
    return render(request, "billing/login.html", {"form": form})

def user_logout(request):
    logout(request)
    return redirect("login")

def is_admin(user):
    return user.is_superuser

@login_required
def dashboard(request):
    items = Item.objects.all()
    customers = Customer.objects.all()
    # ... rest of the code ...

    if request.method == "POST":
        data = json.loads(request.body)

        customer = None
        customer_id = data.get("customer_id")
        
        # Get payment status, default to True (paid)
        is_paid = data.get("is_paid", True)

        # Handle customer for unpaid bills
        if not is_paid:
            customer_name = data.get("customer_name", "").strip()
            customer_phone = data.get("customer_phone", "").strip()
            
            if customer_id:
                # Existing customer selected
                customer = Customer.objects.get(id=customer_id)
                # Update phone if provided and different
                if customer_phone and customer.phone != customer_phone:
                    customer.phone = customer_phone
                    customer.save()
            elif customer_name and customer_phone:
                # Create new customer or get existing by phone
                customer, created = Customer.objects.get_or_create(
                    phone=customer_phone,
                    defaults={"name": customer_name}
                )
                if not created and customer.name != customer_name:
                    customer.name = customer_name
                    customer.save()
        elif customer_id:
            # Paid bill with customer selected
            customer = Customer.objects.get(id=customer_id)

        order = Order.objects.create(
    customer=customer,
    item_total=sum(
        int(i["price"]) * int(i["qty"])
        for i in data["items"]
    ),
    adjustment=data.get("adjustment", 0),
    total_amount=data["total"],
    customer_given=data["given"],
    balance=data["balance"],
    is_paid=is_paid,
    payment_method=data.get("payment_method", "Google Pay")
)
        for i in data["items"]:
            OrderItem.objects.create(
                order=order,
                item_id=i["id"],
                quantity=i["qty"]
            )

        return JsonResponse({"status": "saved"})

    return render(request, "billing/dashboard.html", {
        "items": items,
        "customers": customers
    })
@login_required
def order_edit(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "full_payment":
            order.customer_given = order.total_amount
            order.balance = 0
            order.is_paid = True
        else:
            payment = int(request.POST.get("payment", 0))
            order.customer_given += payment
            order.balance = order.total_amount - order.customer_given
            if order.balance <= 0:
                order.balance = 0
                order.is_paid = True
            else:
                order.is_paid = False
        
        order.save()
        if order.customer:
            return redirect("customer_bills", customer_id=order.customer.id)
        return redirect("report")

    return render(request, "billing/order_edit.html", {
        "order": order
    })

@csrf_exempt
def update_cart(request):
    """
    AJAX endpoint to update item quantity in the session cart.
    Expects JSON: { "item_id": int, "qty": int }
    """
    if request.method == "POST":
        data = json.loads(request.body)
        item_id = str(data.get("item_id"))
        qty = int(data.get("qty", 0))
        cart = request.session.get("cart", {})
        if qty > 0:
            cart[item_id] = qty
        elif item_id in cart:
            del cart[item_id]
        request.session["cart"] = cart
        return JsonResponse({"status": "ok", "cart": cart})
    return JsonResponse({"status": "error"}, status=400)


@login_required
def report(request):
    from django.db.models import Sum
    filter_type = request.GET.get('filter', 'all')
    orders = Order.objects.all()
    
    now = timezone.now()
    
    if filter_type == 'today':
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        orders = orders.filter(created_at__gte=start_of_day)
    elif filter_type == 'weekly':
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        orders = orders.filter(created_at__gte=start_of_week)
    elif filter_type == 'monthly':
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        orders = orders.filter(created_at__gte=start_of_month)

    orders = orders.order_by("-id")
    
    # Calculate totals
    summary = orders.aggregate(
        total_sales=Sum('total_amount'),
        total_given=Sum('customer_given')
    )
    
    # Calculate only actual debt (unpaid balances)
    unpaid_total = orders.filter(is_paid=False).aggregate(res=Sum('balance'))['res'] or 0
    
    sales = summary['total_sales'] or 0
    
    totals = {
        'total_sales': sales,
        'total_given': summary['total_given'] or 0,
        'total_balance': unpaid_total,
        'net_amount': sales - unpaid_total
    }
    
    return render(request, "billing/report.html", {
        "orders": orders,
        "totals": totals,
        "filter_type": filter_type
    })
@login_required
def report_detail(request, order_id):
    order = Order.objects.get(id=order_id)
    items = OrderItem.objects.filter(order=order).select_related("item")

    bill_items = []
    for oi in items:
        bill_items.append({
            "name": oi.item.name,
            "price": oi.item.price,
            "qty": oi.quantity,
            "total": oi.quantity * oi.item.price
        })

    return render(request, "billing/report_detail.html", {
        "order": order,
        "bill_items": bill_items
    })

@login_required
@user_passes_test(is_admin)
def items_list(request):
    items = Item.objects.all()
    return render(request, "billing/items_list.html", {"items": items})


@login_required
@user_passes_test(is_admin)
@login_required
@user_passes_test(is_admin)
def item_add(request):
    if request.method == "POST":
        Item.objects.create(
            name=request.POST.get("name"),
            price=request.POST.get("price"),
            image=request.FILES.get("image")
        )
        return redirect("items")
    return render(request, "billing/item_form.html")


@login_required
@user_passes_test(is_admin)
def item_edit(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.method == "POST":
        item.name = request.POST.get("name")
        item.price = request.POST.get("price")
        if request.FILES.get("image"):
            item.image = request.FILES.get("image")
        item.save()
        return redirect("items")
    return render(request, "billing/item_form.html", {"item": item})


@login_required
@user_passes_test(is_admin)
def item_delete(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.method == "POST":
        item.delete()
        return redirect("items")
    return render(request, "billing/item_delete.html", {"item": item})

@login_required
def unpaid_bills(request):
    unpaid_orders = Order.objects.filter(is_paid=False).order_by("-id")
    total_unpaid = unpaid_orders.aggregate(res=Sum('balance'))['res'] or 0
    return render(request, "billing/unpaid_bills.html", {
        "orders": unpaid_orders,
        "total_unpaid": total_unpaid
    })

@csrf_exempt
def customer_create(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get("name", "").strip()
            phone = data.get("phone", "").strip()
            address = data.get("address", "").strip()

            if not name or not phone:
                return JsonResponse({"success": False, "message": "Name and phone are required"})

            # Check if customer with this phone already exists
            existing = Customer.objects.filter(phone=phone).first()
            if existing:
                return JsonResponse({"success": False, "message": f"Customer with phone {phone} already exists"})

            customer = Customer.objects.create(
                name=name,
                phone=phone,
                address=address if address else None
            )

            return JsonResponse({"success": True, "customer_id": customer.id})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})

    return JsonResponse({"success": False, "message": "Invalid request method"})

@login_required
def customers_list(request):
    from django.db.models import Sum
    
    customers = Customer.objects.all().order_by("name")
    customer_data = []
    
    for customer in customers:
        orders = Order.objects.filter(customer=customer)
        
        # Ledger Concept:
        # Debit = Total Bill Amounts
        # Credit = Total Payments Received
        # Balance = Outstanding Dues
        
        debit = orders.aggregate(res=Sum('total_amount'))['res'] or 0
        credit = orders.aggregate(res=Sum('customer_given'))['res'] or 0
        balance = orders.filter(is_paid=False).aggregate(res=Sum('balance'))['res'] or 0
        
        customer_data.append({
            'customer': customer,
            'debit': debit,
            'credit': credit,
            'balance': balance,
            'unpaid_count': orders.filter(is_paid=False).count()
        })
    
    return render(request, "billing/customers_list.html", {"customer_data": customer_data})

@login_required
def customer_bills(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    orders = Order.objects.filter(customer=customer).order_by("-id")
    
    # Calculate ledger summary
    customer.unpaid_total = orders.filter(is_paid=False).aggregate(res=Sum('balance'))['res'] or 0
    customer.total_billed = orders.aggregate(res=Sum('total_amount'))['res'] or 0
    customer.total_paid = orders.aggregate(res=Sum('customer_given'))['res'] or 0
    
    return render(request, "billing/customer_bills.html", {
        "customer": customer,
        "orders": orders
    })

@login_required
def customer_edit(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    if request.method == "POST":
        customer.name = request.POST.get("name")
        customer.phone = request.POST.get("phone")
        customer.address = request.POST.get("address")
        customer.save()
        return redirect("customers_list")
    return render(request, "billing/customer_form.html", {"customer": customer})

@login_required
def customer_pay_all(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    unpaid_orders = Order.objects.filter(customer=customer, is_paid=False)
    
    for order in unpaid_orders:
        order.customer_given = order.total_amount
        order.balance = 0
        order.is_paid = True
        order.save()
        
    return redirect("customers_list")

from .models import Expense

from django.utils import timezone
from datetime import timedelta

@login_required
@user_passes_test(is_admin)
def expense_list(request):
    filter_type = request.GET.get('filter', 'all')
    expenses = Expense.objects.all()
    
    now = timezone.now()
    
    if filter_type == 'today':
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        expenses = expenses.filter(date__gte=start_of_day)
    elif filter_type == 'weekly':
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        expenses = expenses.filter(date__gte=start_of_week)
    elif filter_type == 'monthly':
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        expenses = expenses.filter(date__gte=start_of_month)
        
    expenses = expenses.order_by("-date")
    total_expenses = sum(e.amount for e in expenses)
    
    return render(request, "billing/expense_list.html", {
        "expenses": expenses,
        "total_expenses": total_expenses,
        "filter_type": filter_type
    })

@login_required
@user_passes_test(is_admin)
def expense_add(request):
    if request.method == "POST":
        Expense.objects.create(
            description=request.POST.get("description"),
            amount=request.POST.get("amount")
        )
        return redirect("expense_list")

    expense_items = ExpenseItem.objects.all()

    return render(request, "billing/expense_form.html", {
        "expense_items": expense_items
    })

@login_required
@user_passes_test(is_admin)
def expense_items_list(request):
    expense_items = ExpenseItem.objects.all()
    return render(request, "billing/expense_items_list.html", {"expense_items": expense_items})


@login_required
@user_passes_test(is_admin)
def expense_item_add(request):
    if request.method == "POST":
        ExpenseItem.objects.create(
            name=request.POST.get("name"),
            category=request.POST.get("category")
        )
        return redirect("expense_items")
    return render(request, "billing/expense_item_form.html")


@login_required
@user_passes_test(is_admin)
def expense_item_edit(request, pk):
    expense_item = get_object_or_404(ExpenseItem, pk=pk)
    if request.method == "POST":
        expense_item.name = request.POST.get("name")
        expense_item.category = request.POST.get("category")
        expense_item.save()
        return redirect("expense_items")
    return render(request, "billing/expense_item_form.html", {"expense_item": expense_item})


@login_required
@user_passes_test(is_admin)
def expense_item_delete(request, pk):
    expense_item = get_object_or_404(ExpenseItem, pk=pk)
    if request.method == "POST":
        expense_item.delete()
        return redirect("expense_items")
    return render(request, "billing/expense_item_delete.html", {"expense_item": expense_item})

from django.contrib.auth.models import User

@login_required
@user_passes_test(is_admin)
def user_list(request):
    users = User.objects.all().order_by("-id")
    return render(request, "billing/user_list.html", {"users": users})

@login_required
@user_passes_test(is_admin)
def user_add(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        role = request.POST.get("role")
        
        if User.objects.filter(username=username).exists():
            return render(request, "billing/user_form.html", {"error": "Username already exists"})
            
        is_super = (role == "admin")
        user = User.objects.create_user(username=username, password=password)
        user.is_superuser = is_super
        user.is_staff = True # Always set staff to True so they can log in
        user.save()
        return redirect("user_list")
        
    return render(request, "billing/user_form.html")

@login_required
@user_passes_test(is_admin)
def user_password_reset(request, user_id):
    user_to_reset = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        new_password = request.POST.get("password")
        if new_password:
            user_to_reset.set_password(new_password)
            user_to_reset.save()
            return redirect("user_list")
    return render(request, "billing/user_password_reset.html", {"user_to_reset": user_to_reset})


