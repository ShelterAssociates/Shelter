"""The standard concept dictionary: stable text keys shared by every provider.

A key is slugged once from the name a concept was first seen with and never
regenerated, so reports keep working when a provider renames a question. Each
provider's own id and spelling live in ConceptAlias, which is how a future tool
maps its questions onto the keys that already exist.
"""

import logging
import re

from survey.models import Concept, ConceptAlias

logger = logging.getLogger(__name__)

MAX_KEY_LENGTH = 120
FALLBACK_KEY = "concept"
NON_WORD = re.compile(r"[^a-z0-9]+")


def slugify_key(name):
    """'Current place of defecation?' -> 'current_place_of_defecation'. Non-ASCII -> ''."""
    if not name:
        return ""
    try:
        ascii_name = str(name).encode("ascii", "ignore").decode("ascii")
    except Exception:
        return ""
    slug = NON_WORD.sub("_", ascii_name.lower()).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug[:MAX_KEY_LENGTH].strip("_")


def unique_key(name, taken=None):
    """A free key for `name`; collisions get _2, _3, ... and blank slugs concept_1."""
    taken = taken if taken is not None else set()
    base = slugify_key(name)
    if base and is_free(base, taken):
        return base
    return numbered(base or FALLBACK_KEY, taken, start=2 if base else 1)


def is_free(key, taken):
    return key not in taken and not Concept.objects.filter(key=key).exists()


def numbered(base, taken, start=2):
    index = start
    while True:
        suffix = "_{}".format(index)
        candidate = base[:MAX_KEY_LENGTH - len(suffix)] + suffix
        if is_free(candidate, taken):
            return candidate
        index += 1


class ConceptCache(object):
    """Per-run memo so one sync resolves each provider concept once."""

    def __init__(self):
        self.by_id = {}
        self.by_name = {}
        self.claimed_keys = set()

    def get(self, provider, external_id, name):
        if external_id and (provider, external_id) in self.by_id:
            return self.by_id[(provider, external_id)]
        if name and (provider, name) in self.by_name:
            return self.by_name[(provider, name)]
        return None

    def put(self, provider, external_id, name, concept):
        if external_id:
            self.by_id[(provider, external_id)] = concept
        if name:
            self.by_name[(provider, name)] = concept
        self.claimed_keys.add(concept.key)


def resolve(ref, provider_key, role="question", source="observed", cache=None, create=True):
    """ConceptRef -> Concept, creating the concept and its alias on first sighting."""
    external_id = (ref.external_id or "").strip()
    name = (ref.name or "").strip()
    if not external_id and not name:
        return None
    if cache is not None:
        hit = cache.get(provider_key, external_id, name)
        if hit is not None:
            return hit

    alias = find_alias(provider_key, external_id, name)
    if alias is None and name:
        concept = Concept.objects.filter(name=name).first()
        if concept is not None:
            alias = ConceptAlias.objects.create(
                concept=concept, provider=provider_key, external_id=external_id, external_name=name
            )
    if alias is None:
        if not create:
            return None
        alias = create_concept(provider_key, external_id, name, ref.data_type, role, source, cache)

    concept = alias.concept
    update_concept(concept, name, ref.data_type, role, source)
    update_alias(alias, external_id, name)
    if cache is not None:
        cache.put(provider_key, external_id, name, concept)
    return concept


def find_alias(provider_key, external_id, name):
    alias = None
    if external_id:
        alias = ConceptAlias.objects.filter(provider=provider_key, external_id=external_id).select_related("concept").first()
    if alias is None and name:
        alias = ConceptAlias.objects.filter(provider=provider_key, external_name=name).select_related("concept").first()
    return alias


def create_concept(provider_key, external_id, name, data_type, role, source, cache):
    taken = cache.claimed_keys if cache is not None else set()
    concept = Concept.objects.create(
        key=unique_key(name, taken),
        name=name,
        data_type=concept_data_type(data_type, role),
        is_question=role == "question",
        is_answer=role == "answer",
        sa_text=name,
        source=source,
    )
    return ConceptAlias.objects.create(
        concept=concept, provider=provider_key, external_id=external_id, external_name=name
    )


def concept_data_type(data_type, role):
    if role == "answer":
        return "answer"
    return data_type or "unknown"


def update_concept(concept, name, data_type, role, source):
    """OR in the role, fill a placeholder's name/key, follow a rename, upgrade the source."""
    changed = []
    if role == "question" and not concept.is_question:
        concept.is_question = True
        changed.append("is_question")
    if role == "answer" and not concept.is_answer:
        concept.is_answer = True
        changed.append("is_answer")

    wanted_type = concept_data_type(data_type, role)
    if wanted_type != "unknown" and concept.data_type in ("unknown", ""):
        concept.data_type = wanted_type
        changed.append("data_type")
    if source == "catalog" and concept.source != "catalog":
        concept.source = "catalog"
        changed.append("source")

    if name and name != concept.name:
        if not concept.name:
            concept.key = unique_key(name)
            changed.append("key")
        elif concept.sa_text == concept.name:
            concept.sa_text = name
            changed.append("sa_text")
        concept.name = name
        changed.append("name")
    if not concept.sa_text and concept.name:
        concept.sa_text = concept.name
        changed.append("sa_text")
    if changed:
        concept.save(update_fields=sorted(set(changed)))


def update_alias(alias, external_id, name):
    changed = []
    if external_id and alias.external_id != external_id:
        alias.external_id = external_id
        changed.append("external_id")
    if name and alias.external_name != name:
        alias.external_name = name
        changed.append("external_name")
    if changed:
        alias.save(update_fields=changed)


def upsert_catalog(entries, provider_key):
    """Claim a clean key for every question and answer the provider's forms define."""
    cache = ConceptCache()
    counts = {"forms": 0, "questions": 0, "answers": 0}
    for entry in entries:
        counts["forms"] += 1
        for question, answers in entry.concepts:
            if resolve(question, provider_key, role="question", source="catalog", cache=cache) is not None:
                counts["questions"] += 1
            for answer in answers or ():
                if resolve(answer, provider_key, role="answer", source="catalog", cache=cache) is not None:
                    counts["answers"] += 1
    return counts
