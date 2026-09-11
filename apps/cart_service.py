from decimal import Decimal

from django.db import transaction
from django.db.models import Prefetch

from .models import Cart, CartItem, Product, ProductImage, ProductVariant


class CartValidationError(Exception):
    def __init__(self, message, code):
        super().__init__(message)
        self.message = message
        self.code = code


def get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def current_item_price(item):
    if item.variant_id:
        return item.variant.final_price
    return item.product.price


def available_stock(product, variant=None):
    if variant is not None:
        return min(product.stock, variant.stock)
    return product.stock


def _get_item(cart, product, variant):
    queryset = CartItem.objects.filter(cart=cart, product=product)
    if variant is None:
        return queryset.filter(variant__isnull=True).first()
    return queryset.filter(variant=variant).first()


@transaction.atomic
def add_item(user, product_id, variant_id=None, quantity=1):
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        raise CartValidationError("Miqdor noto‘g‘ri kiritildi.", "invalid_quantity")
    if quantity < 1:
        raise CartValidationError("Miqdor kamida 1 bo‘lishi kerak.", "invalid_quantity")

    product = Product.objects.select_for_update().filter(
        pk=product_id, is_active=True
    ).first()
    if product is None:
        raise CartValidationError("Mahsulot topilmadi.", "product_not_found")

    variant = None
    if variant_id:
        variant = ProductVariant.objects.select_for_update().filter(
            pk=variant_id, product=product, is_active=True
        ).first()
        if variant is None:
            raise CartValidationError("Mahsulot varianti topilmadi.", "variant_not_found")

    stock = available_stock(product, variant)
    cart = get_or_create_cart(user)
    item = _get_item(cart, product, variant)
    requested_quantity = quantity + (item.quantity if item else 0)
    if stock < requested_quantity:
        raise CartValidationError(
            f"Faqat {stock} dona mahsulot mavjud.",
            "insufficient_stock",
        )

    price = variant.final_price if variant else product.price
    if item:
        item.quantity = requested_quantity
        item.save(update_fields=("quantity", "updated_at"))
        created = False
    else:
        item = CartItem.objects.create(
            cart=cart,
            product=product,
            variant=variant,
            quantity=quantity,
            price=price,
        )
        created = True
    return item, created


@transaction.atomic
def update_item_quantity(user, item_id, quantity):
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        raise CartValidationError("Miqdor noto‘g‘ri kiritildi.", "invalid_quantity")
    if quantity < 1:
        raise CartValidationError("Miqdor kamida 1 bo‘lishi kerak.", "invalid_quantity")

    cart = get_or_create_cart(user)
    item = CartItem.objects.select_for_update().filter(cart=cart, pk=item_id).first()
    if item is None:
        raise CartValidationError("Savat qatori topilmadi.", "item_not_found")

    stock = available_stock(item.product, item.variant)
    if quantity > stock:
        raise CartValidationError(
            f"Faqat {stock} dona mahsulot mavjud.",
            "insufficient_stock",
        )
    item.quantity = quantity
    item.save(update_fields=("quantity", "updated_at"))
    return item


@transaction.atomic
def remove_item(user, item_id):
    cart = get_or_create_cart(user)
    deleted, _ = CartItem.objects.filter(cart=cart, pk=item_id).delete()
    return bool(deleted)


@transaction.atomic
def clear_cart(user):
    cart = get_or_create_cart(user)
    deleted, _ = cart.items.all().delete()
    return deleted > 0


def cart_totals(cart):
    items = list(
        cart.items.select_related("product", "product__category", "variant")
        .prefetch_related(
            Prefetch(
                "product__images",
                queryset=ProductImage.objects.order_by("-is_primary", "id"),
                to_attr="card_images",
            )
        )
        .order_by("id")
    )
    total = Decimal("0")
    quantity = 0
    for item in items:
        item.current_price = current_item_price(item)
        item.price_changed = item.current_price != item.price
        item.subtotal = item.price * item.quantity
        total += item.subtotal
        quantity += item.quantity
    return items, total, quantity
