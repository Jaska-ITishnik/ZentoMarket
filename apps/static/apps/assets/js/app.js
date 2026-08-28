const $ = (s, c = document) => c.querySelector(s), $$ = (s, c = document) => [...c.querySelectorAll(s)];
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
