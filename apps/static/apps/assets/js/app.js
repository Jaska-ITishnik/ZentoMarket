const $ = (s, c = document) => c.querySelector(s), $$ = (s, c = document) => [...c.querySelectorAll(s)];

const formatMoney = (value) => {
    const number = Number(value || 0);
    return `${number.toLocaleString('uz-UZ', { maximumFractionDigits: 0 })} so‘m`;
};

const updateVariantSelection = (button) => {
    const detail = button.closest('[data-product-detail]');
    if (!detail) return;
    const priceEl = detail.querySelector('[data-product-price]');
    const installmentEl = detail.querySelector('[data-installment-price]');
    const stockEl = detail.querySelector('[data-product-stock]');
    const hiddenInput = detail.querySelector('[data-selected-variant]');
    const actionButtons = $$('[data-purchase-action]', detail);

    const price = button.dataset.price;
    const installment = button.dataset.installment;
    const stock = Number(button.dataset.stock || 0);
    const variantId = button.dataset.variantId;

    if (priceEl) priceEl.textContent = formatMoney(price);
    if (installmentEl) installmentEl.textContent = `${formatMoney(installment).replace(' so‘m', '')} so‘mdan × 12 oy`;
    if (stockEl) stockEl.textContent = stock > 0 ? `${stock} dona` : 'sotuvda yo‘q';
    if (hiddenInput) hiddenInput.value = variantId || '';

    actionButtons.forEach((node) => {
        if (stock > 0) {
            node.disabled = false;
            node.setAttribute('aria-disabled', 'false');
            node.classList.remove('is-disabled');
        } else {
            node.disabled = true;
            node.setAttribute('aria-disabled', 'true');
            node.classList.add('is-disabled');
        }
    });

    $$('[data-product-variant]', detail).forEach((item) => {
        const isActive = item === button;
        item.classList.toggle('active', isActive);
        item.setAttribute('aria-pressed', String(isActive));
    });
};

$$('[data-gallery-thumb]').forEach((button) => {
    button.addEventListener('click', () => {
        const mainImage = document.querySelector('[data-gallery-main]');
        if (!mainImage) return;
        mainImage.src = button.dataset.imageSrc || mainImage.src;
        $$('[data-gallery-thumb]').forEach((item) => item.classList.toggle('active', item === button));
    });
});

$$('[data-product-variant]').forEach((button) => {
    button.addEventListener('click', () => updateVariantSelection(button));
});

