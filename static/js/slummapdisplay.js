$(document).ready(function () {
    if (window.location !== window.parent.location) {
        $('#navbar').hide();
    }

    // Guard against duplicate AJAX calls (e.g. script loaded twice)
    if ($(".city-cards-list").data('loaded')) return;
    $(".city-cards-list").data('loaded', true);

    function formatNumber(value) {
        var number = parseInt(value, 10);
        if (isNaN(number)) {
            return '0';
        }
        return number.toLocaleString('en-IN');
    }

    function add_cards(name, data) {
        var template = $("div[name=section_card_clone]")[0];

        // Guard: if template missing, skip silently
        if (!template) {
            console.error("Card template (section_card_clone) not found in DOM.");
            return;
        }

        var card = $(template.outerHTML).attr('name', 'card').removeClass('hide');
        card.find(".city_name")[0].innerHTML = name;
        card.find(".number-of-slums")[0].innerHTML = formatNumber(data['slum_count']) + " / " + formatNumber(data['total_slum_count']);
        card.find(".household-count")[0].innerHTML = formatNumber(data['household_count__sum']);
        card.find('.dashboard-url')[0].href = "/dashboard/" + data['city_id'];
        card.find('.gis-url')[0].href = "/" + data['city_id'];
        $(".city-cards-list").append(card);
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
            total_slums += value['slum_count'] == null ? 0 : value['slum_count'];
            total_households += value['household_count__sum'] == null ? 0 : value['household_count__sum'];
            total_population += value['slum_population__sum'] == null ? 0 : value['slum_population__sum'];
            total_toilets += value['count_of_toilets_completed__sum'] == null ? 0 : value['count_of_toilets_completed__sum'];
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

        // Hide the old subheader statsbar now that new one is fully populated
        $('.dashboard-statsbar:not(.new-statsbar)').hide();
    }

    $.ajax({
        url: "/graphs/card/all/",
        type: "GET",
        contentType: "application/json",
        success: function (json) {
            // Clear existing cards first to avoid duplicates on re-runs
            $(".city-cards-list").empty();

            $.each(json['city'], function (key, value) {
                if (value['household_count__sum'] > 0) {
                    add_cards(key, value);
                }
            });

            // Update old subheader bar (desktop fallback) safely
            if (typeof populate_top_bar === 'function') {
                populate_top_bar(json['city']);
            }

            // Always directly update the new statsbar — works on both mobile and desktop
            populate_new_statsbar(json['city']);
        },
        error: function (xhr, status, error) {
            console.error("Failed to load city cards:", xhr.status, status, error);
        }
    });
});