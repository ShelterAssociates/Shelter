/* Shared slum search box.
 *
 * Filters a slum index rendered into the page and reports the slum that was
 * chosen. The KML upload page and the reports page both use it: each passes
 * its own class prefix and decides what happens on a pick (one opens a confirm
 * modal, the other fills its dropdowns straight away).
 *
 * Every node is filled with .text(), never .html(): slum and ward names are
 * user-entered database values.
 */
(function (global, $) {
    "use strict";

    /**
     * Arrow-key navigation for a list of result rows.
     *
     * opts.$input   - optional text field that keeps focus while arrowing (the
     *                 search box); when absent, the rows take focus themselves.
     * opts.onEscape - where to send focus when the list is dismissed.
     *
     * Rows are real <button>s, so Tab and Enter already work natively; this
     * adds Up/Down, Enter-on-the-highlighted-row, and Escape.
     */
    function enableListKeyboard(opts) {
        const $container = opts.$container;
        const rowSelector = opts.rowSelector;
        let activeIndex = -1;

        function rows() {
            return $container.find(rowSelector);
        }

        function scrollRowIntoView($row) {
            if (!$row.length) return;
            const top = $row.position().top + $container.scrollTop();
            const bottom = top + $row.outerHeight();
            const viewTop = $container.scrollTop();
            const viewBottom = viewTop + $container.innerHeight();
            if (top < viewTop) {
                $container.scrollTop(top);
            } else if (bottom > viewBottom) {
                $container.scrollTop(bottom - $container.innerHeight());
            }
        }

        function setActive(index) {
            const $rows = rows();
            if (!$rows.length) {
                activeIndex = -1;
                return;
            }
            // Wrap at both ends so Up from the top lands on the last row.
            if (index < 0) index = $rows.length - 1;
            if (index >= $rows.length) index = 0;
            activeIndex = index;
            $rows.removeClass("is-active");
            const $active = $rows.eq(index).addClass("is-active");
            scrollRowIntoView($active);
            if (!opts.$input) $active.trigger("focus");
        }

        function clearActive() {
            rows().removeClass("is-active");
            activeIndex = -1;
        }

        function handleKey(e) {
            if (e.key === "ArrowDown" || e.key === "Down") {
                e.preventDefault();
                setActive(activeIndex + 1);
                return;
            }
            if (e.key === "ArrowUp" || e.key === "Up") {
                e.preventDefault();
                setActive(activeIndex - 1);
                return;
            }
            if (e.key === "Enter") {
                const $rows = rows();
                if (!$rows.length) return;
                // These rows live inside a form, so a stray Enter would
                // otherwise submit it.
                e.preventDefault();
                $rows.eq(activeIndex >= 0 ? activeIndex : 0).trigger("click");
                return;
            }
            if (e.key === "Escape" || e.key === "Esc") {
                e.preventDefault();
                clearActive();
                if (opts.onEscape) opts.onEscape();
            }
        }

        if (opts.$input) opts.$input.on("keydown", handleKey);
        // Also bind on the rows, so arrows still work after tabbing into them.
        $container.on("keydown", rowSelector, handleKey);
        // A fresh render invalidates the highlight.
        $container.on("listrendered", clearActive);
        // The mouse and the keyboard shouldn't disagree about what's selected.
        $container.on("mouseenter", rowSelector, function () {
            activeIndex = rows().index(this);
            rows().removeClass("is-active");
            $(this).addClass("is-active");
        });
    }

    /** The slum index a view rendered with json_script, lower-cased once. */
    function readIndex(nodeId) {
        let rows = [];
        try {
            const node = document.getElementById(nodeId);
            rows = node ? (JSON.parse(node.textContent) || []) : [];
        } catch (err) {
            rows = [];
        }
        rows.forEach(function (row) {
            row.haystack = String(row.name).toLowerCase();
        });
        return rows;
    }

    /**
     * opts.index     - rows from readIndex()
     * opts.$input    - the search box
     * opts.$results  - the container the rows are rendered into
     * opts.prefix    - class prefix, e.g. "ku-slum-search" or "slum-search"
     * opts.limit     - how many matches to show (default 15)
     * opts.onPick    - called with the chosen row
     * opts.onEscape  - optional, called when the list is dismissed
     */
    function create(opts) {
        const $input = opts.$input;
        const $results = opts.$results;
        const index = opts.index || [];
        const prefix = opts.prefix;
        const limit = opts.limit || 15;

        function render(query) {
            $results.empty();

            if (!query) {
                $results.css("display", "none");
                return;
            }

            const needle = query.toLowerCase();
            const matches = [];
            for (let i = 0; i < index.length; i++) {
                // Name only. City/ward are shown as context, not searched.
                if (index[i].haystack.indexOf(needle) !== -1) {
                    matches.push(index[i]);
                    // One past the cap, so we can say "there are more" without
                    // scanning the rest of the index.
                    if (matches.length > limit) break;
                }
            }

            $results.css("display", "block");

            if (!matches.length) {
                $results.append(
                    $("<div>").addClass(prefix + "-empty").text("No slum matches that name.")
                );
                return;
            }

            matches.slice(0, limit).forEach(function (row) {
                const $name = $("<div>").addClass(prefix + "-name").text(row.name);
                if (row.active === false) {
                    $name.append($("<span>").addClass(prefix + "-tag").text("Inactive"));
                }

                $results.append(
                    $("<button>")
                        .attr("type", "button")
                        .addClass(prefix + "-row")
                        .attr("data-slum-id", row.id)
                        .append($name)
                        .append(
                            $("<div>").addClass(prefix + "-path")
                                .text(row.city + " › " + row.aw + " › " + row.ew)
                        )
                );
            });

            $results.trigger("listrendered");

            if (matches.length > limit) {
                $results.append(
                    $("<div>").addClass(prefix + "-more")
                        .text("Showing the first " + limit + " matches - keep typing to narrow it down.")
                );
            }
        }

        $input.on("input", function () {
            render($(this).val().trim());
        });

        $results.off("click", "." + prefix + "-row").on("click", "." + prefix + "-row", function (e) {
            e.preventDefault();
            const id = String($(this).attr("data-slum-id"));
            const row = index.filter(function (r) { return String(r.id) === id; })[0];
            if (row) opts.onPick(row);
        });

        enableListKeyboard({
            $input: $input,
            $container: $results,
            rowSelector: "." + prefix + "-row",
            onEscape: function () {
                $input.val("").trigger("focus");
                render("");
                if (opts.onEscape) opts.onEscape();
            }
        });

        return {
            render: render,
            close: function () { render(""); },
            index: index
        };
    }

    global.SlumSearch = { create: create, readIndex: readIndex, enableListKeyboard: enableListKeyboard };
}(window, jQuery));
