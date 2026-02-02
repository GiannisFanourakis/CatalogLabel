from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import Qt
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
)

from reportlab.lib.pagesizes import A4, A5

from src.domain.models import LabelDocument
from src.domain.units import cm_to_pt
from src.domain.normalize import expand_child_code
from src.services.cache.cache_store import load_cache, save_cache, remember, suggest
from src.services.rules.excel_loader import load_rules_xlsx
from src.services.rules.engine import lookup_mapping
from src.services.rules.rules_types import RulesWorkbook, RulesProfile
from src.services.export.pdf_exporter import export_label_pdf, PdfExportOptions
from src.ui.qt.widgets.hierarchy_editor import HierarchyEditor, LookupResult
from src.ui.qt.widgets.pdf_template_dialog import PdfTemplateDialog


class LabelEditorView(QWidget):
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

        self._build_ui()
        self._wire()

        self._apply_mode_ui()
        self._refresh_hierarchy_providers()

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        self.setFont(QFont("Segoe UI", 10))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        title = QLabel("LabelForge")
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

        info_form.addRow("Title", self.ed_title)
        info_form.addRow("Cabinet Section", self.ed_cab)
        outer.addWidget(info, 0)

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

        content = QGroupBox("Label Content")
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(10, 10, 10, 10)
        content_lay.setSpacing(8)

        self.hierarchy = HierarchyEditor()
        self.hierarchy.set_level_names(self.level_labels[1], self.level_labels[2], self.level_labels[3], self.level_labels[4])
        content_lay.addWidget(self.hierarchy, 1)
        outer.addWidget(content, 1)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        outer.addLayout(footer, 0)

        self.status = QLabel("Ready.")
        self.status.setObjectName("Status")
        footer.addWidget(self.status, 1)

        self._on_custom_size_toggled(self.chk_custom_size.isChecked())

    def _wire(self) -> None:
        self.mode.currentIndexChanged.connect(lambda _i: self._apply_mode_ui())
        self.btn_load_rules.clicked.connect(self._on_load_rules)
        self.cbo_profile.currentIndexChanged.connect(lambda _i: self._on_profile_changed())

        self.btn_export_pdf.clicked.connect(self._export_pdf_clicked)
        self.btn_save_cache.clicked.connect(self._save_cache_clicked)

        self.chk_custom_size.toggled.connect(self._on_custom_size_toggled)

        self.ed_title.textEdited.connect(lambda _t: self._remember_free_typing_meta())
        self.ed_cab.textEdited.connect(lambda _t: self._remember_free_typing_meta())

        self.hierarchy.set_on_change(self._on_hierarchy_changed)

    # ---------------- Helpers ----------------
    def _rules_on(self) -> bool:
        return self.mode.currentIndex() == 1 and self.rules is not None and self.profile is not None

    def _delimiter(self) -> str:
        if self.profile and getattr(self.profile, "code_delimiter", None):
            return self.profile.code_delimiter
        return "."

    def _pad_level1(self) -> int:
        try:
            if self.rules and getattr(self.rules, "settings", None):
                v = str(self.rules.settings.get("pad_level1", "2") or "2")
                n = int(v)
                return max(1, min(n, 6))
        except Exception:
            pass
        return 2

    def _on_custom_size_toggled(self, on: bool) -> None:
        self.sp_w_cm.setEnabled(on)
        self.sp_h_cm.setEnabled(on)
        self.cbo_size_preset.setEnabled(not on)

    def _current_pagesize_pts(self) -> tuple[float, float]:
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

    # ---------------- Mode ----------------
    def _apply_mode_ui(self) -> None:
        rules_mode = (self.mode.currentIndex() == 1)
        self.btn_load_rules.setVisible(rules_mode)
        self.cbo_profile.setVisible(rules_mode)

        if not rules_mode:
            self.profile = None
            self.level_labels = {1: "Level 1", 2: "Level 2", 3: "Level 3", 4: "Level 4"}
            self.hierarchy.set_level_names(self.level_labels[1], self.level_labels[2], self.level_labels[3], self.level_labels[4])
            self.hierarchy.set_rules_normalization(".", 2)
            self.status.setText("Free Typing Mode ON.")
            self._refresh_hierarchy_providers()
        else:
            self.status.setText("Rules Mode ON. Load an Excel rules file.")
            self._refresh_hierarchy_providers()

    # ---------------- Rules loading ----------------
    def load_rules_from_path(self, path: str) -> bool:
        try:
            self.rules = load_rules_xlsx(path)
            self.rules_path = Path(path)
        except Exception as e:
            QMessageBox.critical(self, "Load Excel Failed", str(e))
            self.rules = None
            self.profile = None
            self.rules_path = None
            self.cbo_profile.clear()
            self.cbo_profile.setEnabled(False)
            self.btn_load_rules.setText("Load Excel…")
            self._refresh_hierarchy_providers()
            return False

        self.cbo_profile.blockSignals(True)
        self.cbo_profile.clear()

        try:
            profiles = getattr(self.rules, "profiles", {}) or {}
            for pid, prof in sorted(profiles.items(), key=lambda kv: str(kv[0]).lower()):
                name = getattr(prof, "profile_name", str(pid))
                self.cbo_profile.addItem(f"{name} ({pid})", userData=pid)
        finally:
            self.cbo_profile.blockSignals(False)

        self.cbo_profile.setEnabled(self.cbo_profile.count() > 0)

        if self.cbo_profile.count() > 0:
            self.cbo_profile.setCurrentIndex(0)
            self._apply_profile(self.cbo_profile.currentData())

        self.status.setText(f"Loaded Excel: {self.rules_path.name}")
        self.btn_load_rules.setText("Change Excel…")

        self._refresh_hierarchy_providers()
        return True

    def _on_load_rules(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load rules.xlsx", str(Path.cwd()), "Excel (*.xlsx)")
        if not path:
            return
        self.load_rules_from_path(path)

    def _on_profile_changed(self) -> None:
        pid = self.cbo_profile.currentData()
        if pid:
            self._apply_profile(pid)

    def _apply_profile(self, profile_id: str) -> None:
        if not self.rules or not profile_id:
            return

        prof = self.rules.get_profile(profile_id)
        if not prof:
            return

        self.profile = prof

        labels = getattr(prof, "level_labels", {}) or {}
        self.level_labels = {
            1: labels.get(1, "Level 1"),
            2: labels.get(2, "Level 2"),
            3: labels.get(3, "Level 3"),
            4: labels.get(4, "Level 4"),
        }

        self.hierarchy.set_level_names(self.level_labels[1], self.level_labels[2], self.level_labels[3], self.level_labels[4])

        settings = getattr(self.rules, "settings", {}) or {}
        if settings.get("title_default"):
            self.ed_title.setText(settings["title_default"])

        self.status.setText(f"Profile: {getattr(prof,'profile_name','')}  | delimiter '{self._delimiter()}'")
        self.hierarchy.set_rules_normalization(self._delimiter(), self._pad_level1())
        self._refresh_hierarchy_providers()

    # ---------------- Providers ----------------
    def _refresh_hierarchy_providers(self) -> None:
        if self._rules_on():
            self.hierarchy.set_providers(self._suggest_codes_rules, self._suggest_names_rules, self._lookup_rules)
        else:
            self.hierarchy.set_providers(self._suggest_codes_free, self._suggest_names_free, None)

    def _cache_key_code(self, level: int) -> str:
        return f"lvl{level}.code"

    def _cache_key_name(self, level: int) -> str:
        return f"lvl{level}.name"

    def _suggest_codes_free(self, level: int, prefix: str) -> List[str]:
        try:
            return suggest(self.cache, self._cache_key_code(level), prefix=prefix)  # type: ignore
        except TypeError:
            return suggest(self.cache, self._cache_key_code(level), prefix)  # type: ignore
        except Exception:
            return []

    def _suggest_names_free(self, level: int, prefix: str) -> List[str]:
        try:
            return suggest(self.cache, self._cache_key_name(level), prefix=prefix)  # type: ignore
        except TypeError:
            return suggest(self.cache, self._cache_key_name(level), prefix)  # type: ignore
        except Exception:
            return []

    def _rules_scan_codes(self, level: int) -> List[str]:
        codes: List[str] = []
        if not self.rules or not self.profile:
            return codes
        try:
            for (pid, lv, _), mr in (getattr(self.rules, "mappings", {}) or {}).items():
                if pid != self.profile.profile_id or lv != level:
                    continue
                code = getattr(mr, "code", "") or ""
                if code:
                    codes.append(str(code).strip())
        except Exception:
            pass
        return sorted(set([c for c in codes if c]))

    def _rules_scan_names(self, level: int) -> List[str]:
        names: List[str] = []
        if not self.rules or not self.profile:
            return names
        try:
            for (pid, lv, _), mr in (getattr(self.rules, "mappings", {}) or {}).items():
                if pid != self.profile.profile_id or lv != level:
                    continue
                nm = getattr(mr, "name", "") or ""
                if nm:
                    names.append(str(nm).strip())
        except Exception:
            pass
        return sorted(set([n for n in names if n]))

    def _suggest_codes_rules(self, level: int, prefix: str, parent_code: str = "") -> List[str]:
        if not self._rules_on() or not self.rules or not self.profile:
            return self._suggest_codes_free(level, prefix)

        delim = self._delimiter()
        pfx = (prefix or "").strip()
        parent_code = (parent_code or "").strip()

        hist = self._suggest_codes_free(level, pfx)

        if level <= 1 or not parent_code:
            wb_codes = self._rules_scan_codes(level)
            merged = sorted(set([c for c in wb_codes if c.lower().startswith(pfx.lower())] + hist))
            return merged[:200]

        suffixes: List[str] = []
        for (pid, lv, _), mr in (getattr(self.rules, "mappings", {}) or {}).items():
            if pid != self.profile.profile_id or lv != level:
                continue
            code = str(getattr(mr, "code", "") or "")
            if not code.startswith(parent_code + delim):
                continue
            suf = code[len(parent_code + delim):]
            if suf:
                suffixes.append(suf)

        wb_suffixes = sorted(set(suffixes))
        if pfx:
            wb_suffixes = [s for s in wb_suffixes if s.lower().startswith(pfx.lower())]

        hist_suffix: List[str] = []
        for h in hist:
            hs = (h or "").strip()
            if hs.startswith(parent_code + delim):
                hs = hs[len(parent_code + delim):]
            hist_suffix.append(hs)

        merged = sorted(set(wb_suffixes + hist_suffix))
        return merged[:200]

    def _suggest_names_rules(self, level: int, prefix: str) -> List[str]:
        wb = self._rules_scan_names(level)
        hist = self._suggest_names_free(level, prefix)
        merged = sorted(set([n for n in wb if n.lower().startswith((prefix or "").lower())] + hist))
        return merged[:200]

    def _lookup_rules(self, level: int, code: str, parent_code: str = "") -> Optional[LookupResult]:
        if not self._rules_on():
            return None
        assert self.rules is not None
        assert self.profile is not None

        code_norm = (code or "").strip()
        if level == 1:
            if code_norm.isdigit():
                code_norm = str(int(code_norm)).zfill(self._pad_level1())
        else:
            code_norm = expand_child_code((parent_code or "").strip(), code_norm, self._delimiter())

        mr = lookup_mapping(self.rules, self.profile.profile_id, level, code_norm.strip())
        if mr and getattr(mr, "name", None):
            return LookupResult(name=str(mr.name), locked=bool(getattr(mr, "locked", False)))
        return None

    # ---------------- Cache ----------------
    def _on_hierarchy_changed(self, level: int, code: str, name: str) -> None:
        if code:
            remember(self.cache, self._cache_key_code(level), code, limit=500)
        if name:
            remember(self.cache, self._cache_key_name(level), name, limit=500)

    def _remember_free_typing_meta(self) -> None:
        remember(self.cache, "title", self.ed_title.text(), limit=200)
        remember(self.cache, "cabinet_section", self.ed_cab.text(), limit=200)

    # ---------------- Actions ----------------
    def _save_cache_clicked(self) -> None:
        try:
            save_cache(self.cache)
            QMessageBox.information(self, "Saved", "Cache saved.")
            self.status.setText("Cache saved.")
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", str(e))
            self.status.setText("Save cache failed.")

    def _export_pdf_clicked(self) -> None:
        dlg = PdfTemplateDialog(self)
        dlg.set_sample_content(
            (self.ed_title.text() or "").strip() or "NHMC Label",
            (self.ed_cab.text() or "").strip() or "Cabinet Section: Example Cabinet A",
        )

        # restore last selections
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

        doc = LabelDocument()
        doc.title = (self.ed_title.text() or "").strip()
        doc.cabinet_section = (self.ed_cab.text() or "").strip()
        doc.hierarchy = self.hierarchy.export_entries()

        opts = PdfExportOptions(pagesize=pagesize, template_id=template_id, section_title=section_title)

        try:
            export_label_pdf(doc, out_path, opts)
            QMessageBox.information(self, "Exported", f"Exported PDF:\n{out_path}")
            label = section_title if section_title else "no section title"
            self.status.setText(f"Exported ({template_id}, {label}): {Path(out_path).name}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))
            self.status.setText("Export failed.")
