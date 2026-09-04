from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.db.models import Avg, Count, F, IntegerField, OuterRef, Prefetch, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import FormView, TemplateView
from django.views.generic.base import View

from .forms import EmailAuthenticationForm, UserRegistrationForm
from .models import Brand, Category, Order, OrderItem, Product, ProductImage


CARD_IMAGES = Prefetch(
    "images",
    queryset=ProductImage.objects.order_by("-is_primary", "id"),
    to_attr="card_images",
)


def card_products():
    return (
        Product.objects.filter(is_active=True, stock__gt=0)
        .select_related("brand", "category", "seller")
        .prefetch_related(CARD_IMAGES)
        .annotate(
            average_rating=Coalesce(Avg("reviews__rating"), Value(0.0)),
            review_count=Count("reviews", distinct=True),
        )
    )


def with_sales_count(queryset):
    excluded_statuses = (Order.Status.CANCELLED, Order.Status.RETURNED)
    sales = (
        OrderItem.objects.filter(product=OuterRef("pk"))
        .exclude(order__status__in=excluded_statuses)
        .values("product")
        .annotate(total=Sum("quantity"))
        .values("total")
    )
    return queryset.annotate(
        sales_count=Coalesce(
            Subquery(sales, output_field=IntegerField()),
            Value(0),
        )
    )


class IndexView(TemplateView):
    template_name = "index.html"
    extra_context = {"page_title": "Zento — hammasi bir joyda"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = card_products()
        valid_orders = ~Q(
            products__order_items__order__status__in=(
                Order.Status.CANCELLED,
                Order.Status.RETURNED,
            )
        )

        context["catalog_categories"] = (
            Category.objects.filter(is_active=True)
            .annotate(
                product_count=Count(
                    "products",
                    filter=Q(products__is_active=True),
                    distinct=True,
                )
            )
            .filter(product_count__gt=0)
            .order_by("name")[:12]
        )
        context["discount_products"] = products.filter(
            old_price__isnull=False,
            old_price__gt=F("price"),
        ).order_by("-created_at")[:5]
        context["best_sellers"] = with_sales_count(products).order_by(
            "-sales_count", "-created_at"
        )[:5]
        context["popular_brands"] = (
            Brand.objects.filter(is_active=True, products__is_active=True)
            .annotate(
                sales_count=Coalesce(
                    Sum("products__order_items__quantity", filter=valid_orders),
                    Value(0),
                    output_field=IntegerField(),
                ),
                product_count=Count(
                    "products",
                    filter=Q(products__is_active=True),
                    distinct=True,
                ),
            )
            .order_by("-sales_count", "-product_count", "name")[:8]
        )
        return context


class CatalogView(TemplateView):
    template_name = "catalog.html"
    extra_context = {"page_title": "Katalog — Zento"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = (
            Category.objects.filter(is_active=True)
            .annotate(
                product_count=Count(
                    "products",
                    filter=Q(products__is_active=True),
                    distinct=True,
                )
            )
            .order_by("name")
        )
        return context


class SearchView(TemplateView):
    template_name = "search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()
        category_slug = self.request.GET.get("category", "").strip()
        brand_slug = self.request.GET.get("brand", "").strip()
        discount_only = self.request.GET.get("discount") == "1"
        sort = self.request.GET.get("sort", "popular")

        products = card_products()
        if query:
            products = products.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(sku__icontains=query)
                | Q(brand__name__icontains=query)
                | Q(category__name__icontains=query)
                | Q(seller__store_name__icontains=query)
            )
        if category_slug:
            products = products.filter(
                Q(category__slug=category_slug)
                | Q(category__parent__slug=category_slug)
            )
        if brand_slug:
            products = products.filter(brand__slug=brand_slug)
        if discount_only:
            products = products.filter(old_price__isnull=False, old_price__gt=F("price"))

        products = with_sales_count(products)
        ordering = {
            "price_asc": ("price", "name"),
            "price_desc": ("-price", "name"),
            "newest": ("-created_at",),
        }.get(sort, ("-sales_count", "-created_at"))
        products = products.order_by(*ordering)

        title = f"“{query}” bo‘yicha natijalar" if query else "Mahsulotlar"
        if category_slug and not query:
            category = Category.objects.filter(slug=category_slug).first()
            title = category.name if category else title
        if brand_slug and not query:
            brand = Brand.objects.filter(slug=brand_slug).first()
            title = brand.name if brand else title
        if discount_only and not query:
            title = "Chegirmali mahsulotlar"

        context.update(
            {
                "page_title": f"{title} — Zento",
                "search_title": title,
                "query": query,
                "products": products,
                "result_count": products.count(),
                "sort": sort,
            }
        )
        return context


class LoginPageView(LoginView):
    template_name = "login.html"
    authentication_form = EmailAuthenticationForm
    next_page = reverse_lazy("apps:index")
    extra_context = {"page_title": "Kirish — Zento", "compact_layout": True}

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("apps:index")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        if not form.cleaned_data.get("remember_me"):
            self.request.session.set_expiry(0)
        return response


class LogoutPageView(View):
    def post(self, request):
        user = self.request.user
        if user.is_authenticated:
            logout(self.request)
            return redirect("apps:index")


class RegisterPageView(FormView):
    template_name = "signup.html"
    form_class = UserRegistrationForm
    success_url = reverse_lazy("apps:index")
    extra_context = {"page_title": "Ro‘yxatdan o‘tish — Zento", "compact_layout": True}

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("apps:index")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["next"] = self.request.POST.get("next") or self.request.GET.get("next")
        return context

    def get_success_url(self):
        next_url = self.request.POST.get("next") or self.request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={self.request.get_host()},
                require_https=self.request.is_secure(),
        ):
            return next_url
        return str(self.success_url)


class CheckoutView(LoginRequiredMixin, TemplateView):
    template_name = "checkout.html"
    extra_context = {
        "page_title": "Buyurtmani rasmiylashtirish — Zento",
        "compact_layout": True,
    }
