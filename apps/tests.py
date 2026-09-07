from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils.text import slugify

from .models import Brand, Category, Order, OrderItem, Product, Review, Seller, User


class AuthenticationFlowTests(TestCase):
    password = "StrongPass2026!"

    def setUp(self):
        self.user = User.objects.create_user(
            email="aziza@example.com",
            username="aziza",
            password=self.password,
            first_name="Aziza",
            last_name="Karimova",
            phone="+998901234567",
        )

    def test_main_page_is_public(self):
        response = self.client.get(reverse("apps:index"))
        self.assertEqual(response.status_code, 200)

    def test_checkout_redirects_anonymous_user_to_login(self):
        response = self.client.get(reverse("apps:checkout"))
        expected = f"{reverse('apps:login')}?next={reverse('apps:checkout')}"
        self.assertRedirects(response, expected)

    def test_login_uses_email_and_redirects_to_next(self):
        response = self.client.post(
            reverse("apps:login"),
            {"username": self.user.email.upper(), "password": self.password, "next": reverse("apps:checkout")},
        )
        self.assertRedirects(response, reverse("apps:checkout"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_authenticated_user_is_redirected_away_from_login(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("apps:login"))
        self.assertRedirects(response, reverse("apps:index"))

    def test_authenticated_user_is_redirected_away_from_registration(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("apps:signup"))
        self.assertRedirects(response, reverse("apps:index"))

    def test_registration_creates_customer_and_logs_in(self):
        response = self.client.post(reverse("apps:signup"), {
            "first_name": "Dilnoza",
            "last_name": "Rahimova",
            "email": "DILNOZA@example.com",
            "phone": "+998 91 234 56 78",
            "password1": self.password,
            "password2": self.password,
        })
        new_user = User.objects.get(email="dilnoza@example.com")
        self.assertRedirects(response, reverse("apps:index"))
        self.assertTrue(new_user.check_password(self.password))
        self.assertEqual(new_user.role, User.Role.CUSTOMER)
        self.assertEqual(new_user.phone, "+998912345678")
        self.assertEqual(int(self.client.session["_auth_user_id"]), new_user.pk)

    def test_registration_rejects_duplicate_email(self):
        response = self.client.post(reverse("apps:signup"), {
            "first_name": "Aziza",
            "last_name": "Karimova",
            "email": "AZIZA@example.com",
            "phone": "+998 90 765 43 21",
            "password1": self.password,
            "password2": self.password,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bu email bilan hisob allaqachon mavjud.")
        self.assertEqual(User.objects.filter(email__iexact="aziza@example.com").count(), 1)

    def test_registration_from_checkout_returns_to_checkout(self):
        response = self.client.post(reverse("apps:signup"), {
            "first_name": "Madina",
            "last_name": "Aliyeva",
            "email": "madina@example.com",
            "phone": "+998 93 111 22 33",
            "password1": self.password,
            "password2": self.password,
            "next": reverse("apps:checkout"),
        })
        self.assertRedirects(response, reverse("apps:checkout"))

    def test_authenticated_user_can_open_checkout(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("apps:checkout"))
        self.assertEqual(response.status_code, 200)

    def test_logout_accepts_post_and_returns_to_main_page(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("apps:logout"))
        self.assertRedirects(response, reverse("apps:index"))
        self.assertNotIn("_auth_user_id", self.client.session)


class StorefrontTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user(
            email="customer@example.com",
            username="customer",
            password="StrongPass2026!",
        )
        seller_user = User.objects.create_user(
            email="seller@example.com",
            username="seller",
            password="StrongPass2026!",
            role=User.Role.SELLER,
        )
        cls.seller = Seller.objects.create(user=seller_user, store_name="Tech Store")
        cls.electronics = Category.objects.create(name="Elektronika", slug="elektronika")
        cls.phones = Category.objects.create(
            name="Smartfonlar", slug="smartfonlar", parent=cls.electronics
        )
        audio = Category.objects.create(name="Audio", slug="audio", parent=cls.electronics)
        samsung = Brand.objects.create(name="Samsung", slug="samsung")
        sony = Brand.objects.create(name="Sony", slug="sony")
        cls.discount_product = Product.objects.create(
            seller=cls.seller,
            category=cls.phones,
            brand=samsung,
            name="Samsung Galaxy Test",
            slug="samsung-galaxy-test",
            sku="TEST-SAMSUNG",
            description="5G smartfon",
            price=Decimal("800000"),
            old_price=Decimal("1000000"),
            stock=10,
        )
        cls.best_seller = Product.objects.create(
            seller=cls.seller,
            category=audio,
            brand=sony,
            name="Sony Headphones Test",
            slug="sony-headphones-test",
            sku="TEST-SONY",
            price=Decimal("1200000"),
            stock=10,
        )
        order = Order.objects.create(
            user=cls.customer,
            order_number="ZT-TEST-1",
            status=Order.Status.DELIVERED,
        )
        OrderItem.objects.create(
            order=order,
            product=cls.discount_product,
            seller=cls.seller,
            product_name=cls.discount_product.name,
            price=cls.discount_product.price,
            quantity=1,
        )
        OrderItem.objects.create(
            order=order,
            product=cls.best_seller,
            seller=cls.seller,
            product_name=cls.best_seller.name,
            price=cls.best_seller.price,
            quantity=5,
        )
        Review.objects.create(
            user=cls.customer,
            product=cls.discount_product,
            order=order,
            rating=5,
            text="A'lo mahsulot",
        )
        Review.objects.create(
            user=cls.customer,
            product=cls.best_seller,
            order=order,
            rating=3,
            text="Yaxshi",
        )

    def test_homepage_uses_dynamic_catalog_and_product_sections(self):
        response = self.client.get(reverse("apps:index"))

        self.assertContains(response, "Smartfonlar")
        self.assertContains(response, self.discount_product.name)
        self.assertEqual(response.context["best_sellers"][0], self.best_seller)
        self.assertEqual(response.context["popular_brands"][0].name, "Sony")

    def test_search_finds_products_by_name_case_insensitively(self):
        response = self.client.get(reverse("apps:search"), {"q": "galaxy"})

        self.assertContains(response, self.discount_product.name)
        self.assertNotContains(response, self.best_seller.name)
        self.assertEqual(response.context["result_count"], 1)

    def test_search_can_filter_by_category_brand_and_discount(self):
        category_response = self.client.get(reverse("apps:search"), {"category": "audio"})
        brand_response = self.client.get(reverse("apps:search"), {"brand": "samsung"})
        discount_response = self.client.get(reverse("apps:search"), {"discount": "1"})

        self.assertContains(category_response, self.best_seller.name)
        self.assertContains(brand_response, self.discount_product.name)
        self.assertContains(discount_response, self.discount_product.name)
        self.assertNotContains(discount_response, self.best_seller.name)

    def test_catalog_lists_database_categories(self):
        response = self.client.get(reverse("apps:catalog"))

        self.assertContains(response, "Smartfonlar")
        self.assertContains(response, "Audio")

    def test_category_url_uses_slug_and_database_context(self):
        response = self.client.get(
            reverse("apps:category", kwargs={"slug": self.phones.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["category"], self.phones)
        self.assertEqual(response.context["parent_category"], self.electronics)
        self.assertEqual(
            [item.slug for item in response.context["breadcrumbs"]],
            ["elektronika", "smartfonlar"],
        )
        self.assertEqual(response.context["product_count"], 1)
        self.assertContains(response, self.discount_product.name)

    def test_parent_category_includes_descendant_products_and_children(self):
        response = self.client.get(
            reverse("apps:category", kwargs={"slug": self.electronics.slug})
        )

        self.assertEqual(response.context["product_count"], 2)
        self.assertContains(response, "Smartfonlar")
        self.assertContains(response, "Audio")
        self.assertContains(response, self.discount_product.name)
        self.assertContains(response, self.best_seller.name)

    def test_inactive_and_out_of_stock_products_are_excluded_from_category(self):
        Product.objects.create(
            seller=self.seller,
            category=self.phones,
            name="Inactive phone",
            slug="inactive-phone",
            sku="INACTIVE-PHONE",
            price=Decimal("100000"),
            stock=5,
            is_active=False,
        )
        Product.objects.create(
            seller=self.seller,
            category=self.phones,
            name="Out of stock phone",
            slug="out-of-stock-phone",
            sku="OUT-OF-STOCK-PHONE",
            price=Decimal("100000"),
            stock=0,
        )

        response = self.client.get(
            reverse("apps:category", kwargs={"slug": self.phones.slug})
        )

        self.assertEqual(response.context["product_count"], 1)
        self.assertNotContains(response, "Inactive phone")
        self.assertNotContains(response, "Out of stock phone")

    def test_product_and_seller_have_precise_dynamic_urls(self):
        product_response = self.client.get(
            reverse("apps:product", kwargs={"slug": self.discount_product.slug})
        )
        seller_response = self.client.get(
            reverse("apps:seller", kwargs={"pk": self.seller.pk})
        )

        self.assertEqual(product_response.status_code, 200)
        self.assertContains(product_response, self.discount_product.name)
        self.assertContains(product_response, self.seller.store_name)
        self.assertEqual(seller_response.status_code, 200)
        self.assertContains(seller_response, self.discount_product.name)

    def test_unknown_or_inactive_detail_objects_return_404(self):
        self.seller.is_active = False
        self.seller.save(update_fields=("is_active",))

        self.assertEqual(self.client.get("/category/unknown/").status_code, 404)
        self.assertEqual(self.client.get("/product/unknown/").status_code, 404)
        self.assertEqual(
            self.client.get(reverse("apps:seller", kwargs={"pk": self.seller.pk})).status_code,
            404,
        )

    def test_legacy_demo_urls_redirect_to_precise_urls(self):
        self.assertRedirects(
            self.client.get(reverse("apps:category-legacy")),
            reverse("apps:category", kwargs={"slug": "audio"}),
        )
        self.assertRedirects(
            self.client.get(reverse("apps:product-legacy")),
            reverse("apps:product", kwargs={"slug": self.best_seller.slug}),
        )
        self.assertRedirects(
            self.client.get(reverse("apps:seller-legacy")),
            reverse("apps:seller", kwargs={"pk": self.seller.pk}),
        )

    def test_category_filters_by_brand_price_discount_and_rating(self):
        response = self.client.get(
            reverse("apps:category", kwargs={"slug": self.electronics.slug}),
            {
                "brand": "samsung",
                "min_price": "700000",
                "max_price": "900000",
                "discount": "1",
                "rating": "4",
            },
        )

        self.assertEqual(response.context["product_count"], 1)
        self.assertContains(response, self.discount_product.name)
        self.assertNotContains(response, self.best_seller.name)
        self.assertEqual(response.context["filter_state"]["brand"], "samsung")
        self.assertEqual(response.context["filter_state"]["rating"], 4)

    def test_availability_filter_can_show_out_of_stock_products(self):
        unavailable = Product.objects.create(
            seller=self.seller,
            category=self.phones,
            name="Unavailable Galaxy",
            slug="unavailable-galaxy",
            sku="UNAVAILABLE-GALAXY",
            price=Decimal("500000"),
            stock=0,
        )

        default_response = self.client.get(reverse("apps:search"), {"q": "Galaxy"})
        unavailable_response = self.client.get(
            reverse("apps:search"),
            {"q": "Galaxy", "availability": "out_of_stock"},
        )

        self.assertNotContains(default_response, unavailable.name)
        self.assertContains(unavailable_response, unavailable.name)
        self.assertNotContains(unavailable_response, self.discount_product.name)

    def test_sorting_supports_popular_price_rating_and_newest(self):
        url = reverse("apps:category", kwargs={"slug": self.electronics.slug})

        popular = self.client.get(url, {"sort": "popular"})
        cheapest = self.client.get(url, {"sort": "price_asc"})
        expensive = self.client.get(url, {"sort": "price_desc"})
        rating = self.client.get(url, {"sort": "rating"})
        newest = self.client.get(url, {"sort": "newest"})

        self.assertEqual(popular.context["products"][0], self.best_seller)
        self.assertEqual(cheapest.context["products"][0], self.discount_product)
        self.assertEqual(expensive.context["products"][0], self.best_seller)
        self.assertEqual(rating.context["products"][0], self.discount_product)
        self.assertEqual(newest.context["products"][0], self.best_seller)

    def test_category_and_search_pagination_preserve_filter_query(self):
        Product.objects.bulk_create([
            Product(
                seller=self.seller,
                category=self.phones,
                name=f"Page item {index:02d}",
                slug=f"page-item-{index:02d}",
                sku=f"PAGE-ITEM-{index:02d}",
                price=Decimal("750000") + index,
                stock=5,
            )
            for index in range(13)
        ])
        category_url = reverse("apps:category", kwargs={"slug": self.phones.slug})
        category_response = self.client.get(
            category_url,
            {"min_price": "700000", "sort": "price_asc", "page": "2"},
        )
        search_response = self.client.get(
            reverse("apps:search"),
            {"q": "Page item", "availability": "all", "sort": "newest", "page": "2"},
        )

        self.assertEqual(category_response.context["page_obj"].number, 2)
        self.assertIn("min_price=700000", category_response.context["filter_query"])
        self.assertIn("sort=price_asc", category_response.context["filter_query"])
        self.assertNotIn("page=", category_response.context["filter_query"])
        self.assertEqual(search_response.context["page_obj"].number, 2)
        self.assertIn("q=Page+item", search_response.context["filter_query"])
        self.assertIn("availability=all", search_response.context["filter_query"])

    def test_out_of_stock_product_is_accessible_and_marked_unavailable(self):
        product = Product.objects.create(
            seller=self.seller,
            category=self.phones,
            name="Out of stock vision",
            slug="out-of-stock-vision",
            sku="OUT-OF-STOCK-VISION",
            price=Decimal("740000"),
            stock=0,
        )

        response = self.client.get(reverse("apps:product", kwargs={"slug": product.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_out_of_stock"])
        self.assertEqual(response.context["display_stock"], 0)

    def test_seller_slug_route_uses_store_slug_when_available(self):
        slug = slugify(self.seller.store_name)
        response = self.client.get(reverse("apps:seller_slug", kwargs={"pk_or_slug": slug}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["seller"], self.seller)
