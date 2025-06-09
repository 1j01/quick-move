"""Fuzzy file path autocompletion"""

# from enum import Enum
from dataclasses import dataclass
import os
from pathlib import Path

# class ResultType(Enum):
#     FILE = "file"
#     DIRECTORY = "directory"
#     SYMLINK = "symlink"
#     OTHER = "other"

@dataclass
class Completion:
    path: Path
    display_text: str
    match_highlights: list[tuple[int, int]]
    will_create_directory: bool
    ai_suggested: bool

def get_completions(search: str, folder_scope: str = "/") -> list[Completion]:
    """Get file path completions based on the search input and folder scope."""
    # TODO: handle relative vs absolute paths (QCompleter only does a prefix match)
    # TODO: fuzzy matching
    # TODO: probably loop to find the deepest existing directory instead of only checking the parent

    search = search.strip()
    # if not search:
    #     self.model.setStringList([])
    #     return

    # Normalize the path
    search = os.path.expanduser(search)
    if not os.path.isabs(search):
        search = os.path.join(folder_scope, search)
    search = os.path.normpath(search)

    suggestions: list[str] = []

    # If the path is a directory, list its contents
    if os.path.isdir(search):
        suggestions = sorted(os.listdir(search))
    else:
        # If the path is not a directory, suggest the parent directory's contents
        parent_dir = os.path.dirname(search)
        if os.path.isdir(parent_dir):
            suggestions = sorted(os.listdir(parent_dir))
        else:
            suggestions = []

    return [
        Completion(
            path=Path(suggestion),
            display_text=suggestion,
            match_highlights=[],
            will_create_directory=False,
            ai_suggested=False,
        )
        for suggestion in suggestions
    ]
