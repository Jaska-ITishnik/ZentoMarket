from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Address, Brand, Cart, CartItem, Category, Chat, ChatMessage, DeliveryPoint,
    Notification, Order, OrderItem, Payment, Product, ProductImage,
    ProductVariant, Review, Seller, User, Wishlist,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("email", "first_name", "last_name", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active", "date_joined")
    search_fields = ("email", "username", "first_name", "last_name", "phone")
    ordering = ("-date_joined",)
    fieldsets = UserAdmin.fieldsets + (
        ("Zento ma’lumotlari", {"fields": ("phone", "avatar", "role")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Zento ma’lumotlari edited", {"fields": ("email", "phone", "avatar", "role")}),
    )


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "seller", "category", "price", "stock", "is_active", "created_at")
    list_filter = ("category", "seller", "is_active", "brand")
    search_fields = ("name", "sku", "brand__name")
    prepopulated_fields = {"slug": ("name",)}
    inlines = (ProductImageInline, ProductVariantInline)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "created_at")
    list_filter = ("is_active", "parent")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ("store_name", "user", "rating", "is_verified", "is_active")
    list_filter = ("is_verified", "is_active")
    search_fields = ("store_name", "user__email", "phone")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "price", "seller")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "user", "total", "status", "delivery_type", "payment_type", "created_at")
    list_filter = ("status", "delivery_type", "payment_type", "created_at")
    search_fields = ("order_number", "user__email")
    readonly_fields = ("order_number", "created_at", "updated_at")
    inlines = (OrderItemInline,)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "updated_at")
    search_fields = ("user__email",)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "product", "variant", "quantity", "price")
    search_fields = ("cart__user__email", "product__name")


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created_at")
    search_fields = ("user__email", "product__name")


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "city", "street", "is_default")
    list_filter = ("city", "is_default")
    search_fields = ("user__email", "city", "street", "phone")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "is_verified_purchase", "created_at")
    list_filter = ("rating", "is_verified_purchase", "created_at")
    search_fields = ("product__name", "user__email", "text")


@admin.register(DeliveryPoint)
class DeliveryPointAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "phone", "working_hours", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "address", "phone")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "provider", "transaction_id", "amount", "status", "paid_at")
    list_filter = ("provider", "status", "paid_at")
    search_fields = ("order__order_number", "transaction_id")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("user__email", "title", "message")


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 1


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ("user", "seller", "order", "product", "subject", "created_at")
    list_filter = ("seller", "created_at")
    search_fields = ("user__email", "subject", "product__name", "order__order_number")
    inlines = (ChatMessageInline,)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "is_primary", "created_at")
    list_filter = ("is_primary",)
    search_fields = ("product__name",)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "name", "sku", "extra_price", "stock", "is_active")
    list_filter = ("is_active",)
    search_fields = ("product__name", "name", "sku")
