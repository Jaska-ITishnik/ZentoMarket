from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse
from django.utils.text import slugify

from .models import Brand, Category, Order, OrderItem, Product, Review, Seller, User, Wishlist


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

    def test_search_suggestions_return_matching_product_data(self):
        response = self.client.get(
            reverse("apps:search-suggestions"), {"q": "samsung"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["results"],
            [
                {
                    "name": self.discount_product.name,
                    "url": reverse(
                        "apps:product", kwargs={"slug": self.discount_product.slug}
                    ),
                    "image_url": "",
                    "price": f"{self.discount_product.price:.2f}",
                    "category": self.phones.name,
                }
            ],
        )

    def test_search_suggestions_require_two_characters_and_exclude_inactive_products(self):
        self.discount_product.is_active = False
        self.discount_product.save(update_fields=("is_active",))

        short_query = self.client.get(
            reverse("apps:search-suggestions"), {"q": "s"}
        )
        inactive_query = self.client.get(
            reverse("apps:search-suggestions"), {"q": "samsung"}
        )

        self.assertEqual(short_query.json(), {"results": []})
        self.assertEqual(inactive_query.json(), {"results": []})

    def test_header_search_exposes_ajax_suggestions_endpoint(self):
        response = self.client.get(reverse("apps:index"))

        self.assertContains(response, "data-search-form")
        self.assertContains(
            response,
            f'data-suggestions-url="{reverse("apps:search-suggestions")}"',
        )

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

    def test_wishlist_pages_and_toggle_require_login(self):
        wishlist_url = reverse("apps:wishlist")
        toggle_url = reverse(
            "apps:wishlist-toggle", kwargs={"product_id": self.discount_product.pk}
        )

        self.assertRedirects(
            self.client.get(wishlist_url),
            f"{reverse('apps:login')}?next={wishlist_url}",
        )
        self.assertRedirects(
            self.client.post(toggle_url),
            f"{reverse('apps:login')}?next={toggle_url}",
        )

    def test_wishlist_toggle_adds_then_removes_product(self):
        self.client.force_login(self.customer)
        url = reverse(
            "apps:wishlist-toggle", kwargs={"product_id": self.discount_product.pk}
        )

        added = self.client.post(url)
        self.assertEqual(added.status_code, 200)
        self.assertEqual(
            added.json(),
            {
                "is_wishlisted": True,
                "wishlist_count": 1,
                "message": "Sevimlilarga qo‘shildi",
            },
        )
        self.assertTrue(
            Wishlist.objects.filter(
                user=self.customer, product=self.discount_product
            ).exists()
        )

        removed = self.client.post(url)
        self.assertEqual(removed.status_code, 200)
        self.assertFalse(removed.json()["is_wishlisted"])
        self.assertEqual(removed.json()["wishlist_count"], 0)
        self.assertFalse(Wishlist.objects.filter(user=self.customer).exists())

    def test_wishlist_toggle_only_accepts_post_and_checks_csrf(self):
        url = reverse(
            "apps:wishlist-toggle", kwargs={"product_id": self.discount_product.pk}
        )
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.customer)

        self.assertEqual(csrf_client.get(url).status_code, 405)
        self.assertEqual(csrf_client.post(url).status_code, 403)

        csrf_client.get(reverse("apps:product", kwargs={"slug": self.discount_product.slug}))
        csrf_token = csrf_client.cookies["csrftoken"].value
        response = csrf_client.post(url, HTTP_X_CSRFTOKEN=csrf_token)
        self.assertEqual(response.status_code, 200)

    def test_wishlist_page_is_dynamic_and_renders_empty_state(self):
        self.client.force_login(self.customer)
        empty_response = self.client.get(reverse("apps:wishlist"))

        self.assertContains(empty_response, "Sevimlilar ro‘yxati bo‘sh")
        self.assertNotContains(empty_response, self.discount_product.name)

        Wishlist.objects.create(user=self.customer, product=self.discount_product)
        populated_response = self.client.get(reverse("apps:wishlist"))
        self.assertEqual(populated_response.context["product_count"], 1)
        self.assertContains(populated_response, self.discount_product.name)
        self.assertContains(populated_response, "1 ta mahsulot")

    def test_database_wishlist_state_is_rendered_on_cards_detail_and_header(self):
        Wishlist.objects.create(user=self.customer, product=self.discount_product)
        self.client.force_login(self.customer)

        home_response = self.client.get(reverse("apps:index"))
        detail_response = self.client.get(
            reverse("apps:product", kwargs={"slug": self.discount_product.slug})
        )

        self.assertContains(home_response, 'data-wishlist-count>1</b>')
        self.assertContains(
            home_response,
            f'data-wishlist-product="{self.discount_product.pk}"',
        )
        self.assertContains(detail_response, 'aria-pressed="true"')
        self.assertContains(detail_response, "Sevimlilardan olib tashlash")

    def test_compare_is_session_backed_and_renders_dynamic_products(self):
        add_url = reverse("apps:compare-add", kwargs={"product_id": self.discount_product.pk})
        self.assertEqual(self.client.post(add_url).status_code, 200)

        response = self.client.get(reverse("apps:compare"))
        self.assertEqual(response.context["product_count"], 1)
        self.assertContains(response, self.discount_product.name)
        self.assertContains(response, self.discount_product.sku)
        self.assertContains(response, "Brend")

        refreshed_client = Client()
        session = self.client.session
        refreshed_client.cookies["sessionid"] = session.session_key
        refreshed_response = refreshed_client.get(reverse("apps:compare"))
        self.assertContains(refreshed_response, self.discount_product.name)

    def test_compare_rejects_duplicate_different_category_and_more_than_four(self):
        same_category = [
            Product.objects.create(
                seller=self.seller,
                category=self.phones,
                name=f"Compare phone {index}",
                slug=f"compare-phone-{index}",
                sku=f"COMPARE-PHONE-{index}",
                price=Decimal("500000") + index,
                stock=5,
            )
            for index in range(1, 6)
        ]
        add = lambda product: self.client.post(
            reverse("apps:compare-add", kwargs={"product_id": product.pk})
        )

        first = add(self.discount_product)
        duplicate = add(self.discount_product)
        self.assertTrue(first.json()["is_compared"])
        self.assertFalse(duplicate.json()["changed"])
        for product in same_category[:3]:
            self.assertEqual(add(product).status_code, 200)

        limited = add(same_category[3])
        self.assertEqual(limited.status_code, 400)
        self.assertEqual(limited.json()["code"], "limit_reached")
        mismatch = add(self.best_seller)
        self.assertEqual(mismatch.status_code, 400)
        self.assertEqual(mismatch.json()["code"], "category_mismatch")

    def test_compare_remove_clear_and_empty_state(self):
        add_url = reverse("apps:compare-add", kwargs={"product_id": self.discount_product.pk})
        remove_url = reverse("apps:compare-remove", kwargs={"product_id": self.discount_product.pk})
        clear_url = reverse("apps:compare-clear")

        self.assertEqual(self.client.get(add_url).status_code, 405)
        self.client.post(add_url)
        self.assertEqual(self.client.post(remove_url).json()["compare_count"], 0)
        self.assertFalse(self.client.get(reverse("apps:compare")).context["products"])
        self.client.post(add_url)
        self.assertEqual(self.client.post(clear_url).json()["compare_count"], 0)
        self.assertContains(self.client.get(reverse("apps:compare")), "Taqqoslash ro‘yxati bo‘sh")

    def test_compare_mutations_require_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        add_url = reverse("apps:compare-add", kwargs={"product_id": self.discount_product.pk})
        self.assertEqual(csrf_client.post(add_url).status_code, 403)
