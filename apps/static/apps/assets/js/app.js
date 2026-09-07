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

$$('.heart').forEach(b => b.addEventListener('click', () => {
    b.textContent = b.textContent === '♡' ? '♥' : '♡';
    b.style.color = b.textContent === '♥' ? '#ff3b57' : '';
    toast(b.textContent === '♥' ? 'Sevimlilarga qo‘shildi' : 'Sevimlilardan olib tashlandi')
}));
$$('[data-cart]').forEach(b => b.addEventListener('click', () => {
    const n = $('[data-cart-count]');
    if (n) n.textContent = +n.textContent + 1;
    toast('Mahsulot savatga qo‘shildi')
}));
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