const searchForm = $('[data-search-form]');
if (searchForm) {
    const input = $('input[name="q"]', searchForm);
    const suggestions = $('[data-search-suggestions]', searchForm);
    let debounceTimer;
    let requestController;
    let activeIndex = -1;

    const setSuggestionsOpen = (isOpen) => {
        suggestions.hidden = !isOpen;
        input.setAttribute('aria-expanded', String(isOpen));
        if (!isOpen) activeIndex = -1;
    };

    const showSuggestionStatus = (message) => {
        suggestions.replaceChildren();
        const status = document.createElement('div');
        status.className = 'search-suggestion-status';
        status.textContent = message;
        suggestions.append(status);
        setSuggestionsOpen(true);
    };

    const renderSuggestions = (items, query) => {
        suggestions.replaceChildren();
        activeIndex = -1;

        if (!items.length) {
            const empty = document.createElement('div');
            empty.className = 'search-suggestion-status';
            empty.textContent = 'Mos mahsulot topilmadi';
            suggestions.append(empty);
        }

        items.forEach((item) => {
            const link = document.createElement('a');
            link.className = 'search-suggestion';
            link.href = item.url;
            link.setAttribute('role', 'option');

            if (item.image_url) {
                const image = document.createElement('img');
                image.src = item.image_url;
                image.alt = '';
                link.append(image);
            } else {
                const placeholder = document.createElement('span');
                placeholder.className = 'search-suggestion-placeholder';
                placeholder.textContent = '▧';
                link.append(placeholder);
            }

            const copy = document.createElement('span');
            copy.className = 'search-suggestion-copy';
            const name = document.createElement('b');
            name.textContent = item.name;
            const category = document.createElement('small');
            category.textContent = item.category;
            copy.append(name, category);

            const price = document.createElement('strong');
            price.className = 'search-suggestion-price';
            price.textContent = formatMoney(item.price);
            link.append(copy, price);
            suggestions.append(link);
        });

        const allResults = document.createElement('a');
        const searchUrl = new URL(searchForm.action, window.location.origin);
        searchUrl.searchParams.set('q', query);
        allResults.className = 'search-suggestion-all';
        allResults.href = searchUrl.toString();
        allResults.textContent = 'Barcha natijalarni ko‘rish →';
        suggestions.append(allResults);
        setSuggestionsOpen(true);
    };

    const loadSuggestions = async () => {
        const query = input.value.trim();
        if (query.length < 2) {
            requestController?.abort();
            setSuggestionsOpen(false);
            suggestions.replaceChildren();
            return;
        }

        requestController?.abort();
        requestController = new AbortController();
        showSuggestionStatus('Qidirilmoqda…');

        try {
            const url = new URL(searchForm.dataset.suggestionsUrl, window.location.origin);
            url.searchParams.set('q', query);
            const response = await fetch(url, {
                credentials: 'same-origin',
                headers: {'X-Requested-With': 'XMLHttpRequest'},
                signal: requestController.signal,
            });
            if (!response.ok) throw new Error('Qidiruv takliflarini yuklab bo‘lmadi');
            const data = await response.json();
            if (input.value.trim() === query) renderSuggestions(data.results || [], query);
        } catch (error) {
            if (error.name !== 'AbortError') showSuggestionStatus(error.message);
        }
    };

    input.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(loadSuggestions, 250);
    });

    input.addEventListener('focus', () => {
        if (input.value.trim().length >= 2 && suggestions.childElementCount) {
            setSuggestionsOpen(true);
        }
    });

    input.addEventListener('keydown', (event) => {
        const options = $$('.search-suggestion', suggestions);
        if (event.key === 'Escape') {
            setSuggestionsOpen(false);
            return;
        }
        if (!options.length || !['ArrowDown', 'ArrowUp', 'Enter'].includes(event.key)) return;
        if (event.key === 'Enter' && activeIndex < 0) return;

        event.preventDefault();
        if (event.key === 'Enter') {
            options[activeIndex].click();
            return;
        }
        activeIndex = event.key === 'ArrowDown'
            ? (activeIndex + 1) % options.length
            : (activeIndex - 1 + options.length) % options.length;
        options.forEach((option, index) => {
            option.classList.toggle('is-active', index === activeIndex);
            option.setAttribute('aria-selected', String(index === activeIndex));
        });
        options[activeIndex].scrollIntoView({block: 'nearest'});
    });

    document.addEventListener('click', (event) => {
        if (!searchForm.contains(event.target)) setSuggestionsOpen(false);
    });
}

const updateWishlistButtons = (productId, isWishlisted) => {
    $$('[data-wishlist-product]').forEach((button) => {
        if (button.dataset.wishlistProduct !== String(productId)) return;
        button.textContent = isWishlisted ? '♥' : '♡';
        button.classList.toggle('is-active', isWishlisted);
        button.setAttribute('aria-pressed', String(isWishlisted));
        button.setAttribute(
            'aria-label',
            isWishlisted ? 'Sevimlilardan olib tashlash' : 'Sevimlilarga qo‘shish',
        );
    });
};

const updateWishlistPage = (productId, isWishlisted, count) => {
    const page = $('[data-wishlist-page]');
    if (!page || isWishlisted) return;

    $$('[data-product-card]', page).forEach((card) => {
        if (card.dataset.productCard === String(productId)) card.remove();
    });

    const toolbar = $('[data-wishlist-toolbar]', page);
    const countLabel = $('[data-wishlist-page-count]', page);
    const emptyState = $('[data-wishlist-empty]', page);
    if (countLabel) countLabel.textContent = `${count} ta mahsulot`;
    if (toolbar) toolbar.hidden = count === 0;
    if (emptyState) emptyState.hidden = count !== 0;
};

