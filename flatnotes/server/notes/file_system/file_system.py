import glob
import os
import re
import shutil
import time
from datetime import datetime
from typing import Dict, List, Literal, Set, Tuple

import whoosh
from whoosh import writing
from whoosh.analysis import CharsetFilter, StemmingAnalyzer
from whoosh.fields import DATETIME, ID, KEYWORD, TEXT, SchemaClass
from whoosh.highlight import ContextFragmenter, WholeFragmenter
from whoosh.index import Index, LockError
from whoosh.qparser import MultifieldParser
from whoosh.qparser.dateparse import DateParserPlugin
from whoosh.query import Every
from whoosh.searching import Hit
from whoosh.support.charset import accent_map

from helpers import get_env, is_valid_filename
from logger import logger

from ..base import BaseNotes
from ..models import Note, NoteCreate, NoteUpdate, SearchResult, TreeNode

MARKDOWN_EXT = ".md"
INDEX_SCHEMA_VERSION = "5"

StemmingFoldingAnalyzer = StemmingAnalyzer() | CharsetFilter(accent_map)


class IndexSchema(SchemaClass):
    filename = ID(unique=True, stored=True)
    last_modified = DATETIME(stored=True, sortable=True)
    title = TEXT(
        field_boost=2.0, analyzer=StemmingFoldingAnalyzer, sortable=True
    )
    content = TEXT(analyzer=StemmingFoldingAnalyzer)
    tags = KEYWORD(lowercase=True, field_boost=2.0)


