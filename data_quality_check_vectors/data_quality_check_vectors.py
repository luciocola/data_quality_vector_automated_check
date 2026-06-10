"""Main plugin implementation for Data Quality Check for Vectors."""

import functools
import json
import math
import os
import re
import hashlib
import urllib.error
import urllib.request
from datetime import datetime

from qgis import processing

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QIcon
from qgis.PyQt.QtWidgets import QAction, QListWidgetItem, QMessageBox, QInputDialog, QLineEdit
from qgis.core import (
    NULL,
    QgsField,
    QgsFeature,
    QgsFeatureRequest,
    QgsGeometry,
    QgsMapLayerType,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
    QgsVectorDataProvider,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.PyQt.QtCore import QVariant

from .data_quality_check_dialog import DataQualityCheckDialog
from .rag_rules_engine import (
    EmbeddingRetriever,
    OllamaClient,
    RuleExecutor,
    RuleStore,
    sanitize_rule,
)
from .report_exporter import export_report_html, export_report_json, export_report_pdf


class RectangleMapTool(QgsMapTool):
    """Simple rectangle picker for area-of-interest selection."""

    def __init__(self, canvas, on_finished):
        super().__init__(canvas)
        self.canvas = canvas
        self.on_finished = on_finished
        self.start_point = None
        self.end_point = None
        self.rubber_band = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry)
        self.rubber_band.setColor(QColor(255, 0, 0, 120))
        self.rubber_band.setFillColor(QColor(255, 0, 0, 40))
        self.rubber_band.setWidth(2)

    def reset(self):
        self.start_point = None
        self.end_point = None
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)

    def canvasPressEvent(self, event):
        self.start_point = self.toMapCoordinates(event.pos())
        self.end_point = self.start_point
        self._update_rubber_band()

    def canvasMoveEvent(self, event):
        if self.start_point is None:
            return
        self.end_point = self.toMapCoordinates(event.pos())
        self._update_rubber_band()

    def canvasReleaseEvent(self, event):
        if self.start_point is None:
            return
        self.end_point = self.toMapCoordinates(event.pos())
        self._update_rubber_band()
        rect = QgsRectangle(self.start_point, self.end_point)
        self.on_finished(rect)

    def _update_rubber_band(self):
        if self.start_point is None or self.end_point is None:
            return
        rect = QgsRectangle(self.start_point, self.end_point)
        points = [
            QgsPointXY(rect.xMinimum(), rect.yMinimum()),
            QgsPointXY(rect.xMinimum(), rect.yMaximum()),
            QgsPointXY(rect.xMaximum(), rect.yMaximum()),
            QgsPointXY(rect.xMaximum(), rect.yMinimum()),
            QgsPointXY(rect.xMinimum(), rect.yMinimum()),
        ]
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        for point in points:
            self.rubber_band.addPoint(point, False)
        self.rubber_band.show()


