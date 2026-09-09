from django.urls import path
from django.views.generic import TemplateView

from .views import (
    CatalogView,
    CategoryView,
    CompareAddView,
    CompareClearView,
    CompareRemoveView,
    CompareView,
    CheckoutView,
    IndexView,
    LoginPageView,
    LogoutPageView,
    ProductDetailView,
    RegisterPageView,
    SearchView,
    SearchSuggestionsView,
    SellerDetailView,
    WishlistToggleView,
    WishlistView,
    legacy_category_redirect,
    legacy_product_redirect,
    legacy_seller_redirect,
)

app_name = "apps"


def page(template_name, page_title, **extra_context):
    """Create a temporary static page view until domain views are implemented."""
    context = {"page_title": page_title, **extra_context}
    return TemplateView.as_view(template_name=template_name, extra_context=context)


urlpatterns = [
    path("", IndexView.as_view(), name="index"),
    path("about/", page("about.html", "Biz haqimizda — Zento"), name="about"),
    path("account/", page("account.html", "Shaxsiy kabinet — Zento", active_page="account"), name="account"),
    path("addresses/", page("addresses.html", "Manzillarim — Zento", active_page="addresses"), name="addresses"),
    path("cart/", page("cart.html", "Savat — Zento"), name="cart"),
    path("catalog/", CatalogView.as_view(), name="catalog"),
    path("category/", legacy_category_redirect, name="category-legacy"),
    path("category/<slug:slug>/", CategoryView.as_view(), name="category"),
    path("chat/", page("chat.html", "Yordam chat — Zento", active_page="chat"), name="chat"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("compare/", CompareView.as_view(), name="compare"),
    path("compare/add/<int:product_id>/", CompareAddView.as_view(), name="compare-add"),
    path("compare/remove/<int:product_id>/", CompareRemoveView.as_view(), name="compare-remove"),
    path("compare/clear/", CompareClearView.as_view(), name="compare-clear"),
    path("contact/", page("contact.html", "Kontaktlar — Zento"), name="contact"),
    path("faq/", page("faq.html", "Yordam markazi — Zento"), name="faq"),
    path("forgot-password/", page("forgot-password.html", "Parolni tiklash — Zento", compact_layout=True),
         name="forgot-password"),
    path("login/", LoginPageView.as_view(), name="login"),
    path("logout/", LogoutPageView.as_view(), name="logout"),
    path("notifications/", page("notifications.html", "Xabarnomalar — Zento", active_page="notifications"),
         name="notifications"),
    path("order-detail/", page("order-detail.html", "Buyurtma № ZT-108248 — Zento"), name="order-detail"),
    path("orders/", page("orders.html", "Buyurtmalarim — Zento", active_page="orders"), name="orders"),
    path("pickup/", page("pickup.html", "Topshirish punktlari — Zento"), name="pickup"),
    path("product/", legacy_product_redirect, name="product-legacy"),
    path("product/<slug:slug>/", ProductDetailView.as_view(), name="product"),
    path("search/", SearchView.as_view(), name="search"),
    path("search/suggestions/", SearchSuggestionsView.as_view(), name="search-suggestions"),
    path("sell/", page("sell.html", "Zento’da soting"), name="sell"),
    path("seller/", legacy_seller_redirect, name="seller-legacy"),
    path("seller/<int:pk>/", SellerDetailView.as_view(), name="seller"),
    path("seller/<str:pk_or_slug>/", SellerDetailView.as_view(), name="seller_slug"),
    path("signup/", RegisterPageView.as_view(), name="signup"),
    path("success/", page("success.html", "Buyurtma qabul qilindi — Zento", compact_layout=True), name="success"),
    path("wishlist/", WishlistView.as_view(), name="wishlist"),
    path("wishlist/toggle/<int:product_id>/", WishlistToggleView.as_view(), name="wishlist-toggle"),
    path("404/", page("404.html", "Sahifa topilmadi — Zento", compact_layout=True), name="404"),
]
