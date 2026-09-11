import uuid
from collections import defaultdict
from decimal import Decimal

from django.db import IntegrityError, transaction

from .forms import CheckoutForm
from .models import (
    Address,
    Cart,
    CartItem,
    DeliveryPoint,
    Order,
    OrderItem,
    Payment,
    Product,
    ProductVariant,
)

COURIER_FEE = Decimal("25000")
PICKUP_FEE = Decimal("0")


class CheckoutValidationError(Exception):
    pass


def generate_order_number():
    """Return a readable number; the database unique constraint remains the final guard."""
    while True:
        number = f"ZT-{uuid.uuid4().hex[:12].upper()}"
        if not Order.objects.filter(order_number=number).exists():
            return number


def _resolve_destination(user, cleaned_data):
    if cleaned_data["delivery_type"] == Order.DeliveryType.PICKUP:
        point = DeliveryPoint.objects.select_for_update().filter(
            pk=cleaned_data["delivery_point"].pk,
            is_active=True,
        ).first()
        if point is None:
            raise CheckoutValidationError("Tanlangan topshirish punkti hozir faol emas.")
        return None, point

    if cleaned_data["address_mode"] == CheckoutForm.AddressMode.EXISTING:
        address = Address.objects.select_for_update().filter(
            pk=cleaned_data["address"].pk,
            user=user,
        ).first()
        if address is None:
            raise CheckoutValidationError("Tanlangan manzil sizga tegishli emas.")
        return address, None

    address = Address.objects.create(
        user=user,
        title=cleaned_data["new_address_title"],
        city=cleaned_data["new_city"],
        street=cleaned_data["new_street"],
        house_number=cleaned_data.get("new_house_number", ""),
        phone=cleaned_data["phone"],
    )
    return address, None


def _payment_details(payment_type, order_number):
    transaction_id = f"{order_number}-{uuid.uuid4().hex[:10].upper()}"
    if payment_type == Order.PaymentType.CARD:
        return "demo_card", Payment.Status.DEMO_PENDING, f"DEMO-{transaction_id}"
    if payment_type == Order.PaymentType.CASH:
        return "cash", Payment.Status.CASH_ON_DELIVERY, f"CASH-{transaction_id}"
    return "installment_demo", Payment.Status.INSTALLMENT_REVIEW, f"INST-{transaction_id}"


def _place_order_atomic(user, cleaned_data):
    with transaction.atomic():
        cart = Cart.objects.select_for_update().filter(user=user).first()
        if cart is None:
            raise CheckoutValidationError("Savat bo‘sh. Buyurtma uchun mahsulot qo‘shing.")

        existing = Order.objects.filter(
            checkout_token=cleaned_data["checkout_token"],
        ).first()
        if existing is not None:
            if existing.user_id == user.pk:
                return existing, False
            raise CheckoutValidationError("Checkout so‘rovi eskirgan. Sahifani yangilang.")

        cart_items = list(
            CartItem.objects.select_for_update()
            .filter(cart=cart)
            .order_by("product_id", "variant_id", "id")
        )
        if not cart_items:
            raise CheckoutValidationError("Savat bo‘sh. Buyurtma uchun mahsulot qo‘shing.")

        product_ids = sorted({item.product_id for item in cart_items})
        variant_ids = sorted({item.variant_id for item in cart_items if item.variant_id})
        products = {
            product.pk: product
            for product in Product.objects.select_for_update().filter(pk__in=product_ids, is_active=True)
        }
        variants = {
            variant.pk: variant
            for variant in ProductVariant.objects.select_for_update().filter(
                pk__in=variant_ids, is_active=True
            )
        }

        product_quantities = defaultdict(int)
        variant_quantities = defaultdict(int)
        for item in cart_items:
            product = products.get(item.product_id)
            if product is None:
                raise CheckoutValidationError("Savatdagi mahsulotlardan biri sotuvdan olingan.")
            product_quantities[item.product_id] += item.quantity
            if item.variant_id:
                variant = variants.get(item.variant_id)
                if variant is None or variant.product_id != item.product_id:
                    raise CheckoutValidationError(f"{product.name} varianti hozir mavjud emas.")
                variant_quantities[item.variant_id] += item.quantity

        for product_id, quantity in product_quantities.items():
            product = products[product_id]
            if product.stock < quantity:
                raise CheckoutValidationError(
                    f"{product.name} uchun faqat {product.stock} dona qoldi. Savatni yangilang."
                )
        for variant_id, quantity in variant_quantities.items():
            variant = variants[variant_id]
            if variant.stock < quantity:
                raise CheckoutValidationError(
                    f"{products[variant.product_id].name} — {variant.name} uchun faqat {variant.stock} dona qoldi."
                )

        address, delivery_point = _resolve_destination(user, cleaned_data)
        delivery_fee = (
            PICKUP_FEE
            if cleaned_data["delivery_type"] == Order.DeliveryType.PICKUP
            else COURIER_FEE
        )
        item_total = Decimal("0")
        order_lines = []
        for item in cart_items:
            product = products[item.product_id]
            variant = variants.get(item.variant_id)
            price = product.price + variant.extra_price if variant else product.price
            item_total += price * item.quantity
            order_lines.append((item, product, variant, price))

        order = Order.objects.create(
            user=user,
            order_number=generate_order_number(),
            checkout_token=cleaned_data["checkout_token"],
            address=address,
            delivery_point=delivery_point,
            recipient_phone=cleaned_data["phone"],
            total=item_total + delivery_fee,
            delivery_fee=delivery_fee,
            delivery_type=cleaned_data["delivery_type"],
            payment_type=cleaned_data["payment_type"],
            notes=cleaned_data.get("notes", ""),
        )
        OrderItem.objects.bulk_create([
            OrderItem(
                order=order,
                product=product,
                seller=product.seller,
                product_name=product.name,
                variant_name=variant.name if variant else "",
                sku=variant.sku if variant else product.sku,
                price=price,
                quantity=item.quantity,
            )
            for item, product, variant, price in order_lines
        ])

        provider, payment_status, transaction_id = _payment_details(
            cleaned_data["payment_type"], order.order_number
        )
        Payment.objects.create(
            order=order,
            provider=provider,
            transaction_id=transaction_id,
            amount=order.total,
            status=payment_status,
        )

        for product_id, quantity in product_quantities.items():
            product = products[product_id]
            product.stock -= quantity
            product.save(update_fields=("stock", "updated_at"))
        for variant_id, quantity in variant_quantities.items():
            variant = variants[variant_id]
            variant.stock -= quantity
            variant.save(update_fields=("stock", "updated_at"))

        CartItem.objects.filter(cart=cart).delete()
        return order, True


def place_order(user, cleaned_data):
    for attempt in range(3):
        try:
            return _place_order_atomic(user, cleaned_data)
        except IntegrityError:
            existing = Order.objects.filter(
                user=user,
                checkout_token=cleaned_data["checkout_token"],
            ).first()
            if existing is not None:
                return existing, False
            if attempt == 2:
                raise