const toggleWishlist = async (button) => {
    const loginUrl = document.body.dataset.loginUrl || '/login/';
    if (document.body.dataset.authenticated !== 'true') {
        const next = `${window.location.pathname}${window.location.search}`;
        window.location.assign(`${loginUrl}?next=${encodeURIComponent(next)}`);
        return;
    }

    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    try {
        const csrfToken = $('meta[name="csrf-token"]')?.content;
        const response = await fetch(button.dataset.wishlistUrl, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-CSRFToken': csrfToken || '',
                'X-Requested-With': 'XMLHttpRequest',
            },
        });

        if (response.redirected) {
            window.location.assign(response.url);
            return;
        }

        const contentType = response.headers.get('content-type') || '';
        const data = contentType.includes('application/json') ? await response.json() : {};
        if (!response.ok) {
            if (response.status === 401 && data.login_url) {
                window.location.assign(data.login_url);
                return;
            }
            throw new Error(data.error || (response.status === 403
                ? 'Xavfsizlik tekshiruvi bajarilmadi. Sahifani yangilang.'
                : 'Sevimlilarni yangilab bo‘lmadi.'));
        }

        updateWishlistButtons(button.dataset.wishlistProduct, data.is_wishlisted);
        $$('[data-wishlist-count]').forEach((counter) => {
            counter.textContent = data.wishlist_count;
        });
        updateWishlistPage(button.dataset.wishlistProduct, data.is_wishlisted, data.wishlist_count);
        toast(data.message);
    } catch (error) {
        toast(error.message || 'Tarmoq xatosi yuz berdi. Qayta urinib ko‘ring.');
    } finally {
        button.disabled = false;
        button.removeAttribute('aria-busy');
    }
};

$$('[data-wishlist-product]').forEach((button) => {
    button.addEventListener('click', () => toggleWishlist(button));
});

const updateCompareButtons = (productId, isCompared) => {
    $$('[data-compare-product]').forEach((button) => {
        if (button.dataset.compareProduct !== String(productId)) return;
        button.dataset.compared = String(isCompared);
        button.dataset.compareUrl = isCompared
            ? button.dataset.compareRemoveUrl
            : button.dataset.compareAddUrl;
        button.textContent = isCompared ? '✓' : '⇄';
        button.classList.toggle('is-active', isCompared);
        button.setAttribute('aria-pressed', String(isCompared));
        button.setAttribute(
            'aria-label',
            isCompared ? 'Taqqoslashdan olib tashlash' : 'Taqqoslashga qo‘shish',
        );
    });
};

const updateCompareCount = (count) => {
    $$('[data-compare-count]').forEach((counter) => {
        counter.textContent = count;
    });
};

const postCompare = async (url, button, successMessage) => {
    button.disabled = true;
    try {
        const response = await fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-CSRFToken': $('meta[name="csrf-token"]')?.content || '',
                'X-Requested-With': 'XMLHttpRequest',
            },
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Taqqoslashni yangilab bo‘lmadi.');
        updateCompareCount(data.compare_count);
        toast(data.message || successMessage);
        return data;
    } finally {
        button.disabled = false;
    }
};

$$('[data-compare-product]').forEach((button) => {
    button.addEventListener('click', async () => {
        const isCompared = button.dataset.compared === 'true';
        const url = isCompared ? button.dataset.compareRemoveUrl : button.dataset.compareAddUrl;
        try {
            const data = await postCompare(url, button, 'Taqqoslash yangilandi');
            updateCompareButtons(button.dataset.compareProduct, data.is_compared);
        } catch (error) {
            toast(error.message || 'Tarmoq xatosi yuz berdi. Qayta urinib ko‘ring.');
        }
    });
});

$$('[data-compare-page-remove]').forEach((button) => {
    button.addEventListener('click', async () => {
        try {
            await postCompare(button.dataset.compareRemoveUrl, button, 'Taqqoslashdan olib tashlandi');
            window.location.reload();
        } catch (error) {
            toast(error.message || 'Tarmoq xatosi yuz berdi. Qayta urinib ko‘ring.');
        }
    });
});

const compareClearButton = $('[data-compare-clear-url]');
compareClearButton?.addEventListener('click', async () => {
    try {
        await postCompare(compareClearButton.dataset.compareClearUrl, compareClearButton, 'Taqqoslash tozalandi');
        window.location.reload();
    } catch (error) {
        toast(error.message || 'Tarmoq xatosi yuz berdi. Qayta urinib ko‘ring.');
    }
});

const updateCartCount = (count) => {
    $$('[data-cart-count]').forEach((counter) => {
        counter.textContent = count;
    });
};

