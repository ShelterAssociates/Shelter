$(document).ready(function () {

    // Hide navbar if inside iframe
    try {
        if (window.location !== window.parent.location) {
            $('#navbar').hide();
        }
    } catch (e) { }

    // Guard against duplicate AJAX calls
    if ($(".city-cards-list").data('loaded')) return;
    $(".city-cards-list").data('loaded', true);

    // -------------------------------------------------------
    // formatNumber: manual Indian format, no locale API needed
    // toLocaleString('en-IN') breaks on iOS WKWebView browsers
    // -------------------------------------------------------
    function formatNumber(value) {
        var number = parseInt(value, 10);
        if (isNaN(number) || number === 0) return '0';

        var s = number.toString();
        var lastThree = s.length > 3 ? s.substring(s.length - 3) : s;
        var rest = s.length > 3 ? s.substring(0, s.length - 3) : '';
        if (rest !== '') {
            lastThree = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' + lastThree;
        }
        return lastThree;
    }

    // -------------------------------------------------------
    // add_cards: uses cloneNode + querySelector (iOS safe)
    // -------------------------------------------------------
    function add_cards(name, data) {
        try {
            var template = document.querySelector("div[name=section_card_clone]");
            if (!template) return;

            var cardEl = template.cloneNode(true);
            cardEl.setAttribute('name', 'card');
            cardEl.classList.remove('hide');

            var cityNameEl = cardEl.querySelector('.city_name');
            var slumsEl = cardEl.querySelector('.number-of-slums');
            var householdsEl = cardEl.querySelector('.household-count');
            var dashboardEl = cardEl.querySelector('.dashboard-url');
            var gisEl = cardEl.querySelector('.gis-url');

            if (cityNameEl) cityNameEl.innerHTML = name;
            if (slumsEl) slumsEl.innerHTML = formatNumber(data['slum_count']) + " / " + formatNumber(data['total_slum_count']);
            if (householdsEl) householdsEl.innerHTML = formatNumber(data['household_count__sum']);
            if (dashboardEl) dashboardEl.href = "/dashboard/" + data['city_id'];
            if (gisEl) gisEl.href = "/" + data['city_id'];

            var list = document.querySelector(".city-cards-list");
            if (list) list.appendChild(cardEl);

        } catch (e) {
            console.error("add_cards error:", e);
        }
    }

    // -------------------------------------------------------
    // populate_new_statsbar: writes directly to new icon bar
    // -------------------------------------------------------
    function populate_new_statsbar(data) {
        try {
            var total_slums = 0;
            var total_households = 0;
            var total_population = 0;
            var total_toilets = 0;

            // Hardcoded toilet counts: 1282-Sangli, 3952-Pune, 14-Donje
            if (Object.keys(data).length > 1) {
                total_toilets = 1282 + 3952 + 14;
            }

            $.each(data, function (key, value) {
                total_slums += value['slum_count'] == null ? 0 : parseInt(value['slum_count'], 10) || 0;
                total_households += value['household_count__sum'] == null ? 0 : parseInt(value['household_count__sum'], 10) || 0;
                total_population += value['slum_population__sum'] == null ? 0 : parseInt(value['slum_population__sum'], 10) || 0;
                total_toilets += value['count_of_toilets_completed__sum'] == null ? 0 : parseInt(value['count_of_toilets_completed__sum'], 10) || 0;
            });

            var bar = document.querySelector('.new-statsbar');
            if (!bar) return;

            var tEl = bar.querySelector('[data-stat="toilets"]');
            var sEl = bar.querySelector('[data-stat="slums"]');
            var hEl = bar.querySelector('[data-stat="households"]');
            var pEl = bar.querySelector('[data-stat="population"]');

            if (tEl) tEl.textContent = formatNumber(total_toilets);
            if (sEl) sEl.textContent = formatNumber(total_slums);
            if (hEl) hEl.textContent = formatNumber(total_households);
            if (pEl) pEl.textContent = formatNumber(total_population);

            // Hide old statsbar
            var oldBars = document.querySelectorAll('.dashboard-statsbar');
            for (var i = 0; i < oldBars.length; i++) {
                if (!oldBars[i].classList.contains('new-statsbar')) {
                    oldBars[i].style.cssText = 'display:none!important';
                }
            }
        } catch (e) {
            console.error("populate_new_statsbar error:", e);
        }
    }

    // -------------------------------------------------------
    // AJAX — use plain XMLHttpRequest instead of $.ajax
    // $.ajax can behave differently in WKWebView on iOS Chrome
    // -------------------------------------------------------
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/graphs/card/all/', true);
    xhr.withCredentials = true;
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.setRequestHeader('Accept', 'application/json');

    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) return;

        if (xhr.status === 200) {
            try {
                var json = JSON.parse(xhr.responseText);

                // Clear cards list
                var cardsList = document.querySelector(".city-cards-list");
                if (cardsList) cardsList.innerHTML = '';

                // Render city cards
                var cities = json['city'] || {};
                Object.keys(cities).forEach(function (key) {
                    var value = cities[key];
                    if (value['household_count__sum'] > 0) {
                        add_cards(key, value);
                    }
                });

                // Update old subheader bar safely
                if (typeof populate_top_bar === 'function') {
                    try { populate_top_bar(json['city']); } catch (e) { }
                }

                // Update new icon statsbar
                populate_new_statsbar(json['city']);

            } catch (e) {
                console.error("JSON parse error:", e);
            }
        } else {
            console.error("XHR failed with status:", xhr.status);
        }
    };

    xhr.onerror = function () {
        console.error("XHR network error");
    };

    xhr.send();

});