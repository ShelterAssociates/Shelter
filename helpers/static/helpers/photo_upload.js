/* photo_upload.js — drives the Photo Upload Django admin page */
; (function ($) {
    'use strict'

    /* ── helpers ── */
    function getConfig() {
        var $c = $('#photoUploadContainer')
        return {
            isSuperuser: $c.data('is-superuser') === true || $c.data('is-superuser') === 'true',
            cityListUrl: $c.data('city-list-url'),
            adminWardListUrl: $c.data('administrative-ward-list-url'),
            electoralWardListUrl: $c.data('electoral-ward-list-url'),
            slumListUrl: $c.data('slum-list-url'),
            sponsorProjectListUrl: $c.data('sponsor-project-list-url'),
            photoTypeItemsUrl: $c.data('photo-type-items-url'),
            manageTreeUrl: $c.data('manage-tree-url'),
            manageToggleUrl: $c.data('manage-toggle-url'),
            manageAddUrl: $c.data('manage-add-url'),
            uploadUrl: $c.data('upload-url'),
            csrfToken: $('input[name="csrfmiddlewaretoken"]').val()
        }
    }

    var cfg = getConfig()

    /*
     * populate a <select> from the API response format:
     *   { idArray: [1,2,3], nameArray: ['A','B','C'] }
     * OR a plain array of objects: [{id,name}, ...]
     */
    function populateSelect($sel, data, placeholder) {
        $sel.empty().append($('<option value="">').text(placeholder || '— Select —'))

        if (data && data.idArray && data.nameArray) {
            /* parallel-array format used by cityList, administrativewardList, etc. */
            $.each(data.idArray, function (i, id) {
                $sel.append($('<option>').val(id).text(data.nameArray[i]))
            })
        } else if ($.isArray(data)) {
            /* array-of-objects format */
            $.each(data, function (i, item) {
                $sel.append($('<option>').val(item.id).text(item.name))
            })
        }

        $sel.prop('disabled', false)
    }

    function disableSelect($sel, placeholder) {
        $sel.empty().append($('<option value="">').text(placeholder || '— Select —'))
        $sel.prop('disabled', true)
    }

    /* ════════════════════════════════════════
       1. LOCATION CASCADE
       ════════════════════════════════════════ */

    /* Load cities on page load */
    $.get(cfg.cityListUrl, function (data) {
        populateSelect($('#city'), data, '— Select City —')
    })

    /* Load sponsor projects on page load */
    $.get(cfg.sponsorProjectListUrl, function (data) {
        populateSelect($('#sponsor_project'), data, '— No Sponsor Project —')
        // re-prepend the "no project" blank option
        $('#sponsor_project option:first').text('— No Sponsor Project —')
    }).fail(function () {
        // sponsor project is optional – silently ignore failures
    })

    $('#city').on('change', function () {
        var cityId = $(this).val()
        disableSelect($('#admin_ward'), '— Select Administrative Ward —')
        disableSelect($('#electoral_ward'), '— Select Electoral Ward —')
        disableSelect($('#slum'), '— Select Slum —')
        if (!cityId) return
        /* administrativewardList expects POST with param 'id' */
        $.post(cfg.adminWardListUrl, { id: cityId, csrfmiddlewaretoken: cfg.csrfToken }, function (data) {
            populateSelect($('#admin_ward'), data, '— Select Administrative Ward —')
        })
    })

    $('#admin_ward').on('change', function () {
        var wardId = $(this).val()
        disableSelect($('#electoral_ward'), '— Select Electoral Ward —')
        disableSelect($('#slum'), '— Select Slum —')
        if (!wardId) return
        /* electoralWardList expects POST with param 'id' */
        $.post(cfg.electoralWardListUrl, { id: wardId, csrfmiddlewaretoken: cfg.csrfToken }, function (data) {
            populateSelect($('#electoral_ward'), data, '— Select Electoral Ward —')
        })
    })

    $('#electoral_ward').on('change', function () {
        var eWardId = $(this).val()
        disableSelect($('#slum'), '— Select Slum —')
        if (!eWardId) return
        /* slumList expects POST with param 'id' */
        $.post(cfg.slumListUrl, { id: eWardId, csrfmiddlewaretoken: cfg.csrfToken }, function (data) {
            populateSelect($('#slum'), data, '— Select Slum —')
        })
    })

    /* ════════════════════════════════════════
       2. PHOTO TYPE CASCADING PICKER
       API returns: [{id, name, parent_id, has_children, full_path}, ...]
       Fetched level by level via ?parent_id=X
       ════════════════════════════════════════ */

    var $picker = $('#photoTypePicker')
    var $hiddenTypeId = $('#photo_type_item_id')
    var $summary = $('#photoTypeSummary')

    function clearLevelsAfter(levelIndex) {
        $picker.find('.photo-type-level-row').each(function () {
            if ($(this).data('level') > levelIndex) $(this).remove()
        })
    }

    function updateSummary() {
        var parts = []
        $picker.find('.photo-type-level-row select').each(function () {
            var $selected = $(this).find('option:selected')
            var value = $(this).val()
            if (value) {
                var label = $.trim($selected.text())
                if (label) parts.push(label)
            }
        })

        if (parts.length) {
            $summary.html('<strong>Selected path:</strong> ' + $('<div>').text(parts.join(' / ')).html())
        } else {
            $summary.text('Select a photo type to see the full path here.')
        }
    }

    function addLevelRow(items, levelIndex, labelText) {
        var $row = $('<div class="photo-row photo-type-level-row">').data('level', levelIndex)
        var rowId = 'photo_type_level_' + levelIndex
        $row.append($('<label>').attr('for', rowId).text(labelText || 'Level ' + (levelIndex + 1)))

        var $sel = $('<select>').attr('id', rowId)
        $sel.append($('<option value="">— Select —</option>'))
        $.each(items, function (i, item) {
            $sel.append($('<option>').val(item.id).text(item.name).attr('title', item.full_path || item.name).data('has-children', item.has_children))
        })
        $row.append($sel)
        $picker.append($row)

        $sel.on('change', function () {
            var selectedId = $(this).val()
            var hasChildren = $(this).find(':selected').data('has-children')
            clearLevelsAfter(levelIndex)
            $hiddenTypeId.val('')
            checkUploadReady()
            updateSummary()

            if (!selectedId) return

            if (hasChildren) {
                /* fetch next level */
                $.get(cfg.photoTypeItemsUrl, { parent_id: selectedId }, function (data) {
                    if (data && data.length > 0) {
                        addLevelRow(data, levelIndex + 1, getLevelLabel(levelIndex + 1))
                    } else {
                        /* no children returned — treat as leaf */
                        $hiddenTypeId.val(selectedId)
                        checkUploadReady()
                        updateSummary()
                    }
                }).fail(function () {
                    $hiddenTypeId.val(selectedId)
                    checkUploadReady()
                    updateSummary()
                })
            } else {
                /* leaf node — set value directly */
                $hiddenTypeId.val(selectedId)
                checkUploadReady()
                updateSummary()
            }
        })
    }

    function getLevelLabel(index) {
        var labels = ['Photo Category', 'Sub-category', 'Type', 'Sub-type', 'Detail']
        return labels[index] || 'Level ' + (index + 1)
    }

    function initPhotoTypePicker() {
        $picker.empty()
        $hiddenTypeId.val('')
        updateSummary()
        $.get(cfg.photoTypeItemsUrl, function (data) {
            if (data && data.length > 0) {
                addLevelRow(data, 0, getLevelLabel(0))
            } else {
                $picker.html('<div style="font-size:12px;color:#9ca3af;padding:6px 0;">No photo types available.</div>')
            }
        }).fail(function (xhr) {
            $picker.html('<div style="font-size:12px;color:#991b1b;padding:6px 0;">Error loading photo types.</div>')
        })
    }

    initPhotoTypePicker()

    /* ════════════════════════════════════════
       3. UPLOAD READINESS & SUBMIT
       ════════════════════════════════════════ */

    function checkUploadReady() {
        var slumId = $('#slum').val()
        var typeId = $hiddenTypeId.val()
        var hasPhotos = $('#photos')[0] && $('#photos')[0].files && $('#photos')[0].files.length > 0
        $('#uploadButton').prop('disabled', !(slumId && typeId && hasPhotos))
    }

    $('#slum, #photo_type_item_id').on('change', checkUploadReady)
    $('#photos').on('change', checkUploadReady)

    /* Also hook slum select since it's a regular select not hidden */
    $(document).on('change', '#slum', checkUploadReady)

    function setStatus(type, html) {
        var $s = $('#uploadStatus')
        $s.removeClass('success error loading').addClass(type).html(html).show()
        if (type === 'success' || type === 'error') {
            $('html, body').animate({ scrollTop: $s.offset().top - 20 }, 300)
        }
    }

    $('#photoUploadForm').on('submit', function (e) {
        e.preventDefault()

        var files = $('#photos')[0].files
        if (!files || files.length === 0) {
            setStatus('error', 'Please select at least one photo.')
            return
        }
        if (files.length > 5) {
            setStatus('error', 'Maximum 5 photos per upload.')
            return
        }
        if (!$('#slum').val()) {
            setStatus('error', 'Please select a slum.')
            return
        }
        if (!$hiddenTypeId.val()) {
            setStatus('error', 'Please complete the photo type selection.')
            return
        }

        $('#uploadButton').prop('disabled', true)
        setStatus('loading', '⏳ Uploading and encrypting photos…')

        var formData = new FormData(this)

        $.ajax({
            url: cfg.uploadUrl,
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function (resp) {
                if (resp && resp.success) {
                    var link = resp.folder_url
                        ? ' <a href="' + resp.folder_url + '" target="_blank">View folder ↗</a>'
                        : ''
                    setStatus('success', '✅ ' + (resp.message || 'Photos uploaded successfully!') + link)
                    /* reset form */
                    $('#photoUploadForm')[0].reset()
                    initPhotoTypePicker()
                    disableSelect($('#admin_ward'), '— Select Administrative Ward —')
                    disableSelect($('#electoral_ward'), '— Select Electoral Ward —')
                    disableSelect($('#slum'), '— Select Slum —')
                } else {
                    setStatus('error', '❌ ' + (resp && resp.message ? resp.message : 'Upload failed. Please try again.'))
                }
                $('#uploadButton').prop('disabled', false)
                checkUploadReady()
            },
            error: function (xhr) {
                var msg = 'Upload failed.'
                try {
                    var r = JSON.parse(xhr.responseText)
                    if (r && r.message) msg = r.message
                } catch (ex) { }
                setStatus('error', '❌ ' + msg)
                $('#uploadButton').prop('disabled', false)
                checkUploadReady()
            }
        })
    })

    /* ════════════════════════════════════════
       4. SUPERUSER MANAGEMENT TREE
       ════════════════════════════════════════ */

    if (!cfg.isSuperuser) return  /* non-superuser stops here */

    function renderNode(node, depth) {
        var hasChildren = node.children && node.children.length > 0
        var isRoot = depth === 0

        var $wrap = $('<div class="tree-node">')
        var $row = $('<div class="tree-row">')

        /* chevron toggle */
        var $tog = $('<button class="tree-toggle" type="button" aria-label="expand">')
        $tog.html('<svg viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6"/></svg>')
        if (!hasChildren) $tog.addClass('leaf')
        $row.append($tog)

        /* depth badge */
        var badgeLabel = isRoot ? 'Root' : 'Sub'
        var badgeClass = isRoot ? 'root' : 'child'
        $row.append($('<span class="tree-badge ' + badgeClass + '">').text(badgeLabel))

        /* name */
        var $name = $('<span class="tree-name">').text(node.name)
        if (!node.is_visible) $name.addClass('hidden-item')
        $row.append($name)

        /* actions */
        var $acts = $('<div class="tree-actions">')

        var $addBtn = $('<button type="button" class="tree-btn">').html(
            '<svg viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg> Child'
        )
        $addBtn.on('click', function (e) {
            e.stopPropagation()
            var n = window.prompt('New child name under "' + node.name + '"')
            if (!n || !n.trim()) return
            $.post(cfg.manageAddUrl, {
                parent_id: node.id,
                name: n.trim(),
                csrfmiddlewaretoken: cfg.csrfToken
            }, function () {
                loadTree()
                initPhotoTypePicker()
            })
        })
        $acts.append($addBtn)

        var $togBtn = $('<button type="button" class="tree-btn">')
        if (node.is_visible) {
            $togBtn.addClass('hide-btn').html(
                '<svg viewBox="0 0 24 24"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/>' +
                '<path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/>' +
                '<line x1="1" y1="1" x2="23" y2="23"/></svg> Hide'
            )
        } else {
            $togBtn.addClass('show-btn').html(
                '<svg viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>' +
                '<circle cx="12" cy="12" r="3"/></svg> Show'
            )
        }
        $togBtn.on('click', function (e) {
            e.stopPropagation()
            $.post(cfg.manageToggleUrl, {
                item_id: node.id,
                csrfmiddlewaretoken: cfg.csrfToken
            }, function () {
                loadTree()
                initPhotoTypePicker()
            })
        })
        $acts.append($togBtn)

        $row.append($acts)
        $wrap.append($row)

        /* children container */
        if (hasChildren) {
            var $kids = $('<div class="tree-children">').hide()
            $.each(node.children, function (i, child) {
                $kids.append(renderNode(child, depth + 1))
            })
            $wrap.append($kids)

            $tog.on('click', function (e) {
                e.stopPropagation()
                if ($tog.hasClass('open')) {
                    $kids.slideUp(160)
                    $tog.removeClass('open')
                } else {
                    $kids.slideDown(180)
                    $tog.addClass('open')
                }
            })

            if (isRoot) {
                $tog.addClass('open')
                $kids.show()
            }
        }

        return $wrap
    }

    function loadTree() {
        $.get(cfg.manageTreeUrl, function (data) {
            var $tree = $('#photoTypeTree').empty()
            var total = 0
            function countAll(nodes) {
                $.each(nodes, function (i, n) {
                    total++
                    if (n.children) countAll(n.children)
                })
            }
            countAll(data)
            $('#mgmt-count').text(total + ' type' + (total !== 1 ? 's' : ''))

            if (!data.length) {
                $tree.append(
                    '<div class="tree-empty">' +
                    '<svg viewBox="0 0 24 24"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>' +
                    'No types yet. Use Add Root Type to start.</div>'
                )
                return
            }
            $.each(data, function (i, node) {
                $tree.append(renderNode(node, 0))
            })
        })
    }

    $('#mgmt_add_root').on('click', function () {
        var n = window.prompt('Root type name')
        if (!n || !n.trim()) return
        $.post(cfg.manageAddUrl, {
            name: n.trim(),
            csrfmiddlewaretoken: cfg.csrfToken
        }, function () {
            loadTree()
            initPhotoTypePicker()
        })
    })

    loadTree()

})(jQuery)