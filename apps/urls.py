from django.urls import path
from django.views.generic import TemplateView


app_name = "apps"


def page(template_name, page_title, **extra_context):
    """Create a temporary static page view until domain views are implemented."""
    context = {"page_title": page_title, **extra_context}
    return TemplateView.as_view(template_name=template_name, extra_context=context)


urlpatterns = [
    path("", page("index.html", "Zento — hammasi bir joyda"), name="index"),
    path("about/", page("about.html", "Biz haqimizda — Zento"), name="about"),
    path("account/", page("account.html", "Shaxsiy kabinet — Zento", active_page="account"), name="account"),
    path("addresses/", page("addresses.html", "Manzillarim — Zento", active_page="addresses"), name="addresses"),
    path("cart/", page("cart.html", "Savat — Zento"), name="cart"),
    path("catalog/", page("catalog.html", "Katalog — Zento"), name="catalog"),
    path("category/", page("category.html", "Smartfonlar — Zento"), name="category"),
    path("chat/", page("chat.html", "Yordam chat — Zento", active_page="chat"), name="chat"),
    path("checkout/", page("checkout.html", "Buyurtmani rasmiylashtirish — Zento", compact_layout=True), name="checkout"),
    path("compare/", page("compare.html", "Mahsulotlarni taqqoslash — Zento"), name="compare"),
    path("contact/", page("contact.html", "Kontaktlar — Zento"), name="contact"),
    path("faq/", page("faq.html", "Yordam markazi — Zento"), name="faq"),
    path("forgot-password/", page("forgot-password.html", "Parolni tiklash — Zento", compact_layout=True), name="forgot-password"),
    path("login/", page("login.html", "Kirish — Zento", compact_layout=True), name="login"),
    path("notifications/", page("notifications.html", "Xabarnomalar — Zento", active_page="notifications"), name="notifications"),
    path("order-detail/", page("order-detail.html", "Buyurtma № ZT-108248 — Zento"), name="order-detail"),
    path("orders/", page("orders.html", "Buyurtmalarim — Zento", active_page="orders"), name="orders"),
    path("pickup/", page("pickup.html", "Topshirish punktlari — Zento"), name="pickup"),
    path("product/", page("product.html", "Samsung Galaxy A55 5G — Zento"), name="product"),
    path("search/", page("search.html", "“Simsiz quloqchin” qidiruvi — Zento"), name="search"),
    path("sell/", page("sell.html", "Zento’da soting"), name="sell"),
    path("seller/", page("seller.html", "Zento Electronics do‘koni"), name="seller"),
    path("signup/", page("signup.html", "Ro‘yxatdan o‘tish — Zento", compact_layout=True), name="signup"),
    path("success/", page("success.html", "Buyurtma qabul qilindi — Zento", compact_layout=True), name="success"),
    path("wishlist/", page("wishlist.html", "Sevimlilar — Zento", active_page="wishlist"), name="wishlist"),
    path("404/", page("404.html", "Sahifa topilmadi — Zento", compact_layout=True), name="404"),
]
