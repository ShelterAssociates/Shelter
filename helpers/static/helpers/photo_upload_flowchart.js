/* flowchart guide for the non-superuser photo upload page */
window.PHOTO_UPLOAD_FLOWCHART_EXTERNAL = true
    ; (function ($) {
        var $flowchart = $('#photoTypeFlowchart')
        if (!$flowchart.length) {
            return
        }

        var treeUrl = $('#photoUploadContainer').data('photo-type-tree-url')
        var flatUrl = $('#photoUploadContainer').data('photo-type-items-url')

        var PALETTES = [
            { rootBg: '#dbeafe', rootBd: '#3b82f6', rootTxt: '#1e3a8a', midBg: '#eff6ff', midBd: '#93c5fd', midTxt: '#1e40af', leafBg: '#1d4ed8', leafTxt: '#fff', leafBd: '#1d4ed8' },
            { rootBg: '#dcfce7', rootBd: '#22c55e', rootTxt: '#14532d', midBg: '#f0fdf4', midBd: '#86efac', midTxt: '#065f46', leafBg: '#16a34a', leafTxt: '#fff', leafBd: '#16a34a' },
            { rootBg: '#ede9fe', rootBd: '#8b5cf6', rootTxt: '#4c1d95', midBg: '#faf5ff', midBd: '#c4b5fd', midTxt: '#581c87', leafBg: '#7c3aed', leafTxt: '#fff', leafBd: '#7c3aed' },
            { rootBg: '#fef3c7', rootBd: '#f59e0b', rootTxt: '#78350f', midBg: '#fffbeb', midBd: '#fde68a', midTxt: '#92400e', leafBg: '#d97706', leafTxt: '#fff', leafBd: '#d97706' },
            { rootBg: '#cffafe', rootBd: '#06b6d4', rootTxt: '#164e63', midBg: '#ecfeff', midBd: '#67e8f9', midTxt: '#155e75', leafBg: '#0891b2', leafTxt: '#fff', leafBd: '#0891b2' }
        ]

        function buildTreeFromFlat(items) {
            var map = {}
            var roots = []
            items.forEach(function (item) {
                map[item.id] = { id: item.id, name: item.name, has_children: item.has_children, children: [] }
            })
            items.forEach(function (item) {
                if (item.parent_id && map[item.parent_id]) {
                    map[item.parent_id].children.push(map[item.id])
                } else if (!item.parent_id) {
                    roots.push(map[item.id])
                }
            })
            return roots
        }

        function fetchAllItems(callback) {
            var allItems = []
            var pending = 0

            function fetchLevel(parentId) {
                pending++
                var params = parentId ? { parent_id: parentId } : {}
                $.get(flatUrl, params, function (data) {
                    if (data && data.length) {
                        data.forEach(function (item) {
                            allItems.push(item)
                            if (item.has_children) fetchLevel(item.id)
                        })
                    }
                    pending--
                    if (pending === 0) callback(buildTreeFromFlat(allItems))
                }).fail(function () {
                    pending--
                    if (pending === 0) callback(buildTreeFromFlat(allItems))
                })
            }

            fetchLevel(null)
        }

        function buildBlock(node, pal, depth) {
            var hasKids = node.children && node.children.length > 0

            if (depth === 0) {
                var $block = $('<div class="fc-root-block">').css({ background: pal.rootBg, borderColor: pal.rootBd })
                var $lbl = $('<div class="fc-root-label">').css({ background: pal.rootBg, color: pal.rootTxt, borderBottomColor: pal.rootBd }).html('<svg viewBox="0 0 24 24"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>').append($('<span>').text(node.name))
                $block.append($lbl)

                if (hasKids) {
                    var $body = $('<div class="fc-root-body">')
                    var leaves = node.children.filter(function (c) {
                        return !c.has_children && (!c.children || !c.children.length)
                    })
                    var mids = node.children.filter(function (c) {
                        return c.has_children || (c.children && c.children.length)
                    })
                    mids.forEach(function (c) {
                        $body.append(buildBlock(c, pal, 1))
                    })
                    if (leaves.length) {
                        var $pills = $('<div class="fc-direct-leaves">')
                        leaves.forEach(function (l) {
                            $pills.append($('<span class="fc-leaf-pill">').css({ background: pal.leafBg, color: pal.leafTxt }).text(l.name))
                        })
                        $body.append($pills)
                    }
                    $block.append($body)
                }
                return $block
            }

            if (depth === 1) {
                var $mid = $('<div class="fc-mid-block">').css({ background: pal.midBg, borderColor: pal.midBd })
                var $ml = $('<div class="fc-mid-label">').css({ background: pal.midBg, color: pal.midTxt, borderBottomColor: pal.midBd }).html('<svg viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6"/></svg>').append($('<span>').text(node.name))
                $mid.append($ml)

                if (hasKids) {
                    var $mb = $('<div class="fc-mid-body">')
                    var lk = node.children.filter(function (c) {
                        return !c.has_children && (!c.children || !c.children.length)
                    })
                    var dk = node.children.filter(function (c) {
                        return c.has_children || (c.children && c.children.length)
                    })
                    dk.forEach(function (c) {
                        $mb.append(buildBlock(c, pal, 2))
                    })
                    if (lk.length) {
                        var $lp = $('<div class="fc-leaf-pills">')
                        lk.forEach(function (l) {
                            $lp.append($('<span class="fc-leaf-pill">').css({ background: pal.leafBg, color: pal.leafTxt }).text(l.name))
                        })
                        $mb.append($lp)
                    }
                    $mid.append($mb)
                }
                return $mid
            }

            var $deep = $('<div class="fc-deep-block">')
            var $dl = $('<div class="fc-deep-label">').css({ color: pal.midTxt }).html('<svg viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6"/></svg>').append($('<span>').text(node.name))
            $deep.append($dl)
            if (hasKids) {
                var $lp2 = $('<div class="fc-leaf-pills">')
                node.children.forEach(function (l) {
                    $lp2.append($('<span class="fc-leaf-pill">').css({ background: pal.leafBg, color: pal.leafTxt }).text(l.name))
                })
                $deep.append($lp2)
            }
            return $deep
        }

        function renderTree(roots) {
            var $fc = $flowchart.empty()
            if (!roots || !roots.length) {
                $fc.html('<div class="fc-loading">No photo types configured yet.</div>')
                return
            }
            roots.forEach(function (root, i) {
                $fc.append(buildBlock(root, PALETTES[i % PALETTES.length], 0))
            })
        }

        if (treeUrl) {
            $.get(treeUrl, function (data) {
                renderTree($.isArray(data) ? data : data.items || [])
            }).fail(function () {
                fetchAllItems(renderTree)
            })
        } else {
            fetchAllItems(renderTree)
        }
    })(jQuery)
