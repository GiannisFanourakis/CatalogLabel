from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QCheckBox,
    QGroupBox,
    QFileDialog,
    QMessageBox,
    QHBoxLayout,
    QVBoxLayout,
    QFormLayout,
    QDoubleSpinBox,
    QSizePolicy,
    QDialog,
    QCompleter,
)

from reportlab.lib.pagesizes import A4, A5

from src.domain.models import LabelDocument
from src.domain.units import cm_to_pt
from src.services.cache.cache_store import load_cache, save_cache, remember, suggest
from src.services.rules.excel_loader import load_rules_xlsx
from src.services.rules.exceptions import RulesWorkbookError
from src.services.rules.engine import lookup_mapping
from src.services.rules.rules_types import RulesWorkbook, RulesProfile
from src.services.export.pdf_exporter import export_label_pdf, PdfExportOptions
from src.ui.qt.widgets.hierarchy_editor import HierarchyEditor, LookupResult
from src.ui.qt.widgets.pdf_template_dialog import PdfTemplateDialog


class LabelEditorView(QWidget):
    """
    Meta fields are scalar in CacheDB.values:
      - title (str)
      - cabinet_section (str)

    History lists live under:
      - title_history (list[str])
      - cabinet_history (list[str])
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.cache = load_cache()

        self.rules: Optional[RulesWorkbook] = None
        self.profile: Optional[RulesProfile] = None
        self.rules_path: Optional[Path] = None

        self.level_labels: Dict[int, str] = {1: "Level 1", 2: "Level 2", 3: "Level 3", 4: "Level 4"}

        # remember last chosen export settings per session
        self._last_template_id: str = "classic"
        self._last_section_title: str = ""

        self._sanitize_meta_cache()

        self._build_ui()
        self._wire()

        self._apply_mode_ui()
        self._refresh_hierarchy_providers()
        self._refresh_meta_completers()

    # ---------------- Cache helpers ----------------
    def _values(self) -> Dict[str, Any]:
        v = getattr(self.cache, "values", None)
        return v if isinstance(v, dict) else {}

    def _coerce_text(self, v: Any, default: str = "") -> str:
        try:
            if isinstance(v, list):
                for item in reversed(v):
                    s = str(item or "").strip()
                    if s:
                        return s
                return default
            if v is None:
                return default
            return str(v)
        except Exception:
            return default

    def _cache_read_text(self, key: str, default: str = "") -> str:
        vals = self._values()
        return self._coerce_text(vals.get(key, default), default=default)

    def _cache_write_text(self, key: str, value: str) -> None:
        vals = self._values()
        vals[key] = str(value or "")

    def _cache_read_list(self, key: str) -> List[str]:
        """
        Read a list[str] from CacheDB.values safely.
        If corrupted (stringified list), return [] to avoid char-iteration.
        """
        vals = self._values()
        v = vals.get(key, None)
        if isinstance(v, list):
            out: List[str] = []
            for x in v:
                s = str(x or "").strip()
                if s:
                    out.append(s)
            # unique preserve order (last wins not needed here)
            seen = set()
            uniq = []
            for s in out:
                if s not in seen:
                    seen.add(s)
                    uniq.append(s)
            return uniq
        return []

    def _sanitize_meta_cache(self) -> None:
        """
        Fix broken states where title/cabinet_section became garbage:
        - single bracket characters like "]" or "["
        - stringified lists like "['a','b']"
        - accidental list values

        Also ensures history keys are lists, not strings.
        """
        vals = self._values()

        def is_junk_scalar(s: str) -> bool:
            t = (s or "").strip()
            if t in ("[", "]", "[]", "]['", "'[", "']"):
                return True
            # common artifacts of stringified lists
            if t.startswith("[") and t.endswith("]") and ("'" in t or '"' in t or "," in t):
                return True
            return False

        # normalize meta scalars
        for key in ("title", "cabinet_section"):
            v = vals.get(key, "")
            if isinstance(v, list):
                v = self._coerce_text(v, default="")
            v = str(v or "")
            if is_junk_scalar(v):
                vals[key] = ""
            else:
                vals[key] = v

        # normalize history keys
        for hkey in ("title_history", "cabinet_history"):
            hv = vals.get(hkey, None)
            if isinstance(hv, str):
                # don't try to parse, just drop corrupted string history
                vals[hkey] = []
            elif isinstance(hv, list):
                cleaned = []
                for item in hv:
                    s = str(item or "").strip()
                    if not s or is_junk_scalar(s):
                        continue
                    cleaned.append(s)
                vals[hkey] = cleaned
            elif hv is None:
                vals[hkey] = []

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        self.setFont(QFont("Segoe UI", 10))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        title = QLabel("CatalogLabel")
        title.setObjectName("Title")
        outer.addWidget(title, 0)

        top = QGroupBox("Mode & Rules")
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(10, 10, 10, 10)
        top_lay.setSpacing(8)

        top_lay.addWidget(QLabel("Mode"), 0)
        self.mode = QComboBox()
        self.mode.addItems(["Free Typing (no rules)", "Rules Mode (Excel)"])
        self.mode.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.mode.setMinimumWidth(220)
        top_lay.addWidget(self.mode, 0)

        self.btn_load_rules = QPushButton("Load Excel…")
        top_lay.addWidget(self.btn_load_rules, 0)

        top_lay.addWidget(QLabel("Profile"), 0)
        self.cbo_profile = QComboBox()
        self.cbo_profile.setEnabled(False)
        self.cbo_profile.setMinimumWidth(260)
        top_lay.addWidget(self.cbo_profile, 0)

        top_lay.addStretch(1)

        self.btn_export_pdf = QPushButton("Export PDF")
        self.btn_save_cache = QPushButton("Save Cache")
        top_lay.addWidget(self.btn_export_pdf, 0)
        top_lay.addWidget(self.btn_save_cache, 0)

        outer.addWidget(top, 0)

        info = QGroupBox("Label Info")
        info_form = QFormLayout(info)
        info_form.setLabelAlignment(Qt.AlignLeft)

        self.ed_title = QLineEdit()
        self.ed_title.setPlaceholderText("e.g. Cabinet Inventory Label")
        self.ed_cab = QLineEdit()
        self.ed_cab.setPlaceholderText("e.g. Collection Room A / Cabinet 12")

        # Proper completers (no stringified list nonsense)
        self._title_model = QStringListModel([])
        self._cab_model = QStringListModel([])

        self._title_completer = QCompleter(self._title_model, self)
        self._title_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._title_completer.setFilterMode(Qt.MatchContains)
        self.ed_title.setCompleter(self._title_completer)

        self._cab_completer = QCompleter(self._cab_model, self)
        self._cab_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._cab_completer.setFilterMode(Qt.MatchContains)
        self.ed_cab.setCompleter(self._cab_completer)

        info_form.addRow("Title", self.ed_title)
        info_form.addRow("Cabinet Section", self.ed_cab)
        outer.addWidget(info, 0)

        # ---------- Label Size (restored) ----------
        size = QGroupBox("Label Size")
        size_form = QFormLayout(size)
        size_form.setLabelAlignment(Qt.AlignLeft)

        self.cbo_size_preset = QComboBox()
        self.cbo_size_preset.addItems(["A4 Portrait", "A4 Landscape", "A5 Portrait", "A5 Landscape"])

        self.chk_custom_size = QCheckBox("Custom size (cm)")
        self.sp_w_cm = QDoubleSpinBox()
        self.sp_w_cm.setRange(1, 100)
        self.sp_w_cm.setDecimals(1)
        self.sp_w_cm.setValue(21.0)
        self.sp_h_cm = QDoubleSpinBox()
        self.sp_h_cm.setRange(1, 100)
        self.sp_h_cm.setDecimals(1)
        self.sp_h_cm.setValue(29.7)

        size_form.addRow("Preset", self.cbo_size_preset)
        size_form.addRow(self.chk_custom_size)
        size_form.addRow("W (cm)", self.sp_w_cm)
        size_form.addRow("H (cm)", self.sp_h_cm)
        outer.addWidget(size, 0)

        hier = QGroupBox("Hierarchy")
        hier_lay = QVBoxLayout(hier)
        hier_lay.setContentsMargins(10, 10, 10, 10)
        hier_lay.setSpacing(8)

        self.hierarchy = HierarchyEditor(self)
        hier_lay.addWidget(self.hierarchy, 1)
        outer.addWidget(hier, 1)

        self.status = QLabel("Ready.")
        self.status.setStyleSheet("color: #bdb7aa;")
        outer.addWidget(self.status, 0)

        self._on_custom_size_toggled(self.chk_custom_size.isChecked())

    def _wire(self) -> None:
        self.mode.currentIndexChanged.connect(lambda _i: self._on_mode_changed())
        self.btn_load_rules.clicked.connect(self._load_rules_clicked)
        self.cbo_profile.currentIndexChanged.connect(lambda _i: self._on_profile_changed())

        self.chk_custom_size.toggled.connect(self._on_custom_size_toggled)

        self.btn_save_cache.clicked.connect(self._save_cache_clicked)
        self.btn_export_pdf.clicked.connect(self._export_pdf_clicked)

        # scalar current values + history lists
        self.ed_title.textChanged.connect(lambda t: self._on_meta_changed("title", "title_history", t))
        self.ed_cab.textChanged.connect(lambda t: self._on_meta_changed("cabinet_section", "cabinet_history", t))

    def _on_meta_changed(self, key_current: str, key_history: str, text: str) -> None:
        txt = str(text or "")
        self._cache_write_text(key_current, txt)
        if txt.strip():
            remember(self.cache, key_history, txt.strip(), limit=200)
            self._refresh_meta_completers()

    def _refresh_meta_completers(self) -> None:
        """
        Rebuild QCompleter lists from history lists.
        This prevents the ']' char suggestion bug.
        """
        titles = self._cache_read_list("title_history")
        cabs = self._cache_read_list("cabinet_history")

        # show newest first (more useful)
        titles = list(reversed(titles))[:200]
        cabs = list(reversed(cabs))[:200]

        self._title_model.setStringList(titles)
        self._cab_model.setStringList(cabs)

    # ---------------- Mode & rules ----------------
    def _rules_on(self) -> bool:
        return self.mode.currentIndex() == 1 and self.rules is not None and self.profile is not None

    def _apply_mode_ui(self) -> None:
        self.ed_title.setText(self._cache_read_text("title", ""))
        self.ed_cab.setText(self._cache_read_text("cabinet_section", ""))

        rules_ready = (self.rules is not None and len(self.rules.profiles) > 0)
        self.cbo_profile.setEnabled(self.mode.currentIndex() == 1 and rules_ready)
        self.btn_load_rules.setEnabled(self.mode.currentIndex() == 1)

        if self.profile is not None:
            try:
                self.level_labels = dict(self.profile.level_labels or self.level_labels)
            except Exception:
                pass

        self.hierarchy.set_level_names(
            self.level_labels.get(1, "Level 1"),
            self.level_labels.get(2, "Level 2"),
            self.level_labels.get(3, "Level 3"),
            self.level_labels.get(4, "Level 4"),
        )

        if self.profile is not None:
            self.hierarchy.set_rules_normalization(self.profile.code_delimiter or ".", 2)
        else:
            self.hierarchy.set_rules_normalization(".", 2)

    def _refresh_hierarchy_providers(self) -> None:
        self.hierarchy.set_providers(self._suggest_codes, self._suggest_names, self._lookup_code)
        self.hierarchy.set_on_change(self._on_hierarchy_change)

    def _on_mode_changed(self) -> None:
        self._apply_mode_ui()
        self._refresh_hierarchy_providers()

    def _load_rules_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load Rules Workbook", "", "Excel (*.xlsx)")
        if not path:
            return

        try:
            wb = load_rules_xlsx(path)
            self.rules = wb
            self.rules_path = Path(path)

            self.cbo_profile.clear()
            for pid, prof in wb.profiles.items():
                self.cbo_profile.addItem(prof.profile_name, userData=pid)

            self.cbo_profile.setEnabled(True)
            self.status.setText(f"Loaded rules: {Path(path).name}")
        except RulesWorkbookError as e:
            QMessageBox.critical(
                self,
                "Rules workbook not valid",
                str(e)
                + "\n\nHow to fix:"
                + "\n- Simple workbook requires sheets: 'Profile' and 'Level 1'"
                + "\n- Legacy workbook requires sheet: 'Profiles'"
                + "\n\nTip: In Excel, right-click sheet tab → Rename."
            )
            self.status.setText("Rules load failed (invalid workbook format).")
            return

        except Exception as e:
            QMessageBox.critical(self, "Load failed", str(e))
            self.rules = None
            self.profile = None
            self.rules_path = None
            self.cbo_profile.clear()
            self.cbo_profile.setEnabled(False)
            self.status.setText("Load failed.")

        self._apply_mode_ui()
        self._refresh_hierarchy_providers()

    def _on_profile_changed(self) -> None:
        if self.rules is None:
            self.profile = None
            self._apply_mode_ui()
            self._refresh_hierarchy_providers()
            return

        pid = self.cbo_profile.currentData()
        if not pid:
            self.profile = None
        else:
            self.profile = self.rules.get_profile(str(pid))

        self._apply_mode_ui()
        self._refresh_hierarchy_providers()
        self.status.setText("Profile selected." if self.profile else "No profile selected.")

    # ---------------- Hierarchy callbacks ----------------
    def _on_hierarchy_change(self, level: int, code: str, name: str) -> None:
        if code.strip():
            remember(self.cache, f"level{level}_codes", code.strip(), limit=500)
        if name.strip():
            remember(self.cache, f"level{level}_names", name.strip(), limit=500)

    def _suggest_codes(self, level: int, prefix: str, parent_code: str = "") -> List[str]:
        prefix = (prefix or "").strip()
        if self._rules_on() and self.rules and self.profile:
            try:
                out = lookup_mapping(self.rules, self.profile.profile_id, level, prefix)
                if isinstance(out, list):
                    return [str(x) for x in out][:200]
            except Exception:
                pass
        return suggest(self.cache, f"level{level}_codes", prefix, limit=200)

    def _suggest_names(self, level: int, prefix: str, parent_code: str = "") -> List[str]:
        prefix = (prefix or "").strip()
        if self._rules_on() and self.rules and self.profile:
            try:
                out = lookup_mapping(self.rules, self.profile.profile_id, level, prefix)
                if isinstance(out, list):
                    return [str(x) for x in out][:200]
            except Exception:
                pass
        return suggest(self.cache, f"level{level}_names", prefix, limit=200)

    def _lookup_code(self, level: int, code: str, parent_code: str = "") -> Optional[LookupResult]:
        code = (code or "").strip()
        if not code:
            return None

        if self._rules_on() and self.rules and self.profile:
            try:
                mr = lookup_mapping(self.rules, self.profile.profile_id, level, code)
                if mr is not None and hasattr(mr, "name"):
                    return LookupResult(
                        name=str(getattr(mr, "name", "") or ""),
                        locked=bool(getattr(mr, "locked", False)),
                    )
            except Exception:
                pass
        return None

    # ---------------- Size (restored) ----------------
    def _on_custom_size_toggled(self, on: bool) -> None:
        self.sp_w_cm.setEnabled(bool(on))
        self.sp_h_cm.setEnabled(bool(on))
        self.cbo_size_preset.setEnabled(not bool(on))

    def _current_pagesize_pts(self) -> Tuple[float, float]:
        if self.chk_custom_size.isChecked():
            return (cm_to_pt(self.sp_w_cm.value()), cm_to_pt(self.sp_h_cm.value()))

        preset = self.cbo_size_preset.currentText()
        if preset == "A4 Portrait":
            return A4
        if preset == "A4 Landscape":
            w, h = A4
            return (h, w)
        if preset == "A5 Portrait":
            return A5
        if preset == "A5 Landscape":
            w, h = A5
            return (h, w)
        return A4

    # ---------------- Cache save ----------------
    def _save_cache_clicked(self) -> None:
        try:
            save_cache(self.cache)
            QMessageBox.information(self, "Saved", "Cache saved.")
            self.status.setText("Cache saved.")
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", str(e))
            self.status.setText("Save cache failed.")

    # ---------------- Export ----------------
    def _export_pdf_clicked(self) -> None:
        doc = LabelDocument()
        doc.title = (self.ed_title.text() or "").strip()
        doc.cabinet_section = (self.ed_cab.text() or "").strip()
        doc.hierarchy = self.hierarchy.export_entries()

        dlg = PdfTemplateDialog(self)
        dlg.set_sample_content(
            doc.title or "NHMC Label",
            doc.cabinet_section or "Cabinet Section: Example Cabinet A",
        )
        dlg.set_preview_document(doc)

        try:
            if self._last_template_id in dlg.radios:
                dlg.radios[self._last_template_id].setChecked(True)
                dlg._selected_template_id = self._last_template_id
            dlg.set_selected_section_title(self._last_section_title)
            dlg._update_preview()
        except Exception:
            pass

        if dlg.exec() != QDialog.DialogCode.Accepted:
            self.status.setText("Export cancelled.")
            return

        template_id = dlg.selected_template_id()
        section_title = dlg.selected_section_title()

        self._last_template_id = template_id
        self._last_section_title = section_title

        out_path, _ = QFileDialog.getSaveFileName(self, "Export PDF", "labels.pdf", "PDF (*.pdf)")
        if not out_path:
            self.status.setText("Export cancelled.")
            return

        pagesize = self._current_pagesize_pts()
        opts = PdfExportOptions(pagesize=pagesize, template_id=template_id, section_title=section_title)

        try:
            export_label_pdf(doc, out_path, opts)
            QMessageBox.information(self, "Exported", f"Exported PDF:\n{out_path}")
            label = section_title if section_title else "no section title"
            self.status.setText(f"Exported ({template_id}, {label}): {Path(out_path).name}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))
            self.status.setText("Export failed.")





