from .models import Product


COMPARE_SESSION_KEY = "compare_product_ids"
COMPARE_LIMIT = 4


class CompareValidationError(Exception):
    def __init__(self, message, code):
        super().__init__(message)
        self.message = message
        self.code = code


def save_compare_ids(request, product_ids):
    request.session[COMPARE_SESSION_KEY] = product_ids
    request.session.modified = True


def get_compare_ids(request):
    raw_ids = request.session.get(COMPARE_SESSION_KEY, [])
    if not isinstance(raw_ids, list):
        raw_ids = []

    candidate_ids = []
    for raw_id in raw_ids:
        try:
            product_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if product_id not in candidate_ids:
            candidate_ids.append(product_id)

    available_products = dict(
        Product.objects.filter(pk__in=candidate_ids, is_active=True).values_list(
            "pk", "category_id"
        )
    )
    product_ids = []
    category_id = None
    for product_id in candidate_ids:
        product_category_id = available_products.get(product_id)
        if product_category_id is None:
            continue
        if category_id is None:
            category_id = product_category_id
        if product_category_id == category_id and len(product_ids) < COMPARE_LIMIT:
            product_ids.append(product_id)

    if product_ids != raw_ids:
        save_compare_ids(request, product_ids)
    return product_ids


def add_to_compare(request, product):
    product_ids = get_compare_ids(request)
    if product.pk in product_ids:
        return product_ids, False

    if product_ids:
        category_id = Product.objects.values_list("category_id", flat=True).get(
            pk=product_ids[0]
        )
        if product.category_id != category_id:
            raise CompareValidationError(
                "Faqat bitta kategoriyadagi mahsulotlarni taqqoslash mumkin.",
                "category_mismatch",
            )
    if len(product_ids) >= COMPARE_LIMIT:
        raise CompareValidationError(
            f"Taqqoslashga ko‘pi bilan {COMPARE_LIMIT} ta mahsulot qo‘shish mumkin.",
            "limit_reached",
        )

    product_ids.append(product.pk)
    save_compare_ids(request, product_ids)
    return product_ids, True


def remove_from_compare(request, product_id):
    product_ids = get_compare_ids(request)
    changed = product_id in product_ids
    if changed:
        product_ids.remove(product_id)
        save_compare_ids(request, product_ids)
    return product_ids, changed


def clear_compare(request):
    changed = bool(get_compare_ids(request))
    save_compare_ids(request, [])
    return changed
