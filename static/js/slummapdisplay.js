$(document).ready(function () {
    if (window.location !== window.parent.location) {
        $('#navbar').hide();
    }

    // Guard against duplicate AJAX calls (e.g. script loaded twice)
    if ($(".city-cards-list").data('loaded')) return;
    $(".city-cards-list").data('loaded', true);

    function formatNumber(value) {
        var number = parseInt(value, 10);
        if (isNaN(number)) return '0';

        // Manual Indian number formatting — works on ALL browsers including
        // WKWebView (iOS Chrome, Firefox, Brave) which doesn't support 'en-IN'
        var s = number.toString();
        var result = '';
        var pos = s.length;

        // Last 3 digits
        result = s.substring(pos - 3);
        pos -= 3;

        // Every 2 digits before that (Indian format: XX,XX,XXX)
        while (pos > 0) {
            var start = Math.max(0, pos - 2);
            result = s.substring(start, pos) + ',' + result;
            pos -= 2;
        }

        return result;
    }

    function add_cards(name, data) {
        var template = document.querySelector("div[name=section_card_clone]");

        if (!template) {
            console.error("Card template (section_card_clone) not found in DOM.");
            return;
        }

        // iOS Safari/Chrome fix: use cloneNode(true) instead of outerHTML
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

        document.querySelector(".city-cards-list").appendChild(cardEl);
    }

    function populate_new_statsbar(data) {
        var total_slums = 0;
        var total_households = 0;
        var total_population = 0;
        var total_toilets = 0;

        // Match the same hardcoded toilet logic from external_dashboard_subheader.js
        // 1282 - Sangli, 3952 - Pune, 14 - Donje
        if (Object.keys(data).length > 1) {
            total_toilets = 1282 + 3952 + 14;
        }

        $.each(data, function (key, value) {
            total_slums += value['slum_count'] == null ? 0 : parseInt(value['slum_count'], 10);
            total_households += value['household_count__sum'] == null ? 0 : parseInt(value['household_count__sum'], 10);
            total_population += value['slum_population__sum'] == null ? 0 : parseInt(value['slum_population__sum'], 10);
            total_toilets += value['count_of_toilets_completed__sum'] == null ? 0 : parseInt(value['count_of_toilets_completed__sum'], 10);
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

        // Hide old subheader statsbar now that new one is fully populated
        var oldBars = document.querySelectorAll('.dashboard-statsbar');
        for (var i = 0; i < oldBars.length; i++) {
            if (!oldBars[i].classList.contains('new-statsbar')) {
                oldBars[i].style.cssText = 'display:none!important';
            }
        }
    }

    $.ajax({
        url: "/graphs/card/all/",
        type: "GET",
        success: function (json) {
            var cardsList = document.querySelector(".city-cards-list");
            if (cardsList) cardsList.innerHTML = '';

            $.each(json['city'], function (key, value) {
                if (value['household_count__sum'] > 0) {
                    add_cards(key, value);
                }
            });

            if (typeof populate_top_bar === 'function') {
                populate_top_bar(json['city']);
            }

            populate_new_statsbar(json['city']);
        },
        error: function (xhr, status, error) {
            console.error("Failed to load city cards:", xhr.status, status, error);
        }
    });
});