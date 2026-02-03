from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
    QSizePolicy,
    QStyledItemDelegate,
    QLineEdit,
    QCompleter,
    QHeaderView,
    QStyleOptionViewItem,
)

from src.domain.normalize import expand_child_code


@dataclass
class LookupResult:
    name: str
    locked: bool = False


# Providers now accept optional parent_code (backwards compatible at runtime).
SuggestFn = Callable[..., List[str]]
LookupFn = Callable[..., Optional[LookupResult]]
ChangeFn = Callable[[int, str, str], None]


ROLE_LEVEL = Qt.UserRole
ROLE_LOCKED = Qt.UserRole + 1
ROLE_CANON_NAME = Qt.UserRole + 2


class HierarchyItemDelegate(QStyledItemDelegate):
    """
    Delegate for QTreeWidget editing:
    - Autocomplete dropdown for Code/Name (live as you type)
    - Enforces lock: when locked, Name column is not editable
    - Ensures editor geometry uses the full cell rect (prevents “chewed” typing)
    """

    def __init__(self, owner: "HierarchyEditor") -> None:
        super().__init__(owner)
        self.owner = owner

    def createEditor(self, parent, option, index):
        if not index.isValid():
            return None

        col = index.column()

        # SAFE: QTreeWidget must use itemFromIndex (internalPointer can crash in PySide)
        item = self.owner.tree.itemFromIndex(index)
        if item is None:
            item = self.owner.tree.currentItem()
        if item is None:
            return None

        locked = bool(item.data(0, ROLE_LOCKED) or False)

        # True lock: block Name editing (column 1)
        if locked and col == self.owner.COL_NAME:
            return None

        # Only Code/Name are editable
        if col not in (self.owner.COL_CODE, self.owner.COL_NAME):
            return None

        ed = QLineEdit(parent)
        ed.setClearButtonEnabled(True)
        ed.setMinimumHeight(28)
        ed.setStyleSheet("padding-left: 6px; padding-right: 6px;")

        comp = QCompleter(ed)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchContains)
        comp.setCompletionMode(QCompleter.PopupCompletion)

        model = QStringListModel(ed)
        comp.setModel(model)
        ed.setCompleter(comp)

        # Strong refs (avoid GC + silent crashes)
        ed._ac_model = model  # type: ignore[attr-defined]
        ed._ac_comp = comp    # type: ignore[attr-defined]

        def refresh(prefix: str) -> None:
            level = self.owner._depth_of(item)
            parent_code = ""
            try:
                p = item.parent()
                if p is not None:
                    parent_code = (p.text(self.owner.COL_CODE) or "").strip()
            except Exception:
                parent_code = ""

            try:
                if col == self.owner.COL_CODE and self.owner._suggest_codes is not None:
                    try:
                        items = self.owner._suggest_codes(level, prefix or "", parent_code)
                    except TypeError:
                        items = self.owner._suggest_codes(level, prefix or "")
                elif col == self.owner.COL_NAME and self.owner._suggest_names is not None:
                    try:
                        items = self.owner._suggest_names(level, prefix or "", parent_code)
                    except TypeError:
                        items = self.owner._suggest_names(level, prefix or "")
                else:
                    items = []
            except Exception:
                items = []

            model.setStringList((items or [])[:200])

        ed.textEdited.connect(refresh)

        try:
            refresh(item.text(col) or "")
        except Exception:
            refresh("")

        return ed

    def updateEditorGeometry(self, editor, option: QStyleOptionViewItem, index) -> None:
        if editor is not None:
            editor.setGeometry(option.rect)
        else:
            super().updateEditorGeometry(editor, option, index)

    def setEditorData(self, editor, index):
        if isinstance(editor, QLineEdit):
            editor.setText(index.data(Qt.EditRole) or "")
            editor.selectAll()
            return
        super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QLineEdit):
            model.setData(index, editor.text(), Qt.EditRole)
            return
        super().setModelData(editor, model, index)


