/* Sends the page's CSRF token with every same-origin POST/PUT/PATCH/DELETE made
 * by XMLHttpRequest (every jQuery copy uses it) or fetch. The token comes from
 * this tag's data-token ({{ csrf_token }}) or a form's csrfmiddlewaretoken field;
 * the cookie is HttpOnly. Never sent to another origin.
 * Include right after jQuery:
 *   <script src="{% static 'js/csrf.js' %}" data-token="{{ csrf_token }}"></script>
 */
(function () {
    if (window.__csrfShim) return;
    window.__csrfShim = true;

    var HEADER = "X-CSRFToken";
    var script = document.currentScript;
    var pageToken = script && script.getAttribute("data-token");

    function token() {
        if (pageToken) return pageToken;
        var field = document.querySelector("input[name=csrfmiddlewaretoken]");
        return field ? field.value : "";
    }

    function needsToken(method, url) {
        if (/^(GET|HEAD|OPTIONS|TRACE)$/i.test(method || "GET")) return false;
        try {
            return new URL(url, window.location.href).origin === window.location.origin;
        } catch (e) {
            return false;
        }
    }

    var proto = XMLHttpRequest.prototype;
    var open = proto.open;
    var send = proto.send;
    var setRequestHeader = proto.setRequestHeader;

    proto.open = function (method, url) {
        this._csrfNeeded = needsToken(method, url);
        this._csrfSet = false;
        return open.apply(this, arguments);
    };
    proto.setRequestHeader = function (name) {
        if (String(name).toLowerCase() === HEADER.toLowerCase()) this._csrfSet = true;
        return setRequestHeader.apply(this, arguments);
    };
    proto.send = function () {
        if (this._csrfNeeded && !this._csrfSet && token()) setRequestHeader.call(this, HEADER, token());
        return send.apply(this, arguments);
    };

    if (window.fetch) {
        var originalFetch = window.fetch;
        window.fetch = function (input, init) {
            var isRequest = typeof Request !== "undefined" && input instanceof Request;
            var method = (init && init.method) || (isRequest ? input.method : "GET");
            var url = isRequest ? input.url : String(input);
            if (needsToken(method, url) && token()) {
                var headers = new Headers((init && init.headers) || (isRequest ? input.headers : undefined));
                if (!headers.has(HEADER)) {
                    headers.set(HEADER, token());
                    init = Object.assign({}, init, {headers: headers});
                }
            }
            return originalFetch.call(this, input, init);
        };
    }
})();
