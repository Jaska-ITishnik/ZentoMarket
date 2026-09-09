from decimal import Decimal, InvalidOperation

from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db.models import Avg, Case, Count, F, IntegerField, OuterRef, Prefetch, Q, Subquery, Sum, Value, When
from django.http import Http404, JsonResponse
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import slugify
from django.views.generic import FormView, TemplateView
from django.views.generic.base import View

from .compare import (
    CompareValidationError,
    add_to_compare,
    clear_compare,
    get_compare_ids,
    remove_from_compare,
)
from .forms import EmailAuthenticationForm, UserRegistrationForm
from .models import Brand, Category, Order, OrderItem, Product, ProductImage, Seller, Wishlist


CARD_IMAGES = Prefetch(
    "images",
    queryset=ProductImage.objects.order_by("-is_primary", "id"),
    to_attr="card_images",
)


def card_products(in_stock=True):
    products = Product.objects.filter(is_active=True)
    if in_stock:
        products = products.filter(stock__gt=0)
    return (
        products
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


def category_descendant_ids(category):
    """Return the category and all of its descendants without assuming a fixed depth."""
    category_ids = [category.pk]
    pending_ids = [category.pk]
    while pending_ids:
        pending_ids = list(
            Category.objects.filter(parent_id__in=pending_ids, is_active=True)
            .values_list("pk", flat=True)
        )
        category_ids.extend(pending_ids)
    return category_ids


def category_breadcrumbs(category):
    breadcrumbs = []
    current = category
    while current is not None:
        breadcrumbs.append(current)
        current = current.parent
    return list(reversed(breadcrumbs))


def decimal_query_value(params, name):
    value = params.get(name, "").strip()
    if not value:
        return None
    try:
        number = Decimal(value)
    except InvalidOperation:
        return None
    return number if number >= 0 else None


def filter_and_sort_products(queryset, params):
    brand_slug = params.get("brand", "").strip()
    min_price = decimal_query_value(params, "min_price")
    max_price = decimal_query_value(params, "max_price")
    discount_only = params.get("discount") == "1"
    availability = params.get("availability", "in_stock")
    if availability not in {"in_stock", "out_of_stock", "all"}:
        availability = "in_stock"

    try:
        minimum_rating = int(params.get("rating", "") or 0)
    except ValueError:
        minimum_rating = 0
    if minimum_rating not in range(1, 6):
        minimum_rating = 0

    if brand_slug:
        queryset = queryset.filter(brand__slug=brand_slug)
    if min_price is not None:
        queryset = queryset.filter(price__gte=min_price)
    if max_price is not None:
        queryset = queryset.filter(price__lte=max_price)
    if discount_only:
        queryset = queryset.filter(old_price__isnull=False, old_price__gt=F("price"))
    if minimum_rating:
        queryset = queryset.filter(average_rating__gte=minimum_rating)
    if availability == "in_stock":
        queryset = queryset.filter(stock__gt=0)
    elif availability == "out_of_stock":
        queryset = queryset.filter(stock=0)

    queryset = with_sales_count(queryset)
    sort = params.get("sort", "popular")
    ordering = {
        "popular": ("-sales_count", "-created_at"),
        "price_asc": ("price", "name"),
        "price_desc": ("-price", "name"),
        "rating": ("-average_rating", "-review_count", "name"),
        "newest": ("-created_at",),
    }
    if sort not in ordering:
        sort = "popular"

    state = {
        "brand": brand_slug,
        "min_price": params.get("min_price", "").strip(),
        "max_price": params.get("max_price", "").strip(),
        "discount": discount_only,
        "rating": minimum_rating,
        "availability": availability,
        "sort": sort,
    }
    return queryset.order_by(*ordering[sort]), state


def paginated_product_context(request, queryset, per_page=12):
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)
    return {
        "products": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "is_paginated": page_obj.has_other_pages(),
        "filter_query": query_params.urlencode(),
        "product_count": paginator.count,
    }


class CategoryView(TemplateView):
    template_name = "category.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = get_object_or_404(
            Category.objects.select_related("parent"),
            slug=self.kwargs["slug"],
            is_active=True,
        )
        category_ids = category_descendant_ids(category)
        base_products = card_products(in_stock=False).filter(category_id__in=category_ids)
        brands = Brand.objects.filter(
            is_active=True,
            products__in=base_products,
        ).distinct().order_by("name")
        products, filter_state = filter_and_sort_products(base_products, self.request.GET)
        children = list(
            category.children.filter(is_active=True)
            .annotate(
                product_count=Count(
                    "products",
                    filter=Q(products__is_active=True, products__stock__gt=0),
                    distinct=True,
                )
            )
            .order_by("name")
        )

        context.update(paginated_product_context(self.request, products))
        context.update({
                "page_title": f"{category.name} — Zento",
                "category": category,
                "parent_category": category.parent,
                "child_categories": children,
                "breadcrumbs": category_breadcrumbs(category),
                "brands": brands,
                "filter_state": filter_state,
                "reset_url": self.request.path,
            })
        return context