class FileSystemNotes(BaseNotes):
    TAGS_RE = re.compile(r"(?:(?<=^#)|(?<=\s#))[a-zA-Z0-9_-]+(?=\s|$)")
    CODEBLOCK_RE = re.compile(r"`{1,3}.*?`{1,3}", re.DOTALL)
    TAGS_WITH_HASH_RE = re.compile(
        r"(?:(?<=^)|(?<=\s))#[a-zA-Z0-9_-]+(?=\s|$)"
    )

    def __init__(self):
        self.storage_path = get_env("FLATNOTES_PATH", mandatory=True)
        if not os.path.exists(self.storage_path):
            raise NotADirectoryError(
                f"'{self.storage_path}' is not a valid directory."
            )
        self.index = self._load_index()
        self._sync_index_with_retry(optimize=True)

    def create(self, data: NoteCreate) -> Note:
        """Create a new note."""
        filepath = self._path_from_title(data.title)
        # Create parent directories if needed
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self._write_file(filepath, data.content)
        return Note(
            title=data.title,
            content=data.content,
            last_modified=os.path.getmtime(filepath),
        )

    def get(self, title: str) -> Note:
        """Get a specific note."""
        is_valid_filename(title)
        filepath = self._path_from_title(title)
        content = self._read_file(filepath)
        return Note(
            title=title,
            content=content,
            last_modified=os.path.getmtime(filepath),
        )

    def update(self, title: str, data: NoteUpdate) -> Note:
        """Update a specific note."""
        is_valid_filename(title)
        filepath = self._path_from_title(title)
        if data.new_title is not None:
            new_filepath = self._path_from_title(data.new_title)
            if filepath != new_filepath and os.path.isfile(new_filepath):
                raise FileExistsError(
                    f"Failed to rename. '{data.new_title}' already exists."
                )
            os.makedirs(os.path.dirname(new_filepath), exist_ok=True)
            os.rename(filepath, new_filepath)
            title = data.new_title
            filepath = new_filepath
        if data.new_content is not None:
            self._write_file(filepath, data.new_content, overwrite=True)
            content = data.new_content
        else:
            content = self._read_file(filepath)
        return Note(
            title=title,
            content=content,
            last_modified=os.path.getmtime(filepath),
        )

    def delete(self, title: str) -> None:
        """Delete a specific note."""
        is_valid_filename(title)
        filepath = self._path_from_title(title)
        os.remove(filepath)
        # Remove empty parent directories (up to storage_path)
        parent = os.path.dirname(filepath)
        while parent != self.storage_path:
            try:
                os.rmdir(parent)
                parent = os.path.dirname(parent)
            except OSError:
                break

    def search(
        self,
        term: str,
        sort: Literal["score", "title", "last_modified"] = "score",
        order: Literal["asc", "desc"] = "desc",
        limit: int = None,
    ) -> Tuple[SearchResult, ...]:
        """Search the index for the given term."""
        self._sync_index_with_retry()
        term = self._pre_process_search_term(term)
        with self.index.searcher() as searcher:
            if term == "*":
                query = Every()
            else:
                parser = MultifieldParser(
                    self._fieldnames_for_term(term), self.index.schema
                )
                parser.add_plugin(DateParserPlugin())
                query = parser.parse(term)

            sort = sort if sort in ["title", "last_modified"] else None

            reverse = order == "desc"
            if sort is None:
                reverse = not reverse

            results = searcher.search(
                query,
                sortedby=sort,
                reverse=reverse,
                limit=limit,
                terms=True,
            )
            return tuple(self._search_result_from_hit(hit) for hit in results)

    def get_tags(self) -> list[str]:
        """Return a list of all indexed tags."""
        self._sync_index_with_retry()
        with self.index.reader() as reader:
            tags = reader.field_terms("tags")
            return [tag for tag in tags]

    def get_tree(self) -> List[TreeNode]:
        """Return the directory tree of notes as a nested list of TreeNodes."""
        return self._build_tree(self.storage_path, "")

    def _build_tree(self, dir_path: str, rel_prefix: str) -> List[TreeNode]:
        """Recursively build a tree of TreeNode objects for a directory."""
        nodes: List[TreeNode] = []
        try:
            entries = sorted(os.scandir(dir_path), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            return nodes

        for entry in entries:
            # Skip the whoosh index directory and hidden entries
            if entry.name.startswith("."):
                continue

            rel_path = f"{rel_prefix}/{entry.name}" if rel_prefix else entry.name

            if entry.is_dir(follow_symlinks=False):
                children = self._build_tree(entry.path, rel_path)
                nodes.append(
                    TreeNode(
                        name=entry.name,
                        path=rel_path,
                        type="folder",
                        children=children,
                    )
                )
            elif entry.is_file() and entry.name.endswith(MARKDOWN_EXT):
                note_title = rel_path[: -len(MARKDOWN_EXT)]
                nodes.append(
                    TreeNode(
                        name=entry.name[: -len(MARKDOWN_EXT)],
                        path=note_title,
                        type="file",
                        children=None,
                    )
                )

        return nodes

    @property
    def _index_path(self):
        return os.path.join(self.storage_path, ".flatnotes")

    def _path_from_title(self, title: str) -> str:
        # Normalise forward slashes and resolve to an absolute path
        rel = title.replace("\\", "/") + MARKDOWN_EXT
        full = os.path.normpath(os.path.join(self.storage_path, rel))
        # Safety check: must remain inside storage_path
        if not full.startswith(os.path.abspath(self.storage_path) + os.sep) and \
                full != os.path.abspath(self.storage_path):
            raise ValueError(f"Invalid title: path traversal detected")
        return full

    def _title_from_path(self, filepath: str) -> str:
        """Convert an absolute filepath to a note title (relative path without ext)."""
        rel = os.path.relpath(filepath, self.storage_path)
        return rel[: -len(MARKDOWN_EXT)].replace("\\", "/")

    def _get_by_filename(self, filename: str) -> Note:
        """Get a note by its relative filename (path + .md)."""
        return self.get(self._strip_ext(filename).replace("\\", "/"))

    def _load_index(self) -> Index:
        """Load the note index or create new if not exists."""
        index_dir_exists = os.path.exists(self._index_path)
        if index_dir_exists and whoosh.index.exists_in(
            self._index_path, indexname=INDEX_SCHEMA_VERSION
        ):
            logger.info("Loading existing index")
            return whoosh.index.open_dir(
                self._index_path, indexname=INDEX_SCHEMA_VERSION
            )
        else:
            if index_dir_exists:
                logger.info("Deleting outdated index")
                self._clear_dir(self._index_path)
            else:
                os.mkdir(self._index_path)
            logger.info("Creating new index")
            return whoosh.index.create_in(
                self._index_path, IndexSchema, indexname=INDEX_SCHEMA_VERSION
            )

    @classmethod
    def _extract_tags(cls, content) -> Tuple[str, Set[str]]:
        """Strip tags from the given content and return a tuple of
        (content_without_tags, tag_set)."""
        content_ex_codeblock = re.sub(cls.CODEBLOCK_RE, "", content)
        _, tags = cls._re_extract(cls.TAGS_RE, content_ex_codeblock)
        content_ex_tags, _ = cls._re_extract(cls.TAGS_RE, content)
        try:
            tags = [tag.lower() for tag in tags]
            return (content_ex_tags, set(tags))
        except IndexError:
            return (content, set())

    def _add_note_to_index(
        self, writer: writing.IndexWriter, note: Note
    ) -> None:
        """Add a Note to the index. The filename stored is the relative path
        including the .md extension (e.g. folder/note.md)."""
        content_ex_tags, tag_set = self._extract_tags(note.content)
        tag_string = " ".join(tag_set)
        writer.update_document(
            filename=note.title + MARKDOWN_EXT,
            last_modified=datetime.fromtimestamp(note.last_modified),
            title=note.title,
            content=content_ex_tags,
            tags=tag_string,
        )

    def _list_all_note_filenames(self) -> List[str]:
        """Return relative filenames (e.g. folder/note.md) for all notes."""
        pattern = os.path.join(self.storage_path, "**", "*" + MARKDOWN_EXT)
        results = []
        for filepath in glob.glob(pattern, recursive=True):
            # Skip the whoosh index directory
            if os.path.sep + ".flatnotes" + os.path.sep in filepath:
                continue
            rel = os.path.relpath(filepath, self.storage_path)
            results.append(rel.replace("\\", "/"))
        return results

    def _sync_index(self, optimize: bool = False, clean: bool = False) -> None:
        """Synchronize the index with the notes directory."""
        indexed = set()
        writer = self.index.writer()
        if clean:
            writer.mergetype = writing.CLEAR
        with self.index.searcher() as searcher:
            for idx_note in searcher.all_stored_fields():
                idx_filename = idx_note["filename"]
                idx_filepath = os.path.join(self.storage_path, idx_filename)
                if not os.path.exists(idx_filepath):
                    writer.delete_by_term("filename", idx_filename)
                    logger.info(f"'{idx_filename}' removed from index")
                elif (
                    datetime.fromtimestamp(os.path.getmtime(idx_filepath))
                    != idx_note["last_modified"]
                ):
                    logger.info(f"'{idx_filename}' updated")
                    self._add_note_to_index(
                        writer, self._get_by_filename(idx_filename)
                    )
                    indexed.add(idx_filename)
                else:
                    indexed.add(idx_filename)
        for filename in self._list_all_note_filenames():
            if filename not in indexed:
                self._add_note_to_index(
                    writer, self._get_by_filename(filename)
                )
                logger.info(f"'{filename}' added to index")
        writer.commit(optimize=optimize)
        logger.info("Index synchronized")

    def _sync_index_with_retry(
        self,
        optimize: bool = False,
        clean: bool = False,
        max_retries: int = 8,
        retry_delay: float = 0.25,
    ) -> None:
        for _ in range(max_retries):
            try:
                self._sync_index(optimize=optimize, clean=clean)
                return
            except LockError:
                logger.warning(f"Index locked, retrying in {retry_delay}s")
                time.sleep(retry_delay)
        logger.error(f"Failed to sync index after {max_retries} retries")

    @classmethod
    def _pre_process_search_term(cls, term):
        term = term.strip()
        term = re.sub(
            cls.TAGS_WITH_HASH_RE,
            lambda tag: "tags:" + tag.group(0)[1:],
            term,
        )
        return term

    @staticmethod
    def _re_extract(pattern, string) -> Tuple[str, List[str]]:
        matches = []
        text = re.sub(pattern, lambda tag: matches.append(tag.group()), string)
        return (text, matches)

    @staticmethod
    def _strip_ext(filename):
        return os.path.splitext(filename)[0]

    @staticmethod
    def _clear_dir(path):
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)

    def _search_result_from_hit(self, hit: Hit):
        matched_fields = self._get_matched_fields(hit.matched_terms())

        title = self._strip_ext(hit["filename"])
        last_modified = hit["last_modified"].timestamp()

        score = hit.score if type(hit.score) is float else None

        if "title" in matched_fields:
            hit.results.fragmenter = WholeFragmenter()
            title_highlights = hit.highlights("title", text=title)
        else:
            title_highlights = None

        if "content" in matched_fields:
            hit.results.fragmenter = ContextFragmenter()
            content = self._read_file(self._path_from_title(title))
            content_ex_tags, _ = FileSystemNotes._extract_tags(content)
            content_highlights = hit.highlights(
                "content",
                text=content_ex_tags,
            )
        else:
            content_highlights = None

        tag_matches = (
            [field[1] for field in hit.matched_terms() if field[0] == "tags"]
            if "tags" in matched_fields
            else None
        )

        return SearchResult(
            title=title,
            last_modified=last_modified,
            score=score,
            title_highlights=title_highlights,
            content_highlights=content_highlights,
            tag_matches=tag_matches,
        )

    def _fieldnames_for_term(self, term: str) -> List[str]:
        fields = ["title", "content"]
        if '"' not in term:
            fields.append("tags")
        return fields

    @staticmethod
    def _get_matched_fields(matched_terms):
        return set([matched_term[0] for matched_term in matched_terms])

    @staticmethod
    def _read_file(filepath: str):
        logger.debug(f"Reading from '{filepath}'")
        with open(filepath, "r") as f:
            content = f.read()
        return content

    @staticmethod
    def _write_file(filepath: str, content: str, overwrite: bool = False):
        logger.debug(f"Writing to '{filepath}'")
        with open(filepath, "w" if overwrite else "x") as f:
            f.write(content)
