'use strict';
{
    const $ = django.jQuery;
    $(function () {
        const $picker = $('#slum-picker');
        if (!$picker.length) {
            return;
        }
        $picker.select2({
            ajax: {
                url: $picker.data('url'),
                dataType: 'json',
                delay: 250,
                data: function (params) {
                    return {term: params.term};
                },
            },
            placeholder: $picker.data('placeholder'),
            width: '320px',
            minimumInputLength: 1,
        });
        $picker.closest('form').on('submit', function () {
            const ids = $picker.val() || [];
            $('#slum-picker-value').val(ids.join(',')).prop('disabled', ids.length === 0);
        });
    });
}
