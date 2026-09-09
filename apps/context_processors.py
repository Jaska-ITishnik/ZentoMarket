from .cart_service import get_or_create_cart, cart_totals
from .models import Category, Wishlist
from .compare import get_compare_ids


def navigation_categories(request):
    compare_product_ids = set(get_compare_ids(request))
    wishlist_product_ids = set()
    cart_count = 0
    if request.user.is_authenticated:
        wishlist_product_ids = set(
            Wishlist.objects.filter(user=request.user).values_list("product_id", flat=True)
        )
        _, _, cart_count = cart_totals(get_or_create_cart(request.user))

    return {
        "navigation_categories": Category.objects.filter(
            is_active=True,
            parent__isnull=True,
        ).order_by("name")[:7],
        "wishlist_product_ids": wishlist_product_ids,
        "wishlist_count": len(wishlist_product_ids),
        "compare_product_ids": compare_product_ids,
        "compare_count": len(compare_product_ids),
        "cart_count": cart_count,
    }