const postCart = async (url, body = {}) => {
    const formData = new URLSearchParams(body);
    const response = await fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'X-CSRFToken': $('meta[name="csrf-token"]')?.content || '',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData,
    });
    if (response.redirected) {
        window.location.assign(response.url);
        return {};
    }
    if (!(response.headers.get('content-type') || '').includes('application/json')) {
        throw new Error('Savatni yangilash uchun tizimga kiring.');
    }
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Savatni yangilab bo‘lmadi.');
    return data;
};

const queueCartActionForLogin = (url, body) => {
    sessionStorage.setItem('pending-cart-action', JSON.stringify({
        url,
        body,
        returnUrl: `${window.location.pathname}${window.location.search}`,
    }));
    const loginUrl = document.body.dataset.loginUrl || '/login/';
    const next = `${window.location.pathname}${window.location.search}`;
    window.location.assign(`${loginUrl}?next=${encodeURIComponent(next)}`);
};

const resumePendingCartAction = async () => {
    if (document.body.dataset.authenticated !== 'true') return;
    const rawAction = sessionStorage.getItem('pending-cart-action');
    if (!rawAction) return;
    let action;
    try {
        action = JSON.parse(rawAction);
    } catch {
        sessionStorage.removeItem('pending-cart-action');
        return;
    }
    const currentUrl = `${window.location.pathname}${window.location.search}`;
    if (!action.url || action.returnUrl !== currentUrl) return;

    sessionStorage.removeItem('pending-cart-action');
    try {
        const data = await postCart(action.url, action.body || {});
        updateCartCount(data.cart_count);
        toast(data.message || 'Savatga qo‘shildi');
    } catch (error) {
        toast(error.message || 'Savatni yangilab bo‘lmadi.');
    }
};

$$('[data-cart-url]').forEach((button) => {
    button.addEventListener('click', async () => {
        if (document.body.dataset.authenticated !== 'true') {
            const detail = button.closest('[data-product-detail]');
            const variant = detail?.querySelector('[data-selected-variant]')?.value;
            queueCartActionForLogin(button.dataset.cartUrl, variant ? {variant_id: variant} : {});
            return;
        }
        button.disabled = true;
        button.setAttribute('aria-busy', 'true');
        try {
            const detail = button.closest('[data-product-detail]');
            const variant = detail?.querySelector('[data-selected-variant]')?.value;
            const data = await postCart(button.dataset.cartUrl, variant ? {variant_id: variant} : {});
            updateCartCount(data.cart_count);
            toast(data.message);
        } catch (error) {
            toast(error.message || 'Savatni yangilab bo‘lmadi.');
        } finally {
            button.disabled = false;
            button.removeAttribute('aria-busy');
        }
    });
});

resumePendingCartAction();

const refreshCartPage = (data) => {
    updateCartCount(data.cart_count);
    $$('[data-cart-total]').forEach((node) => {
        node.textContent = formatMoney(data.total);
    });
};

$$('[data-cart-item]').forEach((item) => {
    const quantityEl = $('[data-cart-quantity]', item);
    $$('[data-step]', item).forEach((button) => {
        button.addEventListener('click', async () => {
            const current = Number(quantityEl.textContent);
            const quantity = Math.max(1, current + (button.dataset.step === 'up' ? 1 : -1));
            if (quantity === current) return;
            button.disabled = true;
            button.setAttribute('aria-busy', 'true');
            try {
                const data = await postCart(item.dataset.cartUpdateUrl, {quantity});
                quantityEl.textContent = data.quantity;
                $('[data-cart-subtotal]', item).textContent = formatMoney(data.subtotal);
                refreshCartPage(data);
            } catch (error) {
                toast(error.message || 'Miqdorni yangilab bo‘lmadi.');
            } finally {
                button.disabled = false;
                button.removeAttribute('aria-busy');
            }
        });
    });

    $('[data-cart-remove]', item)?.addEventListener('click', async () => {
        const removeButton = $('[data-cart-remove]', item);
        removeButton.disabled = true;
        removeButton.setAttribute('aria-busy', 'true');
        try {
            const data = await postCart(item.dataset.cartRemoveUrl);
            item.remove();
            refreshCartPage(data);
            if (!document.querySelector('[data-cart-item]')) window.location.reload();
            else toast(data.message);
        } catch (error) {
            toast(error.message || 'Mahsulotni o‘chirib bo‘lmadi.');
        } finally {
            removeButton.disabled = false;
            removeButton.removeAttribute('aria-busy');
        }
    });
});