class ProductDetailView(TemplateView):
    template_name = "product.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = get_object_or_404(
            Product.objects.filter(is_active=True)
            .select_related("brand", "category", "category__parent", "seller")
            .prefetch_related("images", "variants", "reviews__user")
            .annotate(
                average_rating=Coalesce(Avg("reviews__rating"), Value(0.0)),
                review_count=Count("reviews", distinct=True),
            ),
            slug=self.kwargs["slug"],
        )
        sales_count = (
            product.order_items.exclude(
                order__status__in=(Order.Status.CANCELLED, Order.Status.RETURNED)
            ).aggregate(total=Coalesce(Sum("quantity"), Value(0)))["total"]
        )
        product_images = list(product.images.order_by("-is_primary", "id"))
        variants = list(product.variants.filter(is_active=True).order_by("id"))
        selected_variant = next((variant for variant in variants if variant.stock), variants[0] if variants else None)
        display_price = selected_variant.final_price if selected_variant else product.price
        display_stock = selected_variant.stock if selected_variant else product.stock
        related_products = with_sales_count(card_products().filter(
            category=product.category
        ).exclude(pk=product.pk)).order_by("-sales_count", "-average_rating", "-created_at")[:5]

        context.update(
            {
                "page_title": f"{product.name} — Zento",
                "product": product,
                "breadcrumbs": category_breadcrumbs(product.category),
                "product_images": product_images,
                "variants": variants,
                "selected_variant": selected_variant,
                "display_price": display_price,
                "display_installment_price": display_price / 12,
                "display_stock": display_stock,
                "reviews": product.reviews.select_related("user").order_by("-created_at"),
                "sales_count": sales_count,
                "related_products": related_products,
                "is_out_of_stock": product.stock <= 0 or (selected_variant and selected_variant.stock <= 0),
            }
        )
        return context


class WishlistView(LoginRequiredMixin, TemplateView):
    template_name = "wishlist.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = (
            card_products(in_stock=False)
            .filter(wishlist_items__user=self.request.user)
            .order_by("-wishlist_items__created_at")
        )
        context.update(
            {
                "page_title": "Sevimlilar — Zento",
                "active_page": "wishlist",
                "products": products,
                "product_count": products.count(),
            }
        )
        return context


class WishlistToggleView(LoginRequiredMixin, View):
    def post(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id, is_active=True)
        item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
        if not created:
            item.delete()

        wishlist_count = Wishlist.objects.filter(user=request.user).count()
        is_wishlisted = created
        return JsonResponse(
            {
                "is_wishlisted": is_wishlisted,
                "wishlist_count": wishlist_count,
                "message": (
                    "Sevimlilarga qo‘shildi"
                    if is_wishlisted
                    else "Sevimlilardan olib tashlandi"
                ),
            }
        )


class CompareView(TemplateView):
    template_name = "compare.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product_ids = get_compare_ids(self.request)
        order = Case(
            *[When(pk=product_id, then=position) for position, product_id in enumerate(product_ids)],
            output_field=IntegerField(),
        )
        products = list(
            card_products(in_stock=False).filter(pk__in=product_ids).order_by(order)
        ) if product_ids else []
        context.update(
            {
                "page_title": "Mahsulotlarni taqqoslash — Zento",
                "products": products,
                "product_count": len(products),
            }
        )
        return context


class CompareAddView(View):
    def post(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id, is_active=True)
        try:
            product_ids, changed = add_to_compare(request, product)
        except CompareValidationError as error:
            return JsonResponse(
                {
                    "error": error.message,
                    "code": error.code,
                    "compare_count": len(get_compare_ids(request)),
                },
                status=400,
            )
        return JsonResponse(
            {
                "is_compared": True,
                "changed": changed,
                "compare_count": len(product_ids),
                "message": (
                    "Taqqoslashga qo‘shildi"
                    if changed
                    else "Mahsulot allaqachon taqqoslashda"
                ),
            }
        )


class CompareRemoveView(View):
    def post(self, request, product_id):
        product_ids, changed = remove_from_compare(request, product_id)
        return JsonResponse(
            {
                "is_compared": False,
                "changed": changed,
                "compare_count": len(product_ids),
                "message": (
                    "Taqqoslashdan olib tashlandi"
                    if changed
                    else "Mahsulot taqqoslashda yo‘q"
                ),
            }
        )


class CompareClearView(View):
    def post(self, request):
        changed = clear_compare(request)
        return JsonResponse(
            {
                "compare_count": 0,
                "changed": changed,
                "message": "Taqqoslash ro‘yxati tozalandi",
            }
        )


