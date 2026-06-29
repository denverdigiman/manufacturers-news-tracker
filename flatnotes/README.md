# flatnotes — directory structure fork

This is a fork of [flatnotes](https://github.com/dullage/flatnotes) that adds support for **nested directory structures** in the notes storage path.

## What's new

### Left-hand directory tree sidebar
When viewing or editing a note, a collapsible file-tree sidebar appears on the left showing all folders and notes inside `FLATNOTES_PATH`. Clicking a folder expands it; clicking a note navigates to it. The currently open note is highlighted.

### Sub-directory note storage
Notes can now live in sub-directories inside `FLATNOTES_PATH`. The note *title* becomes its relative path (e.g. `projects/2024/my-note`), which maps to `$FLATNOTES_PATH/projects/2024/my-note.md`.

- Creating a note with a `/`-separated title automatically creates the intermediate directories.
- Renaming a note to a different path moves the file (and creates directories as needed).
- Deleting a note removes empty parent directories automatically.
- Full-text search works across all sub-directories.

### New API endpoint
`GET /api/tree` — returns the directory tree as a nested JSON structure:

```json
[
  {
    "name": "projects",
    "path": "projects",
    "type": "folder",
    "children": [
      {
        "name": "my-note",
        "path": "projects/my-note",
        "type": "file",
        "children": null
      }
    ]
  },
  {
    "name": "quick-idea",
    "path": "quick-idea",
    "type": "file",
    "children": null
  }
]
```

## Changed files

| File | Change |
|------|--------|
| `server/main.py` | Added `GET /api/tree`; changed `{title}` path params to `{title:path}` to allow slashes |
| `server/notes/base.py` | Added abstract `get_tree()` method |
| `server/notes/models.py` | Added `TreeNode` model |
| `server/notes/file_system/file_system.py` | Recursive note discovery; `_path_from_title` supports sub-paths; `create`/`update`/`delete` handle directories; `get_tree()` implementation |
| `server/helpers.py` | `is_valid_filename` now allows `/` but blocks `..` path traversal |
| `client/App.vue` | Two-column layout with sidebar; tree loaded from API |
| `client/partials/NavBar.vue` | "New Note" button hidden when sidebar is visible (button moved into sidebar) |
| `client/components/DirectoryTree.vue` | New component — renders tree root |
| `client/components/TreeNodeItem.vue` | New component — recursive tree node (folder/file) |
| `client/api.js` | Added `getTree()` |
| `client/router.js` | Note route uses `/:title(.*)+` to capture path segments |

## Running

Same as upstream flatnotes — see the [original README](https://github.com/dullage/flatnotes).

```bash
# Docker example
docker run -d \
  -e "FLATNOTES_AUTH_TYPE=none" \
  -v "/path/to/notes:/data" \
  -p "8080:8080" \
  <this-image>
```

Notes stored at the root of `FLATNOTES_PATH` continue to work exactly as before. Sub-directories are opt-in — just create a note with a `/`-separated title or place `.md` files in sub-folders manually.