const cartClearButton = $('[data-cart-clear-url]');
cartClearButton?.addEventListener('click', async () => {
    cartClearButton.disabled = true;
    cartClearButton.setAttribute('aria-busy', 'true');
    try {
        const data = await postCart(cartClearButton.dataset.cartClearUrl);
        updateCartCount(data.cart_count);
        window.location.reload();
    } catch (error) {
        toast(error.message || 'Savatni tozalab bo‘lmadi.');
    } finally {
        cartClearButton.disabled = false;
        cartClearButton.removeAttribute('aria-busy');
    }
});

const checkoutForm = $('[data-checkout-form]');
if (checkoutForm) {
    const deliveryPanels = $$('[data-delivery-panel]', checkoutForm);
    const addressPanels = $$('[data-address-panel]', checkoutForm);
    const deliveryFeeEl = $('[data-checkout-delivery-fee]', checkoutForm);
    const totalEl = $('[data-checkout-total]', checkoutForm);

    const syncCheckout = () => {
        const deliveryType = $('input[name="delivery_type"]:checked', checkoutForm)?.value || 'address';
        const addressMode = $('input[name="address_mode"]:checked', checkoutForm)?.value || 'new';
        const fee = Number(
            deliveryType === 'pickup'
                ? checkoutForm.dataset.pickupFee
                : checkoutForm.dataset.courierFee
        );
        const cartTotal = Number(totalEl?.dataset.cartTotalValue || 0);

        deliveryPanels.forEach((panel) => {
            panel.hidden = panel.dataset.deliveryPanel !== deliveryType;
        });
        addressPanels.forEach((panel) => {
            panel.hidden = panel.dataset.addressPanel !== addressMode;
        });
        $$('.choice-card', checkoutForm).forEach((card) => {
            card.classList.toggle('is-selected', Boolean($('input:checked', card)));
        });
        if (deliveryFeeEl) deliveryFeeEl.textContent = formatMoney(fee);
        if (totalEl) totalEl.textContent = formatMoney(cartTotal + fee);
    };

    $$('input[name="delivery_type"], input[name="address_mode"], input[name="payment_type"]', checkoutForm)
        .forEach((input) => input.addEventListener('change', syncCheckout));
    syncCheckout();
}

