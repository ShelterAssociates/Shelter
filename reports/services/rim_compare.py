"""Field-level differences between two versions of one slum's RIM factsheet.

Pure: it compares two contexts `map_rim_data` has already built, so it makes no
database or network calls of its own.
"""

from collections import OrderedDict

from reports.services.rim_factsheet import RIM_FIELD_DISPLAY_NAMES

NOTHING = "NA"
SLOTS = ("map", "photo1", "photo2")


def image_slots(fields):
    """A section's picture keys: the map, always first, and the two photos."""
    keys = list(fields)
    if not keys:
        return set()
    slots = {keys[0]}
    slots.update(
        key for key in keys
        if "_bottom1" in key or "Photo1" in key or "_bottom2" in key or "Photo2" in key
    )
    return slots


def slot_keys(keys, displays=None):
    """(map, photo1, photo2) picked out of a section's keys, by position and name.

    The map is always the first slot. `displays` lets a raw key be chosen by the
    display name it maps to, which is how the stored appraisal columns are found.
    """
    if not keys:
        return (None, None, None)
    names = displays or {key: key for key in keys}

    def find(*marks):
        return next(
            (key for key in keys if any(mark in str(names.get(key, key)) for mark in marks)),
            None,
        )

    return keys[0], find("_bottom1", "Photo1"), find("_bottom2", "Photo2")


def displayed_images(section):
    """The signed URLs a section shows, per slot."""
    fields = section.get("fields") or OrderedDict()
    keys = list(fields)
    return {
        slot: (fields.get(key) if key else None)
        for slot, key in zip(SLOTS, slot_keys(keys))
    }


def stored_images(section_name, raw):
    """The stored picture paths behind a section, per slot.

    The displayed URL is signed afresh on every fetch, so it says nothing about
    whether the picture changed; the appraisal column behind it does.
    """
    fields = RIM_FIELD_DISPLAY_NAMES.get("sections", {}).get(section_name, {})
    keys = list(fields)
    return {
        slot: ((raw or {}).get(key) if key else None)
        for slot, key in zip(SLOTS, slot_keys(keys, fields))
    }


def compare_images(section_name, old_section, new_section, old_raw, new_raw):
    """Both sides' pictures per slot, marked changed only when the paths differ.

    Without the stored paths nothing is claimed to have changed: a signed URL
    differs every time and would report every picture as new.
    """
    shown_old = displayed_images(old_section)
    shown_new = displayed_images(new_section)
    kept_old = stored_images(section_name, old_raw)
    kept_new = stored_images(section_name, new_raw)

    images, changed = OrderedDict(), 0
    for slot in SLOTS:
        before, after = shown_old.get(slot), shown_new.get(slot)
        if not before and not after:
            continue
        known = old_raw is not None and new_raw is not None
        moved = bool(known and str(kept_old.get(slot) or "") != str(kept_new.get(slot) or ""))
        images[slot] = {"old": before, "new": after, "changed": moved}
        changed += 1 if moved else 0
    return images, changed


def comparable(section):
    """The section's text fields, without the picture slots."""
    fields = section.get("fields") or OrderedDict()
    skip = image_slots(fields)
    return OrderedDict((key, value) for key, value in fields.items() if key not in skip)


def compare(old, new, old_raw=None, new_raw=None):
    """The whole factsheet with each answer marked changed or not, or None.

    Keeps every section and every text field so the result reads like the
    factsheet itself -- a page per section, every question listed -- with the
    answers that moved marked for highlighting. `count` is how many moved, and
    the whole result is None when nothing did.

    `old_raw` / `new_raw` are the two appraisal rows as stored, used to tell
    whether a picture actually changed.
    """
    if not old or not new:
        return None

    old_sections = old.get("sections") or OrderedDict()
    new_sections = new.get("sections") or OrderedDict()
    names = list(new_sections) + [n for n in old_sections if n not in new_sections]

    sections, count = OrderedDict(), 0
    for name in names:
        before = comparable(old_sections.get(name) or {})
        after = comparable(new_sections.get(name) or {})
        labels = list(after) + [label for label in before if label not in after]

        fields, moved = OrderedDict(), 0
        for label in labels:
            was, now = before.get(label, NOTHING), after.get(label, NOTHING)
            changed = was != now
            fields[label] = {"old": was, "new": now, "changed": changed}
            moved += 1 if changed else 0

        images, moved_images = compare_images(
            name, old_sections.get(name) or {}, new_sections.get(name) or {}, old_raw, new_raw,
        )
        moved += moved_images

        # The page layout needs the newer version's map/photo flags.
        source = new_sections.get(name) or old_sections.get(name) or {}
        sections[name] = {
            "fields": fields,
            "images": images,
            "meta": source.get("meta") or {},
            "changed": moved,
        }
        count += moved

    if not count:
        return None
    return {"sections": sections, "count": count}
