/* Kickoff Kits – animated UI layer (themes/hummingbird/assets/js/custom.js) */
(function () {
  'use strict';
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var fine = window.matchMedia && window.matchMedia('(pointer: fine)').matches;
  document.documentElement.setAttribute('data-bs-theme', 'dark');

  function ready(fn) { if (document.readyState !== 'loading') fn(); else document.addEventListener('DOMContentLoaded', fn); }

  ready(function () {
    var base = (window.prestashop && prestashop.urls && prestashop.urls.base_url) || '/g15/';

    /* 1. scroll progress + header state */
    var bar = document.createElement('div'); bar.id = 'kk-progress'; document.body.appendChild(bar);
    var onScroll = function () {
      var h = document.documentElement.scrollHeight - innerHeight;
      bar.style.transform = 'scaleX(' + (h > 0 ? scrollY / h : 0) + ')';
      document.body.classList.toggle('kk-scrolled', scrollY > 40);
    };
    addEventListener('scroll', onScroll, { passive: true }); onScroll();

    /* 2. homepage hero + marquee */
    if (document.body.id === 'index' && !document.querySelector('.kk-hero')) {
      var img = function (id) { return base + id + '-default_lg/kit.jpg'; };
      var hero = document.createElement('section');
      hero.className = 'kk-hero';
      hero.innerHTML =
        '<div class="kk-hero__grid"></div>' +
        '<div class="container-md"><div class="kk-hero__inner">' +
          '<div>' +
            '<span class="kk-eyebrow"><i class="kk-dot"></i> New season drop · <b>Šiauliai, LT</b></span>' +
            '<h1 class="kk-title" aria-label="Wear the game">' +
              '<span class="kk-line"><span class="kk-word">Wear</span></span>' +
              '<span class="kk-line"><span class="kk-word kk-stroke">the</span></span>' +
              '<span class="kk-line"><span class="kk-word kk-grad">game.</span></span>' +
            '</h1>' +
            '<p class="kk-sub">Club home &amp; away kits, retro Lithuania classics and goalkeeper jerseys — built for match day, priced for real fans.</p>' +
            '<div class="kk-ctas">' +
              '<a class="kk-btn kk-btn--main kk-magnet" href="' + base + '2-home">Shop jerseys <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M5 12h14M13 6l6 6-6 6"/></svg></a>' +
              '<a class="kk-btn kk-btn--ghost kk-magnet" href="#kk-news">Get 10% off</a>' +
            '</div>' +
            '<div class="kk-stats">' +
              '<div><strong data-count="4">0</strong><span>signature kits</span></div>' +
              '<div><strong data-count="24" data-suffix="h">0</strong><span>dispatch in LT</span></div>' +
              '<div><strong data-count="30" data-suffix="d">0</strong><span>free returns</span></div>' +
            '</div>' +
          '</div>' +
          '<div class="kk-stage" aria-hidden="true">' +
            '<div class="kk-float kk-float--1"><div class="kk-float__bob"><img src="' + img(4) + '" alt=""></div></div>' +
            '<div class="kk-float kk-float--2"><div class="kk-float__bob"><img src="' + img(2) + '" alt=""></div></div>' +
            '<div class="kk-float kk-float--3"><div class="kk-float__bob"><img src="' + img(1) + '" alt=""></div></div>' +
            '<div class="kk-price-tag">Retro Lithuania #9<b>€54.99</b></div>' +
          '</div>' +
        '</div></div>';
      var marquee = document.createElement('div');
      marquee.className = 'kk-marquee';
      var items = ['Free delivery in Lithuania over €60', 'Code KICKOFF10 = −10%', '30-day free returns', 'Retro Lithuania #9 is back', 'Goalkeeper kits in stock'];
      var html = items.map(function (t) { return '<span>' + t + '</span>'; }).join('');
      marquee.innerHTML = '<div class="kk-marquee__track">' + html + html + '</div>';

      var main = document.querySelector('main.wrapper, main, #wrapper');
      if (main) { main.parentNode.insertBefore(hero, main); main.parentNode.insertBefore(marquee, main); }

      /* parallax tilt of the jersey stack */
      var stage = hero.querySelector('.kk-stage');
      if (fine && !reduce && stage) {
        hero.addEventListener('pointermove', function (e) {
          var r = stage.getBoundingClientRect();
          var x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
          stage.querySelectorAll('.kk-float').forEach(function (el, i) {
            var d = (i + 1) * 10;
            el.style.translate = (x * d) + 'px ' + (y * d) + 'px';
            el.style.rotate = 'x ' + (-y * 10) + 'deg';
          });
        });
      }

      /* count-up stats */
      hero.querySelectorAll('[data-count]').forEach(function (el) {
        var end = +el.dataset.count, suf = el.dataset.suffix || '', t0 = null;
        var step = function (t) { if (!t0) t0 = t; var p = Math.min((t - t0) / 1400, 1);
          el.textContent = Math.round(end * (1 - Math.pow(1 - p, 3))) + suf; if (p < 1) requestAnimationFrame(step); };
        setTimeout(function () { requestAnimationFrame(step); }, reduce ? 0 : 900);
      });
    }

    /* remove leftover demo banner ("20% off on clothes") */
    document.querySelectorAll('a.banner').forEach(function (a) { a.remove(); });

    var news = document.querySelector('.ps-emailsubscription');
    if (news) news.id = news.id || 'kk-news';

    /* 3. scroll reveal with stagger */
    var targets = document.querySelectorAll('.product-miniature, .ps-customtext, .ps-emailsubscription, .footer__main .col, .footer__main [class*=col-], section h2, .subcategories, .product__left, .product__right');
    if ('IntersectionObserver' in window && !reduce) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('kk-in'); io.unobserve(en.target); } });
      }, { threshold: .12, rootMargin: '0px 0px -40px 0px' });
      targets.forEach(function (el, i) {
        el.classList.add('kk-reveal');
        var sib = el.parentElement ? Array.prototype.indexOf.call(el.parentElement.children, el) : 0;
        el.style.setProperty('--kk-delay', (Math.min(sib, 6) * 0.08) + 's');
        io.observe(el);
      });
    }

    /* 4. 3D tilt + cursor glow on product cards */
    if (fine && !reduce) {
      document.addEventListener('pointermove', function (e) {
        var card = e.target.closest && e.target.closest('.product-miniature__inner');
        if (!card) return;
        var r = card.getBoundingClientRect();
        var x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
        card.style.setProperty('--mx', (x * 100) + '%'); card.style.setProperty('--my', (y * 100) + '%');
        card.style.transform = 'perspective(900px) rotateX(' + ((.5 - y) * 8) + 'deg) rotateY(' + ((x - .5) * 10) + 'deg) translateY(-6px)';
      });
      document.addEventListener('pointerout', function (e) {
        var card = e.target.closest && e.target.closest('.product-miniature__inner');
        if (card && !card.contains(e.relatedTarget)) card.style.transform = '';
      });

      /* magnetic buttons */
      document.querySelectorAll('.kk-magnet, .btn-primary').forEach(function (b) {
        b.addEventListener('pointermove', function (e) {
          var r = b.getBoundingClientRect();
          b.style.transform = 'translate(' + ((e.clientX - r.left - r.width / 2) * .18) + 'px,' + ((e.clientY - r.top - r.height / 2) * .25) + 'px)';
        });
        b.addEventListener('pointerleave', function () { b.style.transform = ''; });
      });
    }

    /* 5. add-to-cart feedback toast */
    var toast = document.createElement('div'); toast.className = 'kk-toast'; toast.setAttribute('role', 'status'); document.body.appendChild(toast);
    var showToast = function (msg) { toast.textContent = msg; toast.classList.add('kk-show'); clearTimeout(toast._t); toast._t = setTimeout(function () { toast.classList.remove('kk-show'); }, 2600); };
    if (window.prestashop && prestashop.on) {
      prestashop.on('updateCart', function (ev) {
        if (ev && ev.reason && ev.reason.linkAction === 'add-to-cart') showToast('⚽ Added to your cart — nice pick!');
      });
    }
    document.addEventListener('click', function (e) {
      var b = e.target.closest && e.target.closest('[data-button-action="add-to-cart"], .add-to-cart, .product-miniature .btn-primary');
      if (b) { b.classList.remove('kk-added'); void b.offsetWidth; b.classList.add('kk-added'); }
    });
  });
})();