class HierarchyEditor(QWidget):
    """
    Tree-first hierarchy editor (Levels 1..4).
    - Semantic buttons ("Add Level 3", etc.)
    - Autocomplete in Code/Name cells
    - Rules-mode “lazy typing”:
        * Level 1: pads digits (1 -> 01) based on rules
        * Level 2+: expands suffix by parent (2 -> 01.2)
    """

    COL_CODE = 0
    COL_NAME = 1

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._level_names: List[str] = ["Level 1", "Level 2", "Level 3", "Level 4"]

        self._suggest_codes: Optional[SuggestFn] = None
        self._suggest_names: Optional[SuggestFn] = None
        self._lookup: Optional[LookupFn] = None
        self._on_change: Optional[ChangeFn] = None

        # Rules normalization (set by LabelEditorView in Rules Mode)
        self._code_delimiter: str = "."
        self._pad_level1: int = 2

        self._building = False

        self._build_ui()
        self._wire()

        self.tree.setItemDelegate(HierarchyItemDelegate(self))

        self.add_level1()

    # ---------------- Public API ----------------
    def set_level_names(self, level1: str, level2: str, level3: str = "Level 3", level4: str = "Level 4") -> None:
        self._level_names = [level1, level2, level3, level4]
        self._update_buttons()

    def set_providers(self, suggest_codes: Optional[SuggestFn], suggest_names: Optional[SuggestFn], lookup: Optional[LookupFn]) -> None:
        self._suggest_codes = suggest_codes
        self._suggest_names = suggest_names
        self._lookup = lookup

    def set_on_change(self, cb: Optional[ChangeFn]) -> None:
        self._on_change = cb

    def set_rules_normalization(self, delimiter: str, pad_level1: int) -> None:
        d = (delimiter or ".").strip()
        if len(d) != 1:
            d = "."
        self._code_delimiter = d
        try:
            p = int(pad_level1)
        except Exception:
            p = 2
        self._pad_level1 = max(1, min(p, 6))

    def clear(self) -> None:
        self._building = True
        self.tree.clear()
        self._building = False
        self.add_level1()

    def export_entries(self) -> List[Dict[str, Any]]:
        def walk(item: QTreeWidgetItem, level: int) -> Dict[str, Any]:
            node = {
                "level": level,
                "code": (item.text(self.COL_CODE) or "").strip(),
                "name": (item.text(self.COL_NAME) or "").strip(),
                "children": [],
            }
            for i in range(item.childCount()):
                node["children"].append(walk(item.child(i), level + 1))
            return node

        roots = []
        for i in range(self.tree.topLevelItemCount()):
            roots.append(walk(self.tree.topLevelItem(i), 1))
        return roots

    # ---------------- Buttons ----------------
    def add_level1(self) -> None:
        it = self._make_item(level=1)
        self.tree.addTopLevelItem(it)
        self.tree.setCurrentItem(it)
        self.tree.editItem(it, self.COL_CODE)
        self._update_buttons()

    def add_child(self) -> None:
        sel = self._selected_item()
        if sel is None:
            self.add_level1()
            return
        level = self._depth_of(sel)
        if level >= 4:
            self._warn("Max depth", "You cannot add deeper than Level 4.")
            return
        child = self._make_item(level=level + 1)
        sel.addChild(child)
        sel.setExpanded(True)
        self.tree.setCurrentItem(child)
        self.tree.editItem(child, self.COL_CODE)
        self._update_buttons()

    def add_sibling(self) -> None:
        sel = self._selected_item()
        if sel is None:
            self.add_level1()
            return
        parent = sel.parent()
        level = self._depth_of(sel)
        sib = self._make_item(level=level)
        if parent is None:
            self.tree.addTopLevelItem(sib)
        else:
            parent.addChild(sib)
            parent.setExpanded(True)
        self.tree.setCurrentItem(sib)
        self.tree.editItem(sib, self.COL_CODE)
        self._update_buttons()

    def remove_selected(self) -> None:
        sel = self._selected_item()
        if sel is None:
            return

        parent = sel.parent()
        if parent is None:
            idx = self.tree.indexOfTopLevelItem(sel)
            self.tree.takeTopLevelItem(idx)
        else:
            parent.removeChild(sel)

        if self.tree.topLevelItemCount() == 0:
            self.add_level1()

        self._update_buttons()

    # ---------------- Internals ----------------
    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        bar = QHBoxLayout()
        bar.setSpacing(8)

        self.btn_add_child = QPushButton("Add Level 2")
        self.btn_add_sibling = QPushButton("Add Level 1")
        self.btn_remove = QPushButton("Remove")

        self.btn_add_child.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_add_sibling.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_remove.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        bar.addWidget(self.btn_add_child, 0)
        bar.addWidget(self.btn_add_sibling, 0)
        bar.addStretch(1)
        bar.addWidget(self.btn_remove, 0)

        lay.addLayout(bar, 0)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Code", "Name"])
        self.tree.setUniformRowHeights(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setExpandsOnDoubleClick(True)
        self.tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Avoid "..." eliding
        self.tree.setTextElideMode(Qt.ElideNone)

        # Indentation matters for usable width
        self.tree.setIndentation(18)

        hdr = self.tree.header()
        hdr.setStretchLastSection(True)
        hdr.setMinimumSectionSize(160)
        hdr.setSectionResizeMode(0, QHeaderView.Interactive)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)

        self.tree.setColumnWidth(0, 220)

        lay.addWidget(self.tree, 1)

    def _wire(self) -> None:
        self.btn_add_child.clicked.connect(self.add_child)
        self.btn_add_sibling.clicked.connect(self.add_sibling)
        self.btn_remove.clicked.connect(self.remove_selected)

        self.tree.currentItemChanged.connect(lambda _a, _b: self._update_buttons())
        self.tree.itemChanged.connect(self._on_item_changed)

    def _level_name(self, level: int) -> str:
        if 1 <= level <= len(self._level_names):
            return self._level_names[level - 1]
        return f"Level {level}"

    def _update_buttons(self) -> None:
        sel = self._selected_item()
        if sel is None:
            self.btn_add_child.setText(f"Add {self._level_name(1)}")
            self.btn_add_sibling.setText(f"Add {self._level_name(1)}")
            self.btn_add_child.setEnabled(True)
            self.btn_add_sibling.setEnabled(True)
            return

        depth = self._depth_of(sel)
        next_level = min(depth + 1, 4)

        self.btn_add_child.setText(f"Add {self._level_name(next_level)}")
        self.btn_add_sibling.setText(f"Add {self._level_name(depth)}")

        self.btn_add_child.setEnabled(depth < 4)
        self.btn_add_sibling.setEnabled(True)

    def _make_item(self, level: int) -> QTreeWidgetItem:
        it = QTreeWidgetItem(["", ""])
        it.setData(0, ROLE_LEVEL, level)
        it.setData(0, ROLE_LOCKED, False)
        it.setData(0, ROLE_CANON_NAME, "")
        it.setFlags(it.flags() | Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        return it

    def _selected_item(self) -> Optional[QTreeWidgetItem]:
        return self.tree.currentItem()

    def _depth_of(self, item: QTreeWidgetItem) -> int:
        d = 1
        p = item.parent()
        while p is not None:
            d += 1
            p = p.parent()
        return d

    def _warn(self, title: str, msg: str) -> None:
        QMessageBox.information(self, title, msg)

    def _set_locked(self, item: QTreeWidgetItem, locked: bool, canonical_name: str = "") -> None:
        item.setData(0, ROLE_LOCKED, bool(locked))
        item.setData(0, ROLE_CANON_NAME, str(canonical_name or ""))

    def _normalize_code_for_item(self, item: QTreeWidgetItem, raw_code: str) -> str:
        code = (raw_code or "").strip()
        if not code:
            return code

        level = self._depth_of(item)

        if level == 1:
            if code.isdigit():
                return str(int(code)).zfill(self._pad_level1)
            return code

        # Level 2+ : expand suffix using parent
        parent = item.parent()
        parent_code = ""
        if parent is not None:
            parent_code = (parent.text(self.COL_CODE) or "").strip()

        return expand_child_code(parent_code, code, self._code_delimiter)

    def _on_item_changed(self, item: QTreeWidgetItem, col: int) -> None:
        if self._building:
            return

        level = self._depth_of(item)
        code = (item.text(self.COL_CODE) or "").strip()
        name = (item.text(self.COL_NAME) or "").strip()

        locked = bool(item.data(0, ROLE_LOCKED) or False)

        # If locked and user tried to change Name, revert immediately
        if col == self.COL_NAME and locked:
            canon = str(item.data(0, ROLE_CANON_NAME) or "")
            if canon and name != canon:
                self._building = True
                item.setText(self.COL_NAME, canon)
                self._building = False

            if self._on_change is not None:
                try:
                    self._on_change(level, code, canon or name)
                except Exception:
                    pass
            return

        # Code edits: normalize + lookup
        if col == self.COL_CODE:
            norm = self._normalize_code_for_item(item, code)
            if norm != code:
                self._building = True
                item.setText(self.COL_CODE, norm)
                self._building = False
                code = norm

            if not code:
                self._building = True
                self._set_locked(item, False, "")
                self._building = False
            elif self._lookup is not None:
                # pass parent_code to lookup when possible
                parent_code = ""
                try:
                    p = item.parent()
                    if p is not None:
                        parent_code = (p.text(self.COL_CODE) or "").strip()
                except Exception:
                    parent_code = ""

                try:
                    try:
                        res = self._lookup(level, code, parent_code)
                    except TypeError:
                        res = self._lookup(level, code)
                except Exception:
                    res = None

                if res is not None and res.name:
                    self._building = True
                    item.setText(self.COL_NAME, res.name)
                    self._set_locked(item, bool(res.locked), res.name if res.locked else "")
                    self._building = False

        # Remember callback
        if self._on_change is not None:
            try:
                self._on_change(level, code, (item.text(self.COL_NAME) or "").strip())
            except Exception:
                pass

