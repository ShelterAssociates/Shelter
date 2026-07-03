from django import template


register = template.Library()


@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    query = context["request"].GET.copy()
    for key, value in kwargs.items():
        if value in (None, "", []):
            query.pop(key, None)
        elif isinstance(value, (list, tuple)):
            query.setlist(key, [str(item) for item in value if item not in (None, "")])
        else:
            query[key] = value
    return query.urlencode()