"""Fuzzy file path autocompletion"""

from dataclasses import dataclass
import os
from pathlib import Path

@dataclass
class Completion:
    path: Path
    display_text: str
    match_highlights: list[tuple[int, int]]
    will_create_directory: bool
    ai_suggested: bool

# This prevents the program from hanging when searching large directories, e.g. the root directory.
# Since os.walk uses breadth-first search by default, it still gives good results, as nearby directories are searched first.
# That said, there may be pathological cases where it will not find even fairly shallow matches.
# I haven't explored this in "depth" (haha) yet.
MAX_ITERATIONS = 1000
MAX_COMPLETIONS = 100

def get_completions(search: str, folder_scope: str = "/") -> list[Completion]:
    """Get file path completions based on the search input and folder scope."""
    # Normalize the search input
    # Not sure this is a good idea. A space could disambiguate a search for "Foo Bar" compared to "Foo", when you've typed "foo" so far.
    search = search.strip()

    # Normalize the folder scope
    folder_scope = os.path.expanduser(folder_scope)
    if not os.path.isabs(folder_scope):
        folder_scope = os.path.join(os.getcwd(), folder_scope)
    folder_scope = os.path.normpath(folder_scope)

    # Find the deepest existing directory that exactly matches the search path
    search_from = folder_scope
    search_crumbs = Path(search).parts
    consumed_crumbs: list[str] = []
    for crumb in search_crumbs:
        sub_path = os.path.join(search_from, crumb)
        # print(f"Checking sub_path: {sub_path}, exists: {os.path.exists(sub_path)}, isdir: {os.path.isdir(sub_path)}")
        if os.path.isdir(sub_path):
            search_from = sub_path
            consumed_crumbs.append(crumb)
        else:
            break
    # Consume the crumbs that matched exactly
    # (Could do this in the same loop, with a different type of loop, alternatively)
    search_crumbs = search_crumbs[len(consumed_crumbs):]
    # print(f"Searching from: {search_from} with crumbs: {search_crumbs}")

    consumed_path = search_from
    if not search.startswith(consumed_path):
        print(f"Warning: search '{search}' does not start with consumed path '{consumed_path}'. This may lead to unexpected results.")
        print(f"consumed_path: {consumed_path}")
        print(f"folder_scope: {folder_scope}")
        print(f"search_from: {search_from}")
        print(f"search: {search}")


    # Walk the directory and find matching names
    # TODO: fuzzier matching, e.g. using difflib.get_close_matches or similar
    completions: list[Completion] = []
    steps = 0
    for root, dirs, _files in os.walk(search_from):
        steps += 1
        if steps > MAX_ITERATIONS or len(completions) > MAX_COMPLETIONS:
            break
        # Sorting here is not strictly necessary since matches are sorted later,
        # but it may help with determinism in case MAX_COMPLETIONS or MAX_ITERATIONS is reached.
        for name in sorted(dirs):
            suggestion = os.path.join(root, name)

            match_highlights: list[tuple[int, int]] = []
            if search_crumbs:
                suggestion_lower = suggestion.lower()
                for crumb in search_crumbs:
                    crumb_lower = crumb.lower()
                    start = suggestion_lower.find(crumb_lower, len(consumed_path))
                    if start != -1:
                        match_highlights.append((start, start + len(crumb)))

            if match_highlights or not search_crumbs:
                completions.append(
                    Completion(
                        path=Path(suggestion),
                        display_text=suggestion,
                        match_highlights=match_highlights,
                        will_create_directory=False,
                        ai_suggested=False,
                    )
                )

    # sort completions by relevance, e.g. by length of the match, how many crumbs match (or maybe how many characters would be better), how in order the matches are
    # TODO: prioritize matches that fit word boundaries, e.g. "bar" should match "foo/bar" before "foobar", and "foobar" before "foobarbaz"
    # (and consider lowercase-to-uppercase letter pairs as word boundaries, for camelCase)
    completions.sort(key=lambda c: (
        # prioritize longer matches (total matched characters)
        -sum(end - start for start, end in c.match_highlights),
        # prioritize FEWER separate matches, which means larger contiguous matches are prioritized (in conjunction with the previous rule)
        len(c.match_highlights),
        # prioritize ordered match sets (by counting how many pairs are in order)
        -sum(1 for i in range(len(c.match_highlights) - 1) if c.match_highlights[i][1] <= c.match_highlights[i + 1][0]),
        # fallback to alphabetical order
        c.display_text
    ))

    return completions[:MAX_COMPLETIONS]