class DataQualityCheckVectors:
    """QGIS plugin main class."""

    LIABILITY_CLAIMS_MINIMAL_FIELDS = [
        ("lc_claim_id", ""),
        ("lc_claim_status", "pending"),
        ("lc_claim_type", "other"),
        ("lc_responsible_party", ""),
        ("lc_claim_date", ""),
    ]

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.menu = "&Data Quality Check for Vectors"
        self.toolbar = self.iface.addToolBar("DataQualityCheckVectors")
        self.toolbar.setObjectName("DataQualityCheckVectors")

        self.action = None
        self.dialog = None
        self.picked_extent = None
        self.map_tool = None
        self.previous_map_tool = None

        self.rules_path = os.path.join(self.plugin_dir, "rules", "quality_rules.json")
        self.rule_store = RuleStore(self.rules_path)
        self.rule_store.save_default_if_missing()
        self.rule_store.ensure_default_profiles()
        self.embedding_retriever = EmbeddingRetriever()
        self._managed_rules = []
        self._agent_connections = []  # list of (signal, handler) for cleanup

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.svg")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(self.plugin_dir, "icon.png")
        self.action = QAction(QIcon(icon_path), "Data Quality Check for Vectors", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu(self.menu, self.action)
        self.toolbar.addAction(self.action)

    def unload(self):
        if self.action is not None:
            self.iface.removePluginMenu(self.menu, self.action)
            self.iface.removeToolBarIcon(self.action)
        del self.toolbar

    def _vector_layers(self):
        return [
            layer for layer in QgsProject.instance().mapLayers().values()
            if isinstance(layer, QgsVectorLayer)
        ]

    def run(self):
        layers = self._vector_layers()
        if not layers:
            QMessageBox.warning(self.iface.mainWindow(), "Data Quality Check", "No vector layers found in the project.")
            return

        self.dialog = DataQualityCheckDialog(self.iface.mainWindow())
        self.dialog.set_layers(layers)
        self.dialog.set_profiles(self.rule_store.available_profiles())
        self.dialog.btn_pick_area.clicked.connect(self.pick_area)
        self.dialog.btn_sketch_highlight.clicked.connect(self.sketch_highlight_elements)
        self.dialog.btn_connect_highlighted.clicked.connect(self.connect_highlighted_elements)
        self.dialog.btn_run.clicked.connect(self.execute_checks)
        self.dialog.btn_store_immutable.clicked.connect(self.store_features_in_immutable_catalogue)
        self.dialog.btn_add_rule_from_prompt.clicked.connect(self.add_rule_from_prompt)
        self.dialog.btn_close.clicked.connect(self.dialog.reject)

        self.dialog.rag_query_input.textChanged.connect(self._update_status_badge)
        self.dialog.chk_apply_autofix.stateChanged.connect(self._update_status_badge)
        self.dialog.chk_schema_harmonize.stateChanged.connect(self._update_status_badge)
        self.dialog.area_mode.currentTextChanged.connect(self._update_status_badge)
        self.dialog.layer_list.itemChanged.connect(self._update_status_badge)
        self.dialog.rule_profile.currentTextChanged.connect(self._on_validation_profile_changed)
        self.dialog.rule_search_input.textChanged.connect(self._refresh_rule_search)
        self.dialog.btn_rule_search.clicked.connect(self._refresh_rule_search)
        self.dialog.btn_refresh_search.clicked.connect(self._refresh_rule_search)
        self.dialog.btn_use_selected_rule.clicked.connect(self._use_selected_rule_in_query)

        self.dialog.profile_manage.currentTextChanged.connect(self._on_rules_profile_changed)
        self.dialog.btn_rules_reload.clicked.connect(self._reload_rules_manager)
        self.dialog.btn_rules_new.clicked.connect(self._new_rule)
        self.dialog.btn_rules_delete.clicked.connect(self._delete_rule)
        self.dialog.btn_rules_save.clicked.connect(self._save_rule)
        self.dialog.btn_rules_save_all.clicked.connect(self._save_rules_profile)
        self.dialog.btn_rule_nl_use_example.clicked.connect(self._use_rules_manager_example)
        self.dialog.btn_rule_nl_generate.clicked.connect(self._generate_rule_draft_from_manager_prompt)
        self.dialog.rules_list.currentRowChanged.connect(self._on_rule_selected)

        self.dialog.chk_agent_enabled.stateChanged.connect(self._on_agent_enabled_changed)
        self.dialog.finished.connect(self._on_dialog_closed)

        self._update_status_badge()
        self._reload_rules_manager()
        self._refresh_rule_search()
        self.dialog.clear_highlighted_elements()
        self.dialog.show()

    def _on_dialog_closed(self, _result):
        """Disconnect all agent layer signals when the dialog is closed."""
        self._agent_disconnect_all()

    # ------------------------------------------------------------------
    # Auto-Check Agent
    # ------------------------------------------------------------------

    def _on_agent_enabled_changed(self, state):
        if self.dialog is None:
            return
        if state == Qt.Checked:
            self._agent_connect_selected_layers()
        else:
            self._agent_disconnect_all()

    def _agent_connect_selected_layers(self):
        self._agent_disconnect_all()
        if self.dialog is None:
            return

        selected_ids = self.dialog.selected_layer_ids()
        layers_by_id = {layer.id(): layer for layer in self._vector_layers()}
        connected = 0

        for layer_id in selected_ids:
            layer = layers_by_id.get(layer_id)
            if layer is None:
                continue

            def _make_handler(lid):
                """Return a zero-argument callable that runs checks for lid."""
                def _handler():
                    self._agent_run_checks_for_layer(lid)
                return _handler

            handler = _make_handler(layer.id())
            layer.editingStopped.connect(handler)
            self._agent_connections.append((layer.editingStopped, handler))
            connected += 1

        status = (
            "Agent: monitoring {} layer(s) — will re-check on every committed edit".format(connected)
            if connected else "Agent: no layers selected to monitor"
        )
        self.dialog.set_agent_status(status)

    def _agent_disconnect_all(self):
        for signal, handler in self._agent_connections:
            try:
                signal.disconnect(handler)
            except Exception:
                pass
        self._agent_connections.clear()
        if self.dialog:
            self.dialog.set_agent_status("Agent: inactive")

    def _agent_layer_by_id(self, layer_id):
        for layer in self._vector_layers():
            if layer.id() == layer_id:
                return layer
        return None

    def _agent_run_checks_for_layer(self, layer_id):
        """Run the enabled check categories for a single layer and append the result."""
        layer = self._agent_layer_by_id(layer_id)
        if layer is None or self.dialog is None:
            return

        extent = self.picked_extent or self.iface.mapCanvas().extent()
        lines = [
            "",
            "[Agent] Auto-check triggered by edit commit on '{}'  ({})".format(
                layer.name(), datetime.now().strftime("%H:%M:%S")
            ),
        ]

        if self.dialog.chk_agent_attributes.isChecked():
            required_fields = self.dialog.required_fields()
            lines.append("  [Attributes]")
            if required_fields:
                lines.extend(
                    "    " + ln
                    for ln in self._check_required_fields([layer], required_fields, extent)
                )
            else:
                lines.append("    No required fields configured — add them in the Checks group.")

        if self.dialog.chk_agent_geometry.isChecked():
            lines.append("  [Geometry]")
            lines.extend(
                "    " + ln
                for ln in self._check_geometry_validity([layer], extent)
            )

        if self.dialog.chk_agent_topology.isChecked():
            lines.append("  [Topology]")
            lines.extend(
                "    " + ln
                for ln in self._check_road_endpoint_connectivity(
                    [layer],
                    extent,
                    self.dialog.snap_tolerance_spin.value(),
                    self.dialog.road_elevation_field.text().strip() or "elevation",
                )
            )

        self._agent_append_report("\n".join(lines))

    def _agent_append_report(self, text):
        if self.dialog is None:
            return
        existing = self.dialog.results.toPlainText()
        self.dialog.results.setPlainText(existing + "\n" + "-" * 40 + text)

    # ------------------------------------------------------------------

    def pick_area(self):
        if self.dialog.area_mode.currentText() == "Current map extent":
            self.picked_extent = self.iface.mapCanvas().extent()
            QMessageBox.information(self.iface.mainWindow(), "Area Selected", "Current map extent selected.")
            return

        self.previous_map_tool = self.iface.mapCanvas().mapTool()
        self.map_tool = RectangleMapTool(self.iface.mapCanvas(), self._on_rectangle_finished)
        self.iface.mapCanvas().setMapTool(self.map_tool)
        QMessageBox.information(
            self.iface.mainWindow(),
            "Draw Area",
            "Click and drag on the map canvas to define the validation area.",
        )

    def sketch_highlight_elements(self):
        selected_ids = self.dialog.selected_layer_ids() if self.dialog else []
        if not selected_ids:
            QMessageBox.warning(self.iface.mainWindow(), "No Layers", "Select at least one layer to highlight elements.")
            return

        self.previous_map_tool = self.iface.mapCanvas().mapTool()
        self.map_tool = RectangleMapTool(self.iface.mapCanvas(), self._on_sketch_highlight_finished)
        self.iface.mapCanvas().setMapTool(self.map_tool)
        QMessageBox.information(
            self.iface.mainWindow(),
            "Sketch Selection Area",
            "Draw an area on the map to highlight elements. You can then refine selection manually and click 'Connect Highlighted Elements'.",
        )

    def _on_rectangle_finished(self, rect):
        self.picked_extent = rect
        if self.previous_map_tool is not None:
            self.iface.mapCanvas().setMapTool(self.previous_map_tool)
        QMessageBox.information(self.iface.mainWindow(), "Area Selected", "Rectangle area selected for validation.")
        self._update_status_badge()

    def _on_sketch_highlight_finished(self, rect):
        if self.previous_map_tool is not None:
            self.iface.mapCanvas().setMapTool(self.previous_map_tool)

        selected_ids = self.dialog.selected_layer_ids() if self.dialog else []
        layers_by_id = {layer.id(): layer for layer in self._vector_layers()}
        selected_layers = [layers_by_id[layer_id] for layer_id in selected_ids if layer_id in layers_by_id]
        line_layers = [layer for layer in selected_layers if layer.geometryType() == QgsWkbTypes.LineGeometry]

        if not line_layers:
            if self.dialog is not None:
                self.dialog.clear_highlighted_elements()
            QMessageBox.warning(self.iface.mainWindow(), "Highlight Elements", "No line layers selected to highlight.")
            return

        total = 0
        highlighted_rows = []
        for layer in line_layers:
            feats = self._features_in_extent(layer, rect)
            ids = [feat.id() for feat in feats]
            layer.selectByIds(ids)
            total += len(ids)
            osm_idx = self._field_index(layer, "osm_id")
            for feat in feats:
                row = "{} | fid={}".format(layer.name(), feat.id())
                if osm_idx >= 0:
                    osm_val = feat["osm_id"]
                    row += " | osm_id={}".format("" if osm_val in (None, NULL) else str(osm_val))
                highlighted_rows.append(row)

        self.picked_extent = rect
        msg = "Highlighted {} element(s). Refine the highlighted set with normal QGIS selection tools, then click 'Connect Highlighted Elements'.".format(total)
        QMessageBox.information(self.iface.mainWindow(), "Highlight Elements", msg)
        if self.dialog is not None:
            self.dialog.set_highlighted_elements(highlighted_rows)
            self.dialog.results.setPlainText("[Selection] {}".format(msg))

    def execute_checks(self):
        selected_ids = self.dialog.selected_layer_ids()
        if not selected_ids:
            QMessageBox.warning(self.iface.mainWindow(), "No Layers", "Select at least one layer to validate.")
            return

        if self.picked_extent is None:
            self.picked_extent = self.iface.mapCanvas().extent()

        layers_by_id = {layer.id(): layer for layer in self._vector_layers()}
        selected_layers = [layers_by_id[layer_id] for layer_id in selected_ids if layer_id in layers_by_id]
        required_fields = self.dialog.required_fields()

        active_profile = self._active_profile()
        active_rules = self.rule_store.active_rules(active_profile)
        write_intent = self.dialog.chk_schema_harmonize.isChecked() or self.dialog.chk_apply_autofix.isChecked() or self._query_requests_autofix(self.dialog.rag_query_input.text().strip())

        if write_intent:
            write_prep_lines = self._prepare_layers_for_writes(selected_layers)
            report_lines = []
            report_lines.append("Data Quality Validation Report")
            report_lines.append("=" * 36)
            report_lines.append("Timestamp: {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            report_lines.append("")
            report_lines.extend(self._ensure_liability_claims_minimal_fields(selected_layers))
            report_lines.append("")
            report_lines.append("Area extent: {:.6f}, {:.6f}, {:.6f}, {:.6f}".format(
                self.picked_extent.xMinimum(),
                self.picked_extent.yMinimum(),
                self.picked_extent.xMaximum(),
                self.picked_extent.yMaximum(),
            ))
            report_lines.append("Layers: {}".format(", ".join(layer.name() for layer in selected_layers)))
            report_lines.append("Profile: {}".format(active_profile))
            report_lines.append("")
            report_lines.extend(write_prep_lines)
            report_lines.append("")

        else:
            report_lines = []
            report_lines.append("Data Quality Validation Report")
            report_lines.append("=" * 36)
            report_lines.append("Timestamp: {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            report_lines.append("")
            report_lines.append("Area extent: {:.6f}, {:.6f}, {:.6f}, {:.6f}".format(
                self.picked_extent.xMinimum(),
                self.picked_extent.yMinimum(),
                self.picked_extent.xMaximum(),
                self.picked_extent.yMaximum(),
            ))
            report_lines.append("Layers: {}".format(", ".join(layer.name() for layer in selected_layers)))
            report_lines.append("Profile: {}".format(active_profile))
            report_lines.append("")

        if self.dialog.chk_schema_harmonize.isChecked():
            harmonize_fields = self._collect_required_fields_from_rules(active_rules)
            harmonize_fields.update(required_fields)
            report_lines.extend(self._harmonize_schema_fields(selected_layers, sorted(harmonize_fields)))
            report_lines.append("")

        if self.dialog.chk_required_fields.isChecked() and required_fields:
            report_lines.extend(self._check_required_fields(selected_layers, required_fields, self.picked_extent))
            report_lines.append("")

        if self.dialog.chk_schema_homogeneous.isChecked():
            report_lines.extend(self._check_schema_homogeneous(selected_layers))
            report_lines.append("")

        if self.dialog.chk_geometry_validity.isChecked():
            report_lines.extend(self._check_geometry_validity(selected_layers, self.picked_extent))
            report_lines.append("")

        if self.dialog.chk_road_topology.isChecked():
            report_lines.extend(self._check_road_endpoint_connectivity(
                selected_layers,
                self.picked_extent,
                self.dialog.snap_tolerance_spin.value(),
                self.dialog.road_elevation_field.text().strip() or "elevation",
            ))
            report_lines.append("")

        if self.dialog.chk_topology_repair.isChecked():
            report_lines.extend(
                self._run_topology_repair(
                    selected_layers,
                    tolerance=self.dialog.repair_tolerance_spin.value(),
                    preview_only=self.dialog.chk_topology_preview_only.isChecked(),
                )
            )
            report_lines.append("")

        rag_query = self.dialog.rag_query_input.text().strip()
        apply_autofix = self.dialog.chk_apply_autofix.isChecked()
        if (not apply_autofix) and self._query_requests_autofix(rag_query):
            apply_autofix = True
            report_lines.append("[5a] Autofix auto-enabled from query intent (fill/set/create).")
            report_lines.append("")

        if self.dialog.chk_use_rag.isChecked():
            report_lines.extend(self._run_rag_rules(
                selected_layers,
                self.picked_extent,
                rag_query,
                apply_autofix,
                active_rules=active_rules,
                active_profile=active_profile,
            ))
            report_lines.append("")

        report_text = "\n".join(report_lines)
        self.dialog.results.setPlainText(report_text)
        self._export_report_if_requested(report_text, report_lines)

    def _ensure_liability_claims_minimal_fields(self, layers):
        lines = ["[0a] Liability/claims minimal attributes (STAC-derived)"]
        for layer in layers:
            if self._layer_is_read_only(layer):
                lines.append("Layer '{}': read-only, skipped minimal liability/claims attributes.".format(layer.name()))
                continue

            added = []
            failed = []
            for field_name, _default in self.LIABILITY_CLAIMS_MINIMAL_FIELDS:
                idx, created = self._ensure_text_field(layer, field_name)
                if idx >= 0:
                    if created:
                        added.append(field_name)
                else:
                    failed.append(field_name)

            if added:
                lines.append(
                    "Layer '{}': added minimal liability/claims attributes: {}.".format(
                        layer.name(), ", ".join(sorted(added))
                    )
                )
            else:
                lines.append("Layer '{}': minimal liability/claims attributes already available.".format(layer.name()))

            if failed:
                lines.append("Layer '{}': failed to add attributes: {}.".format(layer.name(), ", ".join(sorted(failed))))
        return lines

    def _features_in_extent(self, layer, extent):
        request = QgsFeatureRequest().setFilterRect(extent)
        return list(layer.getFeatures(request))

    def _field_index(self, layer, field_name):
        return layer.fields().indexFromName(field_name)

    def _is_empty_attr_value(self, value):
        if value is None or value == NULL:
            return True
        text = str(value).strip()
        return text == "" or text.upper() == "NULL"

    def _check_required_fields(self, layers, required_fields, extent):
        lines = ["[1] Required field non-empty check"]
        for layer in layers:
            features = self._features_in_extent(layer, extent)
            if not features:
                lines.append("Layer '{}':".format(layer.name()))
                lines.append("  - No features in selected area.")
                continue

            layer_lines = []
            for field_name in required_fields:
                idx = self._field_index(layer, field_name)
                if idx < 0:
                    layer_lines.append("  - Missing field '{}'.".format(field_name))
                    continue
                empty_count = 0
                for feat in features:
                    val = feat[field_name]
                    if self._is_empty_attr_value(val):
                        empty_count += 1
                if empty_count == 0:
                    layer_lines.append("  - Field '{}' OK (no empty values).".format(field_name))
                else:
                    layer_lines.append("  - Field '{}' has {} empty values.".format(field_name, empty_count))

            lines.append("Layer '{}':".format(layer.name()))
            lines.extend(layer_lines)
        return lines

    def _query_requests_autofix(self, query):
        if not query:
            return False
        q = query.lower()
        return any(token in q for token in ["fill", "set", "update", "create", "autofix"])

    def _query_requests_full_layer_fill(self, query):
        if not query:
            return False
        q = query.lower()
        return any(
            phrase in q
            for phrase in [
                "all features",
                "all records",
                "all rows",
                "whole layer",
                "entire layer",
                "all layer",
                "all layers",
                "ensure",
            ]
        )

    def _query_requests_overwrite(self, query):
        if not query:
            return False
        q = query.lower()
        return any(token in q for token in ["update", "replace", "overwrite"])

    def _update_status_badge(self, *_args):
        if self.dialog is None:
            return

        query = self.dialog.rag_query_input.text().strip()
        mode = "overwrite" if self._query_requests_overwrite(query) else "fill-empty"

        full_layer = self._query_requests_full_layer_fill(query)
        scope = "full layer" if full_layer else "selected area"

        selected_ids = set(self.dialog.selected_layer_ids())
        pending = False
        for layer in self._vector_layers():
            if layer.id() in selected_ids and layer.isEditable():
                pending = True
                break

        pending_txt = "yes" if pending else "no"
        self.dialog.set_status_badge(
            "Mode: {} | Scope: {} | Pending edits: {}".format(mode, scope, pending_txt)
        )

    def _on_validation_profile_changed(self, profile_name):
        if self.dialog is None:
            return
        if self.dialog.profile_manage.currentText() != profile_name:
            self.dialog.profile_manage.blockSignals(True)
            self.dialog.profile_manage.setCurrentText(profile_name)
            self.dialog.profile_manage.blockSignals(False)
        self._reload_rules_manager()
        self._refresh_rule_search()

    def _on_rules_profile_changed(self, profile_name):
        if self.dialog is None:
            return
        if self.dialog.rule_profile.currentText() != profile_name:
            self.dialog.rule_profile.blockSignals(True)
            self.dialog.rule_profile.setCurrentText(profile_name)
            self.dialog.rule_profile.blockSignals(False)
        self._reload_rules_manager()
        self._refresh_rule_search()

    def _reload_rules_manager(self):
        if self.dialog is None:
            return
        profile = self.dialog.profile_manage.currentText() or "default"
        self._managed_rules = self.rule_store.load_profile(profile)
        self._refresh_rules_list_widget(select_row=0)
        self.dialog.set_rules_message("Loaded {} guidelines from profile '{}'".format(len(self._managed_rules), profile))

    def _refresh_rules_list_widget(self, select_row=None):
        self.dialog.rules_list.clear()
        for rule in self._managed_rules:
            label = "{} ({})".format(rule.get("name", "Unnamed"), rule.get("id", "no-id"))
            item = QListWidgetItem(label)
            self.dialog.rules_list.addItem(item)
        if self.dialog.rules_list.count() == 0:
            self._populate_rule_editor({})
            return

        if select_row is None or select_row < 0 or select_row >= self.dialog.rules_list.count():
            select_row = 0
        self.dialog.rules_list.setCurrentRow(select_row)

    def _on_rule_selected(self, row):
        if row < 0 or row >= len(self._managed_rules):
            return
        self._populate_rule_editor(self._managed_rules[row])

    def _new_rule(self):
        template = {
            "id": "new-rule-id",
            "name": "New Guideline",
            "description": "Describe what this guideline checks.",
            "keywords": [],
            "action": "require_field_not_empty",
            "params": {"field": "copyright"},
        }
        self._managed_rules.append(template)
        self._refresh_rules_list_widget(select_row=max(0, len(self._managed_rules) - 1))
        self.dialog.set_rules_message("New guideline added in memory. Save profile to persist.")

    def _delete_rule(self):
        row = self.dialog.rules_list.currentRow()
        if row < 0 or row >= len(self._managed_rules):
            self.dialog.set_rules_message("Select a guideline to delete.")
            return
        deleted = self._managed_rules.pop(row)
        self._refresh_rules_list_widget(select_row=max(0, row - 1))
        self.dialog.set_rules_message("Deleted guideline '{}' (save profile to persist).".format(deleted.get("id", "no-id")))

    def _save_rule(self):
        row = self.dialog.rules_list.currentRow()
        try:
            rule = self._read_rule_editor()
        except ValueError as exc:
            self.dialog.set_rules_message(str(exc))
            return

        if row < 0 or row >= len(self._managed_rules):
            self._managed_rules.append(rule)
            row = len(self._managed_rules) - 1
        else:
            self._managed_rules[row] = rule
        self._refresh_rules_list_widget(select_row=row)
        self.dialog.set_rules_message("Guideline saved in memory. Click 'Save Profile' to persist.")

    def _save_rules_profile(self):
        profile = self.dialog.profile_manage.currentText() or "default"
        self.rule_store.save_profile(profile, self._managed_rules)
        self.rule_store._load_rules()
        self._refresh_rule_search()
        self.dialog.set_rules_message("Profile '{}' saved with {} guidelines.".format(profile, len(self._managed_rules)))

    def _populate_rule_editor(self, rule):
        self.dialog.rule_id_input.setText(rule.get("id", ""))
        self.dialog.rule_name_input.setText(rule.get("name", ""))
        self.dialog.rule_description_input.setText(rule.get("description", ""))
        self.dialog.rule_keywords_input.setText(", ".join(rule.get("keywords", [])) if isinstance(rule.get("keywords"), list) else "")
        action = rule.get("action", "require_field_not_empty")
        idx = self.dialog.rule_action_input.findText(action)
        if idx < 0:
            idx = 0
        self.dialog.rule_action_input.setCurrentIndex(idx)
        params = rule.get("params", {}) if isinstance(rule.get("params"), dict) else {}
        self.dialog.rule_params_input.setPlainText(json.dumps(params, indent=2))

    def _read_rule_editor(self):
        rid = self.dialog.rule_id_input.text().strip()
        name = self.dialog.rule_name_input.text().strip()
        desc = self.dialog.rule_description_input.text().strip()
        keywords = [k.strip() for k in self.dialog.rule_keywords_input.text().split(",") if k.strip()]
        action = self.dialog.rule_action_input.currentText().strip()
        params_text = self.dialog.rule_params_input.toPlainText().strip()

        if not rid:
            raise ValueError("Guideline id is required.")
        if not name:
            raise ValueError("Guideline name is required.")
        if not params_text:
            params = {}
        else:
            try:
                params = json.loads(params_text)
            except json.JSONDecodeError as exc:
                params = self._parse_human_friendly_params(action, params_text)
                if params is None:
                    raise ValueError(
                        "Params are not valid JSON, and automatic conversion failed: {}".format(str(exc))
                    )
            if not isinstance(params, dict):
                raise ValueError("Params must be a JSON object.")

        return {
            "id": rid,
            "name": name,
            "description": desc,
            "keywords": keywords,
            "action": action,
            "params": params,
        }

    def _generate_rule_draft_from_manager_prompt(self):
        if self.dialog is None:
            return
        prompt = self.dialog.rule_nl_input.toPlainText().strip()
        if not prompt:
            self.dialog.set_rules_message("Write a plain-language guideline description first.")
            return

        client = self._ollama_client()
        if client is None:
            self.dialog.set_rules_message(
                "Enable 'Use local LLM embeddings (Ollama)' in Validation tab to generate drafts."
            )
            return

        generated = client.generate_rule_json(prompt)
        rule = sanitize_rule(generated)
        if rule is None:
            self.dialog.set_rules_message("Could not generate a valid guideline from the provided text.")
            return

        self._populate_rule_editor(rule)
        self.dialog.set_rules_message("Draft generated. Review and click 'Save Guideline' to add it in memory.")

    def _use_rules_manager_example(self):
        if self.dialog is None:
            return
        idx = self.dialog.rule_nl_examples.currentIndex()
        if idx <= 0:
            self.dialog.set_rules_message("Choose an example from the dropdown first.")
            return
        example_text = self.dialog.rule_nl_examples.currentText().strip()
        self.dialog.rule_nl_input.setPlainText(example_text)
        self.dialog.set_rules_message("Example inserted. Click 'Generate Guideline Draft' to convert it.")

    def _parse_human_friendly_params(self, action, params_text):
        client = self._ollama_client()
        if client is not None:
            generated = client.generate_params_json(action, params_text)
            if isinstance(generated, dict):
                return generated
        return self._heuristic_parse_params(action, params_text)

    def _heuristic_parse_params(self, action, text):
        raw = (text or "").strip()
        if not raw:
            return {}
        lower = raw.lower()

        # Quick key=value support (semicolon or newline separated)
        kv_pairs = {}
        parts = [p.strip() for p in re.split(r"[;\n]", raw) if p.strip()]
        for part in parts:
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if not key:
                continue
            if value.lower() in ("true", "false"):
                kv_pairs[key] = value.lower() == "true"
            else:
                try:
                    kv_pairs[key] = float(value) if "." in value else int(value)
                except ValueError:
                    kv_pairs[key] = value
        if kv_pairs:
            return kv_pairs

        if action == "require_field_not_empty":
            m = re.search(r"field\s+([a-zA-Z_][a-zA-Z0-9_]*)", raw)
            if m:
                return {"field": m.group(1)}
            m = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*)\s+(must|should)\s+(be\s+)?(mandatory|required|not\s+empty)", lower)
            if m:
                return {"field": m.group(1)}
            return {"field": "field_name"}

        if action == "set_field_if_empty":
            field = "field_name"
            m_field = re.search(r"field\s+([a-zA-Z_][a-zA-Z0-9_]*)", raw)
            if m_field:
                field = m_field.group(1)
            else:
                m_field = re.search(r"set\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+(field\s+)?(to|with)", lower)
                if m_field:
                    field = m_field.group(1)

            quoted = re.search(r'"([^"]+)"|\'([^\']+)\'', raw)
            if quoted:
                value_template = quoted.group(1) or quoted.group(2)
            elif "today" in lower or "date" in lower:
                value_template = "{date}"
            elif "year" in lower:
                value_template = "{year}"
            else:
                value_template = "Auto value"

            return {
                "field": field,
                "value_template": value_template,
                "create_if_missing": True,
                "fallback_to_full_layer_when_extent_empty": True,
            }

        if action == "check_road_endpoint_snap_candidates":
            tolerance = 0.01
            m_tol = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(m|meter|meters)?", lower)
            if m_tol:
                try:
                    tolerance = float(m_tol.group(1))
                except ValueError:
                    tolerance = 0.01

            elev_field = "elevation"
            if "osm_id" in lower:
                elev_field = "osm_id"
            elif "z" in lower or "height" in lower:
                elev_field = "elevation"

            return {
                "tolerance_m": tolerance,
                "elevation_field": elev_field,
                "select_candidates": "select" in lower or "highlight" in lower,
            }

        if action == "create_bridge_segment_at_road_river_crossing":
            m_half = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(m|meter|meters)?", lower)
            half_length = 1.0
            if m_half:
                try:
                    half_length = float(m_half.group(1))
                except ValueError:
                    half_length = 1.0

            return {
                "road_layer_contains": "road",
                "river_layer_contains": "river",
                "name_field": "name",
                "name_value": "bridge",
                "segment_half_length": half_length,
                "create_if_missing": True,
            }

        return {}

    def _refresh_rule_search(self):
        if self.dialog is None:
            return
        profile = self.dialog.rule_profile.currentText() or "default"
        rules = self.rule_store.active_rules(profile)
        term = self.dialog.rule_search_input.text().strip().lower()

        self.dialog.rule_search_results.clear()
        for rule in rules:
            hay = " ".join([
                rule.get("id", ""),
                rule.get("name", ""),
                rule.get("description", ""),
                " ".join(rule.get("keywords", [])),
                rule.get("action", ""),
            ]).lower()
            if term and term not in hay:
                continue
            label = "{} ({})".format(rule.get("name", "Unnamed"), rule.get("id", "no-id"))
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, rule)
            self.dialog.rule_search_results.addItem(item)

    def _use_selected_rule_in_query(self):
        item = self.dialog.rule_search_results.currentItem()
        if item is None:
            return
        rule = item.data(Qt.UserRole) or {}
        self.dialog.rag_query_input.setText(self._rule_to_query_template(rule))
        self._update_status_badge()

    def _rule_to_query_template(self, rule):
        action = rule.get("action", "")
        params = rule.get("params", {}) if isinstance(rule.get("params"), dict) else {}
        if action == "require_field_not_empty":
            field = params.get("field", "field")
            return "ensure {} field is not empty".format(field)
        if action == "set_field_if_empty":
            field = params.get("field", "field")
            return "update {} field with the text \"example\"".format(field)
        if action == "check_road_endpoint_snap_candidates":
            return "check road endpoint topology and elevation snap candidates"
        if action == "create_bridge_segment_at_road_river_crossing":
            return "if a road is crossing a river create a segment for the crossing and name that element bridge"
        return "run guideline {}".format(rule.get("id", "unknown"))

    def _prepare_layers_for_writes(self, layers):
        lines = ["[0a] Preparing layers for write session"]
        for layer in layers:
            if self._layer_is_read_only(layer):
                lines.append("Layer '{}': is read-only; cannot enter edit mode.".format(layer.name()))
                continue

            if layer.isEditable():
                lines.append("Layer '{}': already in edit mode.".format(layer.name()))
                continue

            if layer.startEditing():
                if hasattr(layer, "triggerRepaint"):
                    try:
                        layer.triggerRepaint()
                    except Exception:
                        pass
                lines.append("Layer '{}': entered edit mode (pending save).".format(layer.name()))
            else:
                lines.append("Layer '{}': failed to enter edit mode.".format(layer.name()))
        return lines

    def _check_schema_homogeneous(self, layers):
        lines = ["[2] Field-name homogeneity across layers"]
        field_sets = {}
        for layer in layers:
            field_sets[layer.name()] = {field.name() for field in layer.fields()}

        if not field_sets:
            lines.append("No layers to compare.")
            return lines

        common = set.intersection(*field_sets.values()) if len(field_sets) > 1 else next(iter(field_sets.values()))
        union = set.union(*field_sets.values())
        lines.append("Common fields: {}".format(", ".join(sorted(common)) if common else "none"))

        for layer_name, fields in field_sets.items():
            missing = sorted(list(union - fields))
            if missing:
                lines.append("Layer '{}' missing fields: {}".format(layer_name, ", ".join(missing)))
            else:
                lines.append("Layer '{}' has full union schema.".format(layer_name))
        return lines

    def _check_geometry_validity(self, layers, extent):
        lines = ["[3] Geometry validity (topological correctness)"]
        for layer in layers:
            features = self._features_in_extent(layer, extent)
            if not features:
                lines.append("Layer '{}': no features in selected area.".format(layer.name()))
                continue

            # Prefer native QGIS validity algorithm, fallback to direct GEOS checks.
            try:
                result = processing.run(
                    "native:checkvalidity",
                    {
                        "INPUT_LAYER": layer,
                        "METHOD": 2,
                        "IGNORE_RING_SELF_INTERSECTION": False,
                        "VALID_OUTPUT": "memory:",
                        "INVALID_OUTPUT": "memory:",
                        "ERROR_OUTPUT": "memory:",
                    },
                )
                invalid_layer = result.get("INVALID_OUTPUT")
                invalid_total = invalid_layer.featureCount() if invalid_layer else 0
                lines.append(
                    "Layer '{}': {} invalid geometries (native checker on full layer), {} features in selected area.".format(
                        layer.name(), invalid_total, len(features)
                    )
                )
            except Exception:
                invalid = 0
                for feat in features:
                    geom = feat.geometry()
                    if geom is None or geom.isEmpty() or (not geom.isGeosValid()):
                        invalid += 1
                if invalid == 0:
                    lines.append("Layer '{}': all {} geometries valid (fallback checker).".format(layer.name(), len(features)))
                else:
                    lines.append(
                        "Layer '{}': {} invalid geometries out of {} (fallback checker).".format(
                            layer.name(), invalid, len(features)
                        )
                    )
        return lines

    def _line_endpoints(self, geom):
        if geom is None or geom.isEmpty():
            return []
        endpoints = []
        gtype = QgsWkbTypes.geometryType(geom.wkbType())
        if gtype != QgsWkbTypes.LineGeometry:
            return endpoints

        if geom.isMultipart():
            multi = geom.asMultiPolyline()
            for part in multi:
                if len(part) >= 2:
                    endpoints.append(part[0])
                    endpoints.append(part[-1])
        else:
            line = geom.asPolyline()
            if len(line) >= 2:
                endpoints.append(line[0])
                endpoints.append(line[-1])
        return endpoints

    def _distance(self, p1, p2):
        dx = p1.x() - p2.x()
        dy = p1.y() - p2.y()
        return math.sqrt(dx * dx + dy * dy)

    def _check_road_endpoint_connectivity(self, layers, extent, tolerance_m, elevation_field, select_candidates=False):
        lines = ["[4] Road endpoint near-connectivity and elevation"]
        line_layers = [layer for layer in layers if layer.geometryType() == QgsWkbTypes.LineGeometry]
        if not line_layers:
            lines.append("No line layers selected.")
            return lines

        for layer in line_layers:
            features = self._features_in_extent(layer, extent)
            if len(features) < 2:
                lines.append("Layer '{}': insufficient features for connectivity checks.".format(layer.name()))
                continue

            endpoint_records = []
            for feat in features:
                elev = feat[elevation_field] if self._field_index(layer, elevation_field) >= 0 else None
                for pt in self._line_endpoints(feat.geometry()):
                    endpoint_records.append((feat.id(), pt, elev))

            candidates = 0
            matched_feature_ids = set()
            for i in range(len(endpoint_records)):
                fid_a, pt_a, elev_a = endpoint_records[i]
                for j in range(i + 1, len(endpoint_records)):
                    fid_b, pt_b, elev_b = endpoint_records[j]
                    if fid_a == fid_b:
                        continue
                    dist = self._distance(pt_a, pt_b)
                    if dist <= tolerance_m:
                        if elev_a is not None and elev_b is not None and str(elev_a) == str(elev_b):
                            candidates += 1
                            matched_feature_ids.add(fid_a)
                            matched_feature_ids.add(fid_b)
            lines.append(
                "Layer '{}': {} near endpoint pairs within {:.4f} m with matching elevation.".format(
                    layer.name(), candidates, tolerance_m
                )
            )
            if select_candidates:
                layer.selectByIds(sorted(matched_feature_ids))
                lines.append(
                    "Layer '{}': selected {} candidate features in map window.".format(
                        layer.name(), len(matched_feature_ids)
                    )
                )
                self._refresh_highlighted_elements_panel(line_layers)
        lines.append("Note: this check identifies snap candidates; automatic line snapping is not applied.")
        return lines

    def _active_profile(self):
        if self.dialog is None:
            return "default"
        return self.dialog.rule_profile.currentText() or "default"

    def _ollama_client(self):
        if self.dialog is None:
            return None
        if not self.dialog.chk_use_llm.isChecked():
            return None
        return OllamaClient(
            self.dialog.ollama_url.text().strip(),
            self.dialog.ollama_model.text().strip(),
        )

    def add_rule_from_prompt(self):
        prompt = self.dialog.new_rule_prompt.text().strip() if self.dialog else ""
        if not prompt:
            QMessageBox.information(self.iface.mainWindow(), "Guideline Authoring", "Enter a prompt to generate a guideline.")
            return

        client = self._ollama_client()
        if client is None:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Guideline Authoring",
                "Enable 'Use local LLM embeddings (Ollama)' to generate guidelines from prompt.",
            )
            return

        generated = client.generate_rule_json(prompt)
        rule = sanitize_rule(generated)
        if rule is None:
            QMessageBox.warning(self.iface.mainWindow(), "Guideline Authoring", "LLM did not return a valid guideline JSON.")
            return

        profile = self._active_profile()
        self.rule_store.append_rule_to_profile(profile, rule)
        self._reload_rules_manager()
        self._refresh_rule_search()
        self.dialog.new_rule_prompt.clear()
        QMessageBox.information(
            self.iface.mainWindow(),
            "Guideline Authoring",
            "Guideline '{}' added to profile '{}'".format(rule.get("id", "generated"), profile),
        )

    def _run_topology_repair(self, layers, tolerance, preview_only):
        lines = ["[4b] Automatic topology repair workflow"]
        line_layers = [layer for layer in layers if layer.geometryType() == QgsWkbTypes.LineGeometry]
        if not line_layers:
            lines.append("No line layers selected for repair.")
            return lines

        behavior_prefer_nodes = 0
        for layer in line_layers:
            try:
                output_layer = processing.run(
                    "native:snapgeometries",
                    {
                        "INPUT": layer,
                        "REFERENCE_LAYER": layer,
                        "TOLERANCE": tolerance,
                        "BEHAVIOR": behavior_prefer_nodes,
                        "OUTPUT": "memory:",
                    },
                ).get("OUTPUT")
            except Exception as exc:
                lines.append("Layer '{}': repair failed: {}".format(layer.name(), str(exc)))
                continue

            changed = self._count_geometry_changes(layer, output_layer)
            lines.append(
                "Layer '{}': {} geometries changed by snap (tolerance {:.4f} m).".format(
                    layer.name(), changed, tolerance
                )
            )

            if preview_only:
                output_layer.setName("{}_repair_preview".format(layer.name()))
                QgsProject.instance().addMapLayer(output_layer)
                lines.append("Layer '{}': preview layer added to project.".format(layer.name()))
            else:
                updated = self._commit_snapped_geometries(layer, output_layer)
                lines.append("Layer '{}': committed {} geometry updates.".format(layer.name(), updated))
        return lines

    def connect_highlighted_elements(self):
        selected_ids = self.dialog.selected_layer_ids() if self.dialog else []
        if not selected_ids:
            QMessageBox.warning(self.iface.mainWindow(), "No Layers", "Select at least one layer.")
            return

        layers_by_id = {layer.id(): layer for layer in self._vector_layers()}
        selected_layers = [layers_by_id[layer_id] for layer_id in selected_ids if layer_id in layers_by_id]
        lines = self._run_topology_repair_on_selected(
            selected_layers,
            tolerance=self.dialog.repair_tolerance_spin.value(),
            preview_only=self.dialog.chk_topology_preview_only.isChecked(),
        )
        self._refresh_highlighted_elements_panel(selected_layers)
        report = "\n".join(lines)
        if self.dialog is not None:
            self.dialog.results.setPlainText(report)

    def _refresh_highlighted_elements_panel(self, layers):
        if self.dialog is None:
            return
        rows = []
        for layer in layers:
            if layer.geometryType() != QgsWkbTypes.LineGeometry:
                continue
            selected_set = set(layer.selectedFeatureIds())
            if not selected_set:
                continue
            osm_idx = self._field_index(layer, "osm_id")
            for feat in layer.getFeatures():
                if feat.id() not in selected_set:
                    continue
                row = "{} | fid={}".format(layer.name(), feat.id())
                if osm_idx >= 0:
                    osm_val = feat["osm_id"]
                    row += " | osm_id={}".format("" if osm_val in (None, NULL) else str(osm_val))
                rows.append(row)
        self.dialog.set_highlighted_elements(rows)

    def _run_topology_repair_on_selected(self, layers, tolerance, preview_only):
        lines = ["[4c] Topology connection on highlighted elements"]
        line_layers = [layer for layer in layers if layer.geometryType() == QgsWkbTypes.LineGeometry]
        if not line_layers:
            lines.append("No line layers selected.")
            return lines

        behavior_prefer_nodes = 0
        for layer in line_layers:
            selected_feature_ids = set(layer.selectedFeatureIds())
            if len(selected_feature_ids) < 2:
                lines.append("Layer '{}': select at least 2 elements to connect.".format(layer.name()))
                continue

            try:
                output_layer = processing.run(
                    "native:snapgeometries",
                    {
                        "INPUT": layer,
                        "REFERENCE_LAYER": layer,
                        "TOLERANCE": tolerance,
                        "BEHAVIOR": behavior_prefer_nodes,
                        "OUTPUT": "memory:",
                    },
                ).get("OUTPUT")
            except Exception as exc:
                lines.append("Layer '{}': connect failed: {}".format(layer.name(), str(exc)))
                continue

            changed = self._count_geometry_changes(layer, output_layer, feature_ids=selected_feature_ids)
            lines.append(
                "Layer '{}': {} highlighted geometries changed by snap (tolerance {:.4f} m).".format(
                    layer.name(), changed, tolerance
                )
            )

            if preview_only:
                output_layer.setName("{}_highlighted_connect_preview".format(layer.name()))
                QgsProject.instance().addMapLayer(output_layer)
                lines.append("Layer '{}': preview layer added to project.".format(layer.name()))
            else:
                updated = self._commit_snapped_geometries(layer, output_layer, feature_ids=selected_feature_ids)
                lines.append("Layer '{}': committed {} highlighted geometry updates.".format(layer.name(), updated))
        return lines

    def _count_geometry_changes(self, source_layer, snapped_layer, feature_ids=None):
        if snapped_layer is None:
            return 0
        changed = 0
        selected_set = set(feature_ids) if feature_ids is not None else None
        src_by_id = {feat.id(): feat.geometry() for feat in source_layer.getFeatures()}
        for feat in snapped_layer.getFeatures():
            if selected_set is not None and feat.id() not in selected_set:
                continue
            src_geom = src_by_id.get(feat.id())
            if src_geom is None:
                continue
            if not src_geom.equals(feat.geometry()):
                changed += 1
        return changed

    def _commit_snapped_geometries(self, source_layer, snapped_layer, feature_ids=None):
        if snapped_layer is None:
            return 0
        updated = 0
        selected_set = set(feature_ids) if feature_ids is not None else None
        was_editable = source_layer.isEditable()
        if not was_editable:
            source_layer.startEditing()
        for feat in snapped_layer.getFeatures():
            if selected_set is not None and feat.id() not in selected_set:
                continue
            source_feat = source_layer.getFeature(feat.id())
            if not source_feat.isValid():
                continue
            if source_feat.geometry().equals(feat.geometry()):
                continue
            if source_layer.changeGeometry(feat.id(), QgsGeometry(feat.geometry())):
                updated += 1
        if updated > 0 and not was_editable:
            source_layer.commitChanges()
        elif updated == 0 and not was_editable:
            source_layer.rollBack()
        return updated

    def _export_report_if_requested(self, report_text, report_lines):
        if self.dialog is None:
            return
        if not any([
            self.dialog.chk_export_json.isChecked(),
            self.dialog.chk_export_html.isChecked(),
            self.dialog.chk_export_pdf.isChecked(),
        ]):
            return
        out_dir = (self.dialog.export_dir or "").strip()
        if not out_dir:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary = {
            "timestamp": timestamp,
            "profile": self._active_profile(),
            "area": {
                "xmin": self.picked_extent.xMinimum(),
                "ymin": self.picked_extent.yMinimum(),
                "xmax": self.picked_extent.xMaximum(),
                "ymax": self.picked_extent.yMaximum(),
            },
            "report_lines": report_lines,
        }

        outputs = []
        if self.dialog.chk_export_json.isChecked():
            outputs.append(export_report_json(out_dir, "dqcv_report_{}".format(timestamp), summary))
        if self.dialog.chk_export_html.isChecked():
            outputs.append(export_report_html(out_dir, "dqcv_report_{}".format(timestamp), report_text, summary))
        if self.dialog.chk_export_pdf.isChecked():
            outputs.append(export_report_pdf(out_dir, "dqcv_report_{}".format(timestamp), report_text, summary))

        if outputs:
            QMessageBox.information(
                self.iface.mainWindow(),
                "Report Export",
                "Saved report files:\n{}".format("\n".join(outputs)),
            )

    def store_features_in_immutable_catalogue(self):
        if self.dialog is None:
            return

        selected_ids = self.dialog.selected_layer_ids()
        if not selected_ids:
            QMessageBox.warning(self.iface.mainWindow(), "Immutable Catalogue", "Select at least one layer first.")
            return

        extent = self.picked_extent or self.iface.mapCanvas().extent()
        layers_by_id = {layer.id(): layer for layer in self._vector_layers()}
        selected_layers = [layers_by_id[layer_id] for layer_id in selected_ids if layer_id in layers_by_id]
        if not selected_layers:
            QMessageBox.warning(self.iface.mainWindow(), "Immutable Catalogue", "No valid vector layers available.")
            return

        entries = []
        minimal_fields = [name for name, _default in self.LIABILITY_CLAIMS_MINIMAL_FIELDS]
        for layer in selected_layers:
            for feat in self._features_in_extent(layer, extent):
                attrs = {}
                for field_name in minimal_fields:
                    idx = self._field_index(layer, field_name)
                    attrs[field_name] = feat[field_name] if idx >= 0 else None

                geom = feat.geometry()
                geom_wkt = geom.asWkt() if geom is not None and not geom.isEmpty() else ""
                digest_payload = {
                    "layer": layer.name(),
                    "fid": int(feat.id()),
                    "geometry_wkt": geom_wkt,
                    "liability_claims": attrs,
                }
                digest = hashlib.sha256(json.dumps(digest_payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()

                entries.append({
                    "layer": layer.name(),
                    "fid": int(feat.id()),
                    "digest_sha256": digest,
                    "liability_claims": attrs,
                })

        if not entries:
            QMessageBox.information(
                self.iface.mainWindow(),
                "Immutable Catalogue",
                "No features found in the selected area to prepare for immutable catalogue storage.",
            )
            return

        out_dir = (self.dialog.export_dir or "").strip()
        if not out_dir:
            out_dir = os.path.join(self.plugin_dir, "immutable_catalogue_exports")
        os.makedirs(out_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(out_dir, "immutable_catalogue_candidate_{}.json".format(timestamp))
        payload = {
            "created_at": datetime.now().isoformat(),
            "profile": self._active_profile(),
            "candidate_type": "immutable_catalogue_feature_package",
            "note": "Candidate package for possible immutable catalogue storage.",
            "stac_liability_claims_fields": minimal_fields,
            "feature_count": len(entries),
            "features": entries,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        existing = self.dialog.results.toPlainText().strip()
        line = "[Immutable Catalogue] Candidate package saved: {}".format(output_path)
        self.dialog.results.setPlainText((existing + "\n\n" + line).strip())
        QMessageBox.information(
            self.iface.mainWindow(),
            "Immutable Catalogue",
            "Candidate package saved for possible immutable catalogue storage:\n{}".format(output_path),
        )

        send_now = QMessageBox.question(
            self.iface.mainWindow(),
            "Immutable Catalogue",
            "Do you want to send this candidate package to an Immutable Catalogue endpoint now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if send_now != QMessageBox.Yes:
            return

        endpoint_url, ok = QInputDialog.getText(
            self.iface.mainWindow(),
            "Immutable Catalogue Endpoint",
            "POST endpoint URL:",
            QLineEdit.Normal,
            "http://localhost:8080/immutable-catalogue/ingest",
        )
        if not ok:
            return
        endpoint_url = (endpoint_url or "").strip()
        if not endpoint_url:
            QMessageBox.warning(self.iface.mainWindow(), "Immutable Catalogue", "Endpoint URL is required.")
            return

        token, token_ok = QInputDialog.getText(
            self.iface.mainWindow(),
            "Immutable Catalogue Auth",
            "Bearer token (optional):",
            QLineEdit.Password,
            "",
        )
        if not token_ok:
            return

        success, status_code, response_text = self._post_immutable_catalogue_candidate(
            endpoint_url,
            (token or "").strip(),
            payload,
        )
        response_excerpt = (response_text or "").strip()
        if len(response_excerpt) > 500:
            response_excerpt = response_excerpt[:500] + "..."

        if success:
            msg = "Published to Immutable Catalogue endpoint. Status: {}".format(status_code)
            if response_excerpt:
                msg = msg + "\nResponse: {}".format(response_excerpt)
            QMessageBox.information(self.iface.mainWindow(), "Immutable Catalogue", msg)
        else:
            msg = "Failed to publish to Immutable Catalogue endpoint. Status: {}".format(status_code)
            if response_excerpt:
                msg = msg + "\nResponse: {}".format(response_excerpt)
            QMessageBox.warning(self.iface.mainWindow(), "Immutable Catalogue", msg)

        updated = self.dialog.results.toPlainText().strip()
        updated_line = "[Immutable Catalogue] Publish status={} endpoint={}".format(status_code, endpoint_url)
        self.dialog.results.setPlainText((updated + "\n" + updated_line).strip())

    def _post_immutable_catalogue_candidate(self, endpoint_url, bearer_token, payload):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
        }
        if bearer_token:
            headers["Authorization"] = "Bearer {}".format(bearer_token)

        body = json.dumps(payload, default=str).encode("utf-8")
        request = urllib.request.Request(endpoint_url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                raw = response.read()
                text = raw.decode("utf-8", errors="replace") if raw else ""
                return True, getattr(response, "status", 200), text
        except urllib.error.HTTPError as exc:
            raw = exc.read() if hasattr(exc, "read") else b""
            text = raw.decode("utf-8", errors="replace") if raw else str(exc)
            return False, exc.code, text
        except urllib.error.URLError as exc:
            return False, 0, str(exc)
        except Exception as exc:
            return False, 0, str(exc)

    def _run_rag_rules(self, layers, extent, query, apply_autofix, active_rules=None, active_profile=None):
        lines = ["[5] Local RAG guideline retrieval and execution"]
        if not query:
            query = "quality validation for attributes and topology"

        self.rule_store._load_rules()
        if active_profile is None:
            active_profile = self._active_profile()
        if active_rules is None:
            active_rules = self.rule_store.active_rules(active_profile)

        retrieved = []
        client = self._ollama_client()
        if client is not None:
            try:
                retrieved = self.embedding_retriever.retrieve(active_rules, query, client, top_k=5)
            except Exception:
                retrieved = []

        if not retrieved:
            retrieved = self.rule_store.retrieve_with_rules(active_rules, query, top_k=5)

        if not retrieved:
            lines.append("No relevant guidelines retrieved for query: '{}'".format(query))
            return lines

        lines.append("Profile: '{}'".format(active_profile))
        lines.append("Retrieved guidelines for query '{}':".format(query))
        for rule in retrieved:
            lines.append("- {} ({})".format(rule.get("name", "Unnamed guideline"), rule.get("id", "no-id")))

        for rule in retrieved:
            action = rule.get("action")
            params = rule.get("params", {})

            if action == "require_field_not_empty":
                field = params.get("field")
                if not field:
                    continue
                lines.extend(self._check_required_fields(layers, [field], extent))

            elif action == "set_field_if_empty":
                field = params.get("field")
                value_template = params.get("value_template", "")
                create_if_missing = bool(params.get("create_if_missing", True))
                fallback_to_full_layer = bool(params.get("fallback_to_full_layer_when_extent_empty", True))
                force_full_layer_fill = self._query_requests_full_layer_fill(query)
                overwrite_existing = self._query_requests_overwrite(query)
                if not field:
                    continue
                if apply_autofix:
                    literal_value = self._extract_fill_literal_from_query(query, field)
                    dynamic_value = self._extract_dynamic_fill_value_from_query(query)
                    value = self._compose_fill_value(query, field, literal_value, dynamic_value, value_template)
                    if literal_value is not None and dynamic_value is not None:
                        lines.append(
                            "Guideline '{}' using combined value for field '{}': '{}' + '{}'".format(
                                rule.get("id", "no-id"), field, literal_value, dynamic_value
                            )
                        )
                    elif literal_value is not None:
                        lines.append(
                            "Guideline '{}' using value override from query for field '{}': '{}'".format(
                                rule.get("id", "no-id"), field, literal_value
                            )
                        )
                    elif dynamic_value is not None:
                        lines.append(
                            "Guideline '{}' using dynamic date/time from query for field '{}': '{}'".format(
                                rule.get("id", "no-id"), field, dynamic_value
                            )
                        )
                    lines.extend(
                        self._apply_fill_if_empty(
                            layers,
                            extent,
                            field,
                            value,
                            create_if_missing=create_if_missing,
                            fallback_to_full_layer_when_extent_empty=fallback_to_full_layer,
                            force_full_layer_fill=force_full_layer_fill,
                            overwrite_existing=overwrite_existing,
                        )
                    )
                else:
                    lines.append(
                        "Guideline '{}' proposes autofix for field '{}' but autofix is disabled.".format(
                            rule.get("id", "no-id"), field
                        )
                    )

            elif action == "check_road_endpoint_snap_candidates":
                tolerance = float(params.get("tolerance_m", 0.01))
                elev_field = params.get("elevation_field", "elevation")
                select_candidates = bool(params.get("select_candidates", False))
                lines.extend(
                    self._check_road_endpoint_connectivity(
                        layers,
                        extent,
                        tolerance,
                        elev_field,
                        select_candidates=select_candidates,
                    )
                )

            elif action == "create_bridge_segment_at_road_river_crossing":
                lines.extend(
                    self._create_bridge_segments_at_road_river_crossings(
                        layers,
                        extent,
                        params,
                        create_segments=apply_autofix,
                    )
                )

            else:
                lines.append("Guideline '{}' has unsupported operation '{}'.".format(rule.get("id", "no-id"), action))

        return lines

    def _layers_by_name_keyword(self, layers, keyword):
        key = (keyword or "").strip().lower()
        if not key:
            return []
        return [layer for layer in layers if key in layer.name().lower()]

    def _create_bridge_segments_at_road_river_crossings(self, layers, extent, params, create_segments):
        lines = ["[5b] Road-river crossing bridge segment workflow"]
        road_key = (params.get("road_layer_contains") or "road").strip().lower()
        river_key = (params.get("river_layer_contains") or "river").strip().lower()
        name_field = (params.get("name_field") or "name").strip()
        name_value = (params.get("name_value") or "bridge").strip()
        create_if_missing = bool(params.get("create_if_missing", True))
        try:
            segment_half_length = float(params.get("segment_half_length", 1.0))
        except (TypeError, ValueError):
            segment_half_length = 1.0
        if segment_half_length <= 0:
            segment_half_length = 1.0

        line_layers = [layer for layer in layers if layer.geometryType() == QgsWkbTypes.LineGeometry]
        road_layers = self._layers_by_name_keyword(line_layers, road_key)
        river_layers = self._layers_by_name_keyword(line_layers, river_key)

        if not road_layers:
            lines.append("No road layers found (name contains '{}').".format(road_key))
            return lines
        if not river_layers:
            lines.append("No river layers found (name contains '{}').".format(river_key))
            return lines

        total_crossings = 0
        total_created = 0
        for road_layer in road_layers:
            road_feats = self._features_in_extent(road_layer, extent)
            if not road_feats:
                lines.append("Road layer '{}': no features in selected area.".format(road_layer.name()))
                continue

            if create_segments and (not road_layer.isEditable()) and (not road_layer.startEditing()):
                lines.append("Road layer '{}': could not start edit mode for bridge creation.".format(road_layer.name()))
                continue

            if create_segments and create_if_missing:
                idx, created = self._ensure_text_field(road_layer, name_field)
                if idx < 0:
                    lines.append("Road layer '{}': could not create/access field '{}'.".format(road_layer.name(), name_field))
                    continue
                if created:
                    lines.append("Road layer '{}': created field '{}' for bridge naming.".format(road_layer.name(), name_field))

            name_idx = self._field_index(road_layer, name_field)

            created_here = 0
            crossing_here = 0
            for river_layer in river_layers:
                river_feats = self._features_in_extent(river_layer, extent)
                if not river_feats:
                    continue

                for road_feat in road_feats:
                    road_geom = road_feat.geometry()
                    if road_geom is None or road_geom.isEmpty():
                        continue
                    for river_feat in river_feats:
                        river_geom = river_feat.geometry()
                        if river_geom is None or river_geom.isEmpty():
                            continue
                        inter = road_geom.intersection(river_geom)
                        if inter is None or inter.isEmpty():
                            continue

                        point_geoms = self._intersection_point_geometries(inter)
                        if not point_geoms:
                            if QgsWkbTypes.geometryType(inter.wkbType()) == QgsWkbTypes.LineGeometry:
                                crossing_here += 1
                                if create_segments and self._add_bridge_feature(road_layer, inter, name_idx, name_value):
                                    created_here += 1
                            continue

                        for point_geom in point_geoms:
                            segment = road_geom.intersection(point_geom.buffer(segment_half_length, 8))
                            if segment is None or segment.isEmpty():
                                continue
                            if QgsWkbTypes.geometryType(segment.wkbType()) != QgsWkbTypes.LineGeometry:
                                continue
                            crossing_here += 1
                            if create_segments and self._add_bridge_feature(road_layer, segment, name_idx, name_value):
                                created_here += 1

            total_crossings += crossing_here
            total_created += created_here
            if create_segments:
                lines.append(
                    "Road layer '{}': found {} crossing candidates and created {} bridge segment features.".format(
                        road_layer.name(), crossing_here, created_here
                    )
                )
            else:
                lines.append(
                    "Road layer '{}': found {} crossing candidates (autofix disabled; no features created).".format(
                        road_layer.name(), crossing_here
                    )
                )

        if create_segments:
            lines.append("Total crossings: {} | Total bridge segments created: {}".format(total_crossings, total_created))
        else:
            lines.append("Total crossings detected: {} (enable autofix/create to persist bridge segments).".format(total_crossings))
        return lines

    def _intersection_point_geometries(self, geom):
        out = []
        if geom is None or geom.isEmpty():
            return out

        gtype = QgsWkbTypes.geometryType(geom.wkbType())
        if gtype == QgsWkbTypes.PointGeometry:
            if geom.isMultipart():
                for pt in geom.asMultiPoint():
                    out.append(QgsGeometry.fromPointXY(QgsPointXY(pt.x(), pt.y())))
            else:
                pt = geom.asPoint()
                out.append(QgsGeometry.fromPointXY(QgsPointXY(pt.x(), pt.y())))
            return out

        collection = geom.asGeometryCollection() if hasattr(geom, "asGeometryCollection") else []
        for part in collection:
            if part is None or part.isEmpty():
                continue
            if QgsWkbTypes.geometryType(part.wkbType()) == QgsWkbTypes.PointGeometry:
                if part.isMultipart():
                    for pt in part.asMultiPoint():
                        out.append(QgsGeometry.fromPointXY(QgsPointXY(pt.x(), pt.y())))
                else:
                    pt = part.asPoint()
                    out.append(QgsGeometry.fromPointXY(QgsPointXY(pt.x(), pt.y())))
        return out

    def _add_bridge_feature(self, layer, geom, name_idx, name_value):
        if geom is None or geom.isEmpty():
            return False
        if not self._layer_can_add_features(layer):
            return False
        feat = QgsFeature(layer.fields())
        feat.setGeometry(QgsGeometry(geom))
        if name_idx >= 0:
            feat.setAttribute(name_idx, name_value)
        ok, _ = layer.dataProvider().addFeatures([feat])
        if ok:
            layer.updateExtents()
            if hasattr(layer, "triggerRepaint"):
                try:
                    layer.triggerRepaint()
                except Exception:
                    pass
        return bool(ok)

    def _extract_fill_literal_from_query(self, query, field_name):
        if not query:
            return None

        generic_patterns = [
            r'"([^"]+)"',
            r"'([^']+)'",
        ]
        patterns = [
            r'fill\s+(?:the\s+)?' + re.escape(field_name) + r'\s+(?:attribute\s+|field\s+)?(?:with|as|to)\s+"([^"]+)"',
            r'set\s+(?:the\s+)?' + re.escape(field_name) + r'\s+(?:attribute\s+|field\s+)?(?:with|as|to)\s+"([^"]+)"',
            r'update\s+(?:the\s+)?' + re.escape(field_name) + r'\s+(?:attribute\s+|field\s+)?(?:with|as|to)\s+the\s+text\s+"([^"]+)"',
            r'update\s+(?:the\s+)?' + re.escape(field_name) + r'\s+(?:attribute\s+|field\s+)?(?:with|as|to)\s+text\s+"([^"]+)"',
            r'update\s+(?:the\s+)?' + re.escape(field_name) + r'\s+(?:attribute\s+|field\s+)?(?:with|as|to)\s+"([^"]+)"',
            r'fill\s+(?:with|as|to)\s+"([^"]+)"',
            r'set\s+(?:with|as|to)\s+"([^"]+)"',
            r'update\s+(?:with|as|to)\s+the\s+text\s+"([^"]+)"',
            r'update\s+(?:with|as|to)\s+text\s+"([^"]+)"',
            r'update\s+(?:with|as|to)\s+"([^"]+)"',
            r'fill\s+(?:the\s+)?' + re.escape(field_name) + r'\s+(?:attribute\s+|field\s+)?(?:with|as|to)\s+\'([^\']+)\'',
            r'set\s+(?:the\s+)?' + re.escape(field_name) + r'\s+(?:attribute\s+|field\s+)?(?:with|as|to)\s+\'([^\']+)\'',
            r'update\s+(?:the\s+)?' + re.escape(field_name) + r'\s+(?:attribute\s+|field\s+)?(?:with|as|to)\s+the\s+text\s+\'([^\']+)\'',
            r'update\s+(?:the\s+)?' + re.escape(field_name) + r'\s+(?:attribute\s+|field\s+)?(?:with|as|to)\s+text\s+\'([^\']+)\'',
            r'update\s+(?:the\s+)?' + re.escape(field_name) + r'\s+(?:attribute\s+|field\s+)?(?:with|as|to)\s+\'([^\']+)\'',
        ]
        for pattern in patterns:
            match = re.search(pattern, query, flags=re.IGNORECASE)
            if match:
                candidate = (match.group(1) or "").strip()
                if candidate:
                    return candidate

        for pattern in generic_patterns:
            match = re.search(pattern, query)
            if match:
                candidate = (match.group(1) or "").strip()
                if candidate:
                    return candidate
        return None

    def _extract_dynamic_fill_value_from_query(self, query):
        if not query:
            return None
        q = query.lower()
        now = datetime.now()

        if re.search(r"\b(this|current)\s+year\b", q):
            return str(now.year)
        if re.search(r"\b(today|current)\s+date\b", q) or re.search(r"\btoday\b", q):
            return now.strftime("%Y-%m-%d")
        if re.search(r"\b(now|current\s+datetime|current\s+date\s+and\s+time)\b", q):
            return now.strftime("%Y-%m-%d %H:%M:%S")
        return None

    def _compose_fill_value(self, query, field_name, literal_value, dynamic_value, value_template):
        if literal_value is not None and dynamic_value is not None:
            literal = literal_value.strip()
            dynamic = dynamic_value.strip()
            if literal and dynamic:
                return "{} {}".format(literal, dynamic)
            if literal:
                return literal
            if dynamic:
                return dynamic
        if literal_value is not None:
            return literal_value.strip()
        if dynamic_value is not None:
            return dynamic_value.strip()
        return RuleExecutor.render_template(value_template)

    def _collect_required_fields_from_rules(self, rules):
        fields = set()
        for rule in rules:
            action = rule.get("action")
            params = rule.get("params", {})
            if action in ("require_field_not_empty", "set_field_if_empty"):
                field_name = (params.get("field") or "").strip()
                if field_name:
                    fields.add(field_name)
        return fields

    def _harmonize_schema_fields(self, layers, field_names):
        lines = ["[0] Schema harmonization (required/profile fields)"]
        if not field_names:
            lines.append("No required fields discovered for harmonization.")
            return lines

        for layer in layers:
            added = []
            failed = []
            created_any = False
            was_editable = layer.isEditable()
            if not was_editable:
                layer.startEditing()

            for field_name in field_names:
                idx = self._field_index(layer, field_name)
                if idx >= 0:
                    continue
                new_idx, created = self._ensure_text_field(layer, field_name)
                if created and new_idx >= 0:
                    created_any = True
                    added.append(field_name)
                else:
                    failed.append(field_name)

            if not created_any and not was_editable:
                layer.rollBack()

            if added:
                if was_editable:
                    lines.append("Layer '{}': added fields: {}.".format(layer.name(), ", ".join(sorted(added))))
                else:
                    lines.append(
                        "Layer '{}': added fields: {} (pending save in layer edit session).".format(
                            layer.name(), ", ".join(sorted(added))
                        )
                    )
            else:
                lines.append("Layer '{}': no missing required fields.".format(layer.name()))
            if failed:
                lines.append("Layer '{}': failed to add fields: {}.".format(layer.name(), ", ".join(sorted(failed))))
        return lines

    def _ensure_text_field(self, layer, field_name):
        idx = self._field_index(layer, field_name)
        if idx >= 0:
            return idx, False

        if not layer.isEditable() and not layer.startEditing():
            return -1, False
        if not layer.addAttribute(QgsField(field_name, QVariant.String, len=255)):
            return -1, False
        layer.updateFields()
        idx = self._field_index(layer, field_name)
        return idx, idx >= 0

    def _apply_fill_if_empty(
        self,
        layers,
        extent,
        field_name,
        fill_value,
        create_if_missing=False,
        fallback_to_full_layer_when_extent_empty=False,
        force_full_layer_fill=False,
        overwrite_existing=False,
    ):
        lines = []
        for layer in layers:
            if self._layer_is_read_only(layer):
                lines.append("Layer '{}': is read-only; cannot autofill '{}'.".format(layer.name(), field_name))
                continue

            if not self._layer_can_change_attributes(layer):
                lines.append(
                    "Layer '{}': provider does not support attribute updates; cannot autofill '{}'.".format(
                        layer.name(), field_name
                    )
                )
                continue

            idx = self._field_index(layer, field_name)
            was_editable = layer.isEditable()
            created_field = False
            if idx < 0:
                if create_if_missing:
                    idx, created = self._ensure_text_field(layer, field_name)
                    if created:
                        created_field = True
                        lines.append("Layer '{}': created missing field '{}'.".format(layer.name(), field_name))
                if idx < 0:
                    lines.append("Layer '{}': cannot create/access field '{}'.".format(layer.name(), field_name))
                    continue

            updated = 0
            if not layer.isEditable() and not layer.startEditing():
                lines.append("Layer '{}': cannot start editing session for autofill.".format(layer.name()))
                continue

            request = QgsFeatureRequest().setFilterRect(extent)
            features = list(layer.getFeatures(request))
            use_full_layer = force_full_layer_fill or (len(features) == 0 and fallback_to_full_layer_when_extent_empty)
            if use_full_layer:
                features = list(layer.getFeatures())

            for feat in features:
                val = feat[field_name]
                if overwrite_existing or self._is_empty_attr_value(val):
                    if layer.changeAttributeValue(feat.id(), idx, fill_value):
                        updated += 1

            if updated > 0 and not was_editable:
                scope = "full layer" if use_full_layer else "selected area"
                mode = "overwrite" if overwrite_existing else "fill-empty"
                lines.append(
                    "Layer '{}': autofill updated {} '{}' values to '{}' (scope: {}, mode: {}, pending save in layer edit session).".format(
                        layer.name(), updated, field_name, fill_value, scope, mode
                    )
                )
            elif updated > 0:
                scope = "full layer" if use_full_layer else "selected area"
                mode = "overwrite" if overwrite_existing else "fill-empty"
                lines.append(
                    "Layer '{}': autofill updated {} '{}' values to '{}' (scope: {}, mode: {}, pending save in current edit session).".format(
                        layer.name(), updated, field_name, fill_value, scope, mode
                    )
                )
            else:
                if not was_editable:
                    if not created_field:
                        layer.rollBack()
                scope = "full layer" if use_full_layer else "selected area"
                lines.append(
                    "Layer '{}': no empty '{}' values to autofill (scope: {}).".format(
                        layer.name(), field_name, scope
                    )
                )
        return lines

    def _layer_is_read_only(self, layer):
        # QGIS API differs by version: some expose readOnly(), some isReadOnly().
        if hasattr(layer, "isReadOnly"):
            try:
                return bool(layer.isReadOnly())
            except Exception:
                pass
        if hasattr(layer, "readOnly"):
            try:
                return bool(layer.readOnly())
            except Exception:
                pass
        return False

    def _layer_can_change_attributes(self, layer):
        provider = layer.dataProvider()
        if provider is None:
            return False
        caps = provider.capabilities()
        return bool(caps & QgsVectorDataProvider.ChangeAttributeValues)

    def _layer_can_add_features(self, layer):
        provider = layer.dataProvider()
        if provider is None:
            return False
        caps = provider.capabilities()
        return bool(caps & QgsVectorDataProvider.AddFeatures)
