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
    search = search.strip()

    # Normalize the folder scope
    folder_scope = os.path.expanduser(folder_scope)
    if not os.path.isabs(folder_scope):
        folder_scope = os.path.join(os.getcwd(), folder_scope)
    folder_scope = os.path.normpath(folder_scope)

    # Find the deepest existing directory that exactly matches the search path
    search_crumbs = os.path.split(search)
    search_from = folder_scope
    consumed_crumbs: list[str] = []
    for crumb in search_crumbs:
        sub_path = os.path.join(search_from, crumb)
        if os.path.isdir(sub_path):
            search_from = sub_path
            consumed_crumbs.append(crumb)
        else:
            break
    # Consume the crumbs that matched exactly
    # (Could do this in the same loop, with a different type of loop, alternatively)
    search_crumbs = search_crumbs[len(consumed_crumbs):]

    # Walk the directory and find matching names
    # TODO: fuzzier matching, e.g. using difflib.get_close_matches or similar
    # TODO: sort completions by relevance, e.g. by length of the match, how many crumbs match, how in order the matches are
    completions: list[Completion] = []
    steps = 0
    for root, dirs, _files in os.walk(search_from):
        steps += 1
        if steps > MAX_ITERATIONS or len(completions) > MAX_COMPLETIONS:
            break
        for name in sorted(dirs):
            suggestion = os.path.join(root, name)

            match_highlights: list[tuple[int, int]] = []
            if search_crumbs:
                suggestion_lower = suggestion.lower()
                for crumb in search_crumbs:
                    crumb_lower = crumb.lower()
                    start = suggestion_lower.find(crumb_lower)
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

    return completions[:MAX_COMPLETIONS]
