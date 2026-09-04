from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.fields import EmailField
from django.utils import timezone
from django.utils.text import slugify

from apps.managers import UserManager


def dated_media_upload_path(instance, filename):
    today = timezone.now()
    return f"{today:%Y/%m/%d}/{filename}"


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "Mijoz"
        SELLER = "seller", "Sotuvchi"

    # username = None
    phone = models.CharField(max_length=30, blank=True)
    email = EmailField(unique=True)
    avatar = models.ImageField(upload_to=dated_media_upload_path, blank=True, null=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    def __str__(self):
        return self.get_full_name() or self.username


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Seller(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seller_profile")
    store_name = models.CharField(max_length=150)
    logo = models.ImageField(upload_to=dated_media_upload_path, blank=True, null=True)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.store_name


class Category(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")
    image = models.ImageField(upload_to=dated_media_upload_path, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    logo = models.ImageField(upload_to=dated_media_upload_path, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    sku = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    old_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def discount_percent(self):
        if self.old_price and self.old_price > self.price:
            return round((self.old_price - self.price) / self.old_price * 100)
        return 0

    @property
    def installment_price(self):
        return self.price / 12

    def __str__(self):
        return self.name


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=dated_media_upload_path)
    is_primary = models.BooleanField(default=False)


class ProductVariant(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=120, help_text="Masalan: Qora, 8/256 GB yoki L o‘lcham")
    sku = models.CharField(max_length=100, unique=True)
    extra_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)


class Cart(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cart_items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "product", "variant"], name="unique_cart_product_variant")]


class Wishlist(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlist_items")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="unique_wishlist_product")]


class Address(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    title = models.CharField(max_length=50, default="Uy")
    city = models.CharField(max_length=100)
    street = models.CharField(max_length=255)
    house_number = models.CharField(max_length=30, blank=True)
    phone = models.CharField(max_length=30)
    is_default = models.BooleanField(default=False)


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        NEW = "new", "Yangi"
        CONFIRMED = "confirmed", "Tasdiqlangan"
        PROCESSING = "processing", "Tayyorlanmoqda"
        SHIPPED = "shipped", "Yuborilgan"
        DELIVERED = "delivered", "Yetkazilgan"
        CANCELLED = "cancelled", "Bekor qilingan"
        RETURNED = "returned", "Qaytarilgan"

    class DeliveryType(models.TextChoices):
        ADDRESS = "address", "Manzilga yetkazish"
        PICKUP = "pickup", "Topshirish punktidan olish"

    class PaymentType(models.TextChoices):
        CARD = "card", "Karta orqali"
        CASH = "cash", "Naqd pul"
        INSTALLMENT = "installment", "Muddatli to‘lov"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    order_number = models.CharField(max_length=30, unique=True)
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    delivery_type = models.CharField(max_length=20, choices=DeliveryType.choices, default=DeliveryType.ADDRESS)
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices, default=PaymentType.CARD)
    notes = models.TextField(blank=True)


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    seller = models.ForeignKey(Seller, on_delete=models.PROTECT, related_name="order_items")
    product_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    @property
    def subtotal(self):
        return self.price * self.quantity


class Review(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField(blank=True)
    is_verified_purchase = models.BooleanField(default=False)


class DeliveryPoint(TimeStampedModel):
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=30, blank=True)
    working_hours = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)


class Payment(TimeStampedModel):
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="payment")
    provider = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=150, unique=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=30, default="pending")
    paid_at = models.DateTimeField(null=True, blank=True)


class Notification(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, default="general")
    is_read = models.BooleanField(default=False)


class Chat(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chats")
    seller = models.ForeignKey(Seller, on_delete=models.SET_NULL, null=True, blank=True, related_name="chats")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="chats")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="chats")
    subject = models.CharField(max_length=200, blank=True)


class ChatMessage(TimeStampedModel):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sent_messages")
    text = models.TextField()
    is_read = models.BooleanField(default=False)