const pickupMapElement = $('#pickup-map');
if (pickupMapElement) {
    const pointElements = $$('[data-pickup-point]');
    const points = pointElements.map((element) => ({
        element,
        id: element.dataset.pickupPoint,
        name: element.dataset.name,
        address: element.dataset.address,
        latitude: Number(element.dataset.latitude),
        longitude: Number(element.dataset.longitude),
        selectUrl: element.dataset.selectUrl,
    })).filter((point) => Number.isFinite(point.latitude) && Number.isFinite(point.longitude)
        && point.latitude && point.longitude);

    const activatePoint = (pointId, scrollToCard = true) => {
        const point = $(`[data-pickup-point="${pointId}"]`);
        if (!point) return;
        $$('.point.is-active').forEach((item) => item.classList.remove('is-active'));
        point.classList.add('is-active');
        if (scrollToCard) point.scrollIntoView({behavior: 'smooth', block: 'nearest'});
    };

    const createPopupContent = (point) => {
        const popup = document.createElement('div');
        popup.className = 'pickup-popup';
        const name = document.createElement('b');
        name.textContent = point.name;
        const address = document.createElement('span');
        address.textContent = point.address;
        const select = document.createElement('a');
        select.className = 'btn btn-soft';
        select.href = point.selectUrl;
        select.textContent = 'Shu punktni tanlash';
        popup.append(name, address, select);
        return popup;
    };

    const initLeafletPickupMap = () => {
        if (!window.L) return;
        pickupMapElement.replaceChildren();
        const map = L.map(pickupMapElement, {
            scrollWheelZoom: false,
            maxBounds: [[36.5, 55.0], [46.5, 74.5]],
            maxBoundsViscosity: .7,
        }).setView([41.3775, 64.5853], 6);
        const markerGroup = L.featureGroup().addTo(map);
        const markers = new Map();

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            maxZoom: 19,
        }).addTo(map);

        points.forEach((point) => {
            const marker = L.marker([point.latitude, point.longitude])
                .addTo(markerGroup)
                .bindPopup(createPopupContent(point));
            markers.set(point.id, marker);
            marker.on('click', () => activatePoint(point.id));
        });

        if (points.length === 1) {
            map.setView([points[0].latitude, points[0].longitude], 14);
        } else if (points.length > 1) {
            map.fitBounds(markerGroup.getBounds(), {padding: [28, 28], maxZoom: 8});
        }

        $$('[data-show-pickup]').forEach((button) => {
            button.addEventListener('click', () => {
                const marker = markers.get(button.dataset.showPickup);
                if (!marker) return;
                activatePoint(button.dataset.showPickup, false);
                map.setView(marker.getLatLng(), 15, {animate: true});
                marker.openPopup();
            });
        });
    };

    const initYandexPickupMap = async () => {
        await window.ymaps3.ready;
        const {YMap, YMapDefaultSchemeLayer, YMapDefaultFeaturesLayer, YMapMarker} = window.ymaps3;
        const location = points.length === 1
            ? {center: [points[0].longitude, points[0].latitude], zoom: 14}
            : {bounds: [[55.9, 37.1], [73.2, 45.7]]};
        const map = new YMap(pickupMapElement, {
            location,
            margin: [28, 28, 28, 28],
            restrictMapArea: [[55.0, 36.5], [74.5, 46.5]],
            zoomRange: {min: 5, max: 18},
        });
        map.addChild(new YMapDefaultSchemeLayer({}));
        map.addChild(new YMapDefaultFeaturesLayer({zIndex: 1800}));
        const markerData = new Map();

        points.forEach((point, index) => {
            const markerElement = document.createElement('div');
            markerElement.className = 'yandex-pickup-marker';
            const dot = document.createElement('button');
            dot.className = 'yandex-pickup-dot';
            dot.type = 'button';
            dot.title = point.name;
            dot.setAttribute('aria-label', `${point.name} filialini tanlash`);
            const number = document.createElement('span');
            number.textContent = String(index + 1);
            dot.append(number);
            const card = createPopupContent(point);
            card.className = 'yandex-pickup-card';
            card.hidden = true;
            markerElement.append(dot, card);

            const marker = new YMapMarker({
                coordinates: [point.longitude, point.latitude],
                zIndex: 1801,
            }, markerElement);
            map.addChild(marker);
            markerData.set(point.id, {point, card});
            dot.addEventListener('click', () => {
                $$('.yandex-pickup-card').forEach((item) => { item.hidden = item !== card; });
                card.hidden = false;
                activatePoint(point.id);
                map.setLocation({center: [point.longitude, point.latitude], zoom: 15, duration: 400});
            });
        });

        $$('[data-show-pickup]').forEach((button) => {
            button.addEventListener('click', () => {
                const marker = markerData.get(button.dataset.showPickup);
                if (!marker) return;
                $$('.yandex-pickup-card').forEach((item) => { item.hidden = item !== marker.card; });
                marker.card.hidden = false;
                activatePoint(button.dataset.showPickup, false);
                map.setLocation({
                    center: [marker.point.longitude, marker.point.latitude],
                    zoom: 15,
                    duration: 400,
                });
            });
        });
    };

    if (pickupMapElement.dataset.mapProvider === 'yandex' && window.ymaps3) {
        initYandexPickupMap().catch(initLeafletPickupMap);
    } else {
        initLeafletPickupMap();
    }
}

$$('[data-qty]').forEach(g => $$('button', g).forEach(b => b.addEventListener('click', () => {
    const s = $('span', g);
    s.textContent = Math.max(1, +s.textContent + (b.dataset.step === 'up' ? 1 : -1))
}))); 
$$('.faq button').forEach(b => b.addEventListener('click', () => b.parentElement.classList.toggle('open')));
$('.chat-form')?.addEventListener('submit', e => {
    e.preventDefault();
    const i = $('input', e.currentTarget);
    if (!i.value.trim()) return;
    const d = document.createElement('div');
    d.className = 'msg me';
    d.textContent = i.value;
    $('.messages').append(d);
    i.value = '';
    $('.messages').scrollTop = $('.messages').scrollHeight
});
$('.catalog-btn')?.addEventListener('click', () => toast('Kategoriyalar menyusi — frontend demo'));

function toast(t) {
    let e = $('.toast');
    if (!e) {
        e = document.createElement('div');
        e.className = 'toast';
        document.body.append(e)
    }
    e.textContent = t;
    e.classList.add('show');
    setTimeout(() => e.classList.remove('show'), 2200)
}