class SellerDetailView(TemplateView):
    template_name = "seller.html"

    def get_seller(self):
        raw_value = (
            self.kwargs.get("pk_or_slug")
            or self.kwargs.get("slug")
            or self.kwargs.get("pk")
        )
        if raw_value is None:
            raise Http404("Seller not found.")

        value = str(raw_value).strip()
        queryset = Seller.objects.filter(is_active=True)
        if value.isdigit():
            return get_object_or_404(queryset, pk=value)

        target_slug = slugify(value)
        seller = queryset.filter(store_name__iexact=value).first()
        if seller is None:
            seller = queryset.filter(store_name__icontains=value).first()
        if seller is None:
            for candidate in queryset.all():
                if slugify(candidate.store_name) == target_slug:
                    seller = candidate
                    break
        if seller is None:
            raise Http404("Seller not found.")
        return seller

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        seller = self.get_seller()
        products = with_sales_count(
            card_products(in_stock=False).filter(seller=seller)
        ).order_by("-sales_count", "-created_at")
        seller_stats = seller.products.filter(is_active=True).aggregate(
            average_product_rating=Coalesce(Avg("reviews__rating"), Value(0.0)),
            review_count=Count("reviews", distinct=True),
            total_stock=Coalesce(Sum("stock"), Value(0)),
        )
        sales_count = (
            OrderItem.objects.filter(seller=seller)
            .exclude(order__status__in=(Order.Status.CANCELLED, Order.Status.RETURNED))
            .aggregate(total=Coalesce(Sum("quantity"), Value(0)))["total"]
        )
        context.update(
            {
                "page_title": f"{seller.store_name} — Zento",
                "seller": seller,
                "products": products,
                "product_count": products.count(),
                "average_product_rating": seller_stats["average_product_rating"],
                "review_count": seller_stats["review_count"],
                "total_stock": seller_stats["total_stock"],
                "sales_count": sales_count,
            }
        )
        return context


def legacy_category_redirect(request):
    category = Category.objects.filter(is_active=True).order_by("name").first()
    return redirect("apps:category", slug=category.slug) if category else redirect("apps:catalog")


def legacy_product_redirect(request):
    product = Product.objects.filter(is_active=True).order_by("-created_at").first()
    return redirect("apps:product", slug=product.slug) if product else redirect("apps:catalog")


def legacy_seller_redirect(request):
    seller = Seller.objects.filter(is_active=True).order_by("store_name").first()
    if not seller:
        return redirect("apps:catalog")
    return redirect("apps:seller", pk=seller.pk)


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

        products = card_products(in_stock=False)
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
            category = Category.objects.filter(slug=category_slug, is_active=True).first()
            products = products.filter(
                category_id__in=category_descendant_ids(category)
            ) if category else products.none()

        brands = Brand.objects.filter(
            is_active=True,
            products__in=products,
        ).distinct().order_by("name")
        products, filter_state = filter_and_sort_products(products, self.request.GET)

        title = f"“{query}” bo‘yicha natijalar" if query else "Mahsulotlar"
        if category_slug and not query:
            category = Category.objects.filter(slug=category_slug).first()
            title = category.name if category else title
        if filter_state["brand"] and not query:
            brand = Brand.objects.filter(slug=filter_state["brand"]).first()
            title = brand.name if brand else title
        if filter_state["discount"] and not query:
            title = "Chegirmali mahsulotlar"

        reset_params = self.request.GET.copy()
        for name in ("brand", "min_price", "max_price", "discount", "rating", "availability", "sort", "page"):
            reset_params.pop(name, None)
        reset_query = reset_params.urlencode()

        context.update(paginated_product_context(self.request, products))
        context.update({
                "page_title": f"{title} — Zento",
                "search_title": title,
                "query": query,
                "result_count": context["product_count"],
                "brands": brands,
                "filter_state": filter_state,
                "reset_url": f"{self.request.path}?{reset_query}" if reset_query else self.request.path,
            })
        return context


class SearchSuggestionsView(View):
    max_results = 6

    def get(self, request):
        query = request.GET.get("q", "").strip()
        if len(query) < 2:
            return JsonResponse({"results": []})

        products = (
            card_products()
            .filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(sku__icontains=query)
                | Q(brand__name__icontains=query)
                | Q(category__name__icontains=query)
                | Q(seller__store_name__icontains=query)
            )
            .annotate(
                search_priority=Case(
                    When(name__istartswith=query, then=Value(0)),
                    When(name__icontains=query, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            )
            .order_by("search_priority", "-average_rating", "name")[: self.max_results]
        )

        results = []
        for product in products:
            image = (
                product.card_images[0].image
                if product.card_images
                else product.category.image
            )
            results.append(
                {
                    "name": product.name,
                    "url": reverse("apps:product", kwargs={"slug": product.slug}),
                    "image_url": image.url if image else "",
                    "price": str(product.price),
                    "category": product.category.name,
                }
            )

        return JsonResponse({"results": results})


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
