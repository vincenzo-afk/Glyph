from indexer import tokenize
from retrieve import entities, retrieve


def make_chunk(file, text, idx=0):
    return {"file": file, "idx": idx, "text": text, "tokens": tokenize(text), "stale": False}


def test_entities_finds_ticket_ids_and_versions():
    assert entities("fixed in ORR-1847 and TQ-40 build") == {"ORR-1847", "TQ-40"}
    assert entities("plain words only") == set()


def test_query_without_tokens_retrieves_nothing(cfg):
    chunks = [make_chunk("a.txt", "limit 94")]
    assert retrieve(chunks, "???", cfg) == []


def test_unrelated_query_retrieves_nothing(cfg):
    chunks = [make_chunk("a.txt", "limit 94")]
    assert retrieve(chunks, "banana", cfg) == []


def test_best_match_ranks_first(cfg):
    chunks = [make_chunk("fan.xlsx", "fan assembly part number"),
              make_chunk("temp.pdf", "maximum junction temperature 94")]
    top = retrieve(chunks, "junction temperature", cfg)
    assert top[0]["file"] == "temp.pdf"


def test_hop_follows_ticket_into_another_file(cfg):
    log = make_chunk("log.txt", "incident logged against ORR-1847", idx=0)
    bugs = make_chunk("bugs.csv", "ORR-1847,4.3.2,closed", idx=0)
    top = retrieve([log, bugs], "which thermal incident happened", cfg)
    assert {c["file"] for c in top} == {"log.txt", "bugs.csv"}


def test_identifier_in_query_is_not_followed_as_a_hop(cfg):
    # Both chunks match the query terms directly, so both are returned, and the
    # hop must not add anything beyond them.
    log = make_chunk("log.txt", "incident logged against ORR-1847", idx=0)
    bugs = make_chunk("bugs.csv", "ORR-1847,4.3.2,closed", idx=0)
    other = make_chunk("other.txt", "notes for 4.3.2 unrelated to tickets", idx=0)
    top = retrieve([log, bugs, other], "which release fixed ORR-1847", cfg)
    assert {c["file"] for c in top} == {"log.txt", "bugs.csv"}
