"""Dialog UI for Data Quality Check for Vectors plugin."""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLineEdit,
    QGroupBox,
    QCheckBox,
    QDoubleSpinBox,
    QDialogButtonBox,
    QTextEdit,
    QFileDialog,
    QScrollArea,
    QTabWidget,
    QSplitter,
)


class DataQualityCheckDialog(QDialog):
    """Main plugin dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Data Quality Check for Vectors")
        self.resize(760, 620)
        self.export_dir = ""
        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        root_layout.addWidget(self.tabs)

        self._build_validation_tab()
        self._build_rules_tab()

    def _build_validation_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        scroll = QScrollArea(tab)
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)

        area_group = QGroupBox("Area")
        area_layout = QHBoxLayout(area_group)
        self.area_mode = QComboBox()
        self.area_mode.addItems([
            "Current map extent",
            "Draw rectangle on map",
        ])
        self.btn_pick_area = QPushButton("Pick Area")
        area_layout.addWidget(QLabel("Selection mode:"))
        area_layout.addWidget(self.area_mode)
        area_layout.addWidget(self.btn_pick_area)
        layout.addWidget(area_group)

        layers_group = QGroupBox("Vector Layers")
        layers_layout = QVBoxLayout(layers_group)
        self.layer_list = QListWidget()
        self.layer_list.setSelectionMode(QListWidget.MultiSelection)
        layers_layout.addWidget(QLabel("Select layers to validate:"))
        layers_layout.addWidget(self.layer_list)
        layout.addWidget(layers_group)

        checks_group = QGroupBox("Checks")
        checks_layout = QVBoxLayout(checks_group)
        self.chk_required_fields = QCheckBox("Required fields are not empty")
        self.chk_schema_homogeneous = QCheckBox("Field names are homogeneous across layers")
        self.chk_schema_harmonize = QCheckBox("Harmonize missing required fields across layers")
        self.chk_geometry_validity = QCheckBox("Geometry validity (topological correctness)")
        self.chk_road_topology = QCheckBox("Road endpoint near-connectivity and elevation")
        self.chk_required_fields.setChecked(True)
        self.chk_schema_homogeneous.setChecked(True)
        self.chk_schema_harmonize.setChecked(False)
        self.chk_geometry_validity.setChecked(True)
        checks_layout.addWidget(self.chk_required_fields)
        checks_layout.addWidget(self.chk_schema_homogeneous)
        checks_layout.addWidget(self.chk_schema_harmonize)
        checks_layout.addWidget(self.chk_geometry_validity)
        checks_layout.addWidget(self.chk_road_topology)

        req_row = QHBoxLayout()
        self.required_fields_input = QLineEdit()
        self.required_fields_input.setPlaceholderText("copyright,source,owner")
        req_row.addWidget(QLabel("Required fields (comma-separated):"))
        req_row.addWidget(self.required_fields_input)
        checks_layout.addLayout(req_row)

        tol_row = QHBoxLayout()
        self.snap_tolerance_spin = QDoubleSpinBox()
        self.snap_tolerance_spin.setDecimals(4)
        self.snap_tolerance_spin.setRange(0.0001, 1000000000.0)
        self.snap_tolerance_spin.setValue(0.01)
        self.snap_tolerance_spin.setSuffix(" m")
        self.road_elevation_field = QLineEdit("elevation")
        tol_row.addWidget(QLabel("Road snap tolerance:"))
        tol_row.addWidget(self.snap_tolerance_spin)
        tol_row.addWidget(QLabel("Elevation field:"))
        tol_row.addWidget(self.road_elevation_field)
        checks_layout.addLayout(tol_row)

        layout.addWidget(checks_group)

        rag_group = QGroupBox("Local Guidelines (RAG-assisted)")
        rag_layout = QVBoxLayout(rag_group)

        profile_row = QHBoxLayout()
        self.rule_profile = QComboBox()
        profile_row.addWidget(QLabel("Guideline profile:"))
        profile_row.addWidget(self.rule_profile)
        rag_layout.addLayout(profile_row)

        self.chk_use_rag = QCheckBox("Enable local guideline retrieval and execution")
        self.chk_use_rag.setChecked(True)
        rag_layout.addWidget(self.chk_use_rag)

        self.chk_use_llm = QCheckBox("Use local LLM embeddings (Ollama)")
        rag_layout.addWidget(self.chk_use_llm)

        llm_row = QHBoxLayout()
        self.ollama_model = QLineEdit("nomic-embed-text")
        self.ollama_url = QLineEdit("http://localhost:11434")
        llm_row.addWidget(QLabel("Ollama model:"))
        llm_row.addWidget(self.ollama_model)
        llm_row.addWidget(QLabel("URL:"))
        llm_row.addWidget(self.ollama_url)
        rag_layout.addLayout(llm_row)

        rag_query_row = QHBoxLayout()
        self.rag_query_input = QLineEdit()
        self.rag_query_input.setPlaceholderText("Example: ensure copyright is filled and connect near roads")
        rag_query_row.addWidget(QLabel("Guideline query:"))
        rag_query_row.addWidget(self.rag_query_input)
        rag_layout.addLayout(rag_query_row)

        self.chk_apply_autofix = QCheckBox("Apply safe autofix operations (empty-field updates only)")
        self.chk_apply_autofix.setChecked(True)
        rag_layout.addWidget(self.chk_apply_autofix)

        author_row = QHBoxLayout()
        self.new_rule_prompt = QLineEdit()
        self.new_rule_prompt.setPlaceholderText("Create a guideline: ensure owner field is mandatory for cadastre")
        self.btn_add_rule_from_prompt = QPushButton("Add Guideline From Prompt")
        author_row.addWidget(self.new_rule_prompt)
        author_row.addWidget(self.btn_add_rule_from_prompt)
        rag_layout.addLayout(author_row)

        search_group = QGroupBox("Stored Guidelines Search")
        search_layout = QVBoxLayout(search_group)
        search_row = QHBoxLayout()
        self.rule_search_input = QLineEdit()
        self.rule_search_input.setPlaceholderText("Search stored guidelines by id, name, keyword, operation")
        self.btn_rule_search = QPushButton("Search")
        search_row.addWidget(self.rule_search_input)
        search_row.addWidget(self.btn_rule_search)
        search_layout.addLayout(search_row)

        self.rule_search_results = QListWidget()
        self.rule_search_results.setSelectionMode(QListWidget.SingleSelection)
        search_layout.addWidget(self.rule_search_results)

        search_use_row = QHBoxLayout()
        self.btn_use_selected_rule = QPushButton("Use Selected Guideline In Query")
        self.btn_refresh_search = QPushButton("Refresh Guideline Index")
        search_use_row.addWidget(self.btn_use_selected_rule)
        search_use_row.addWidget(self.btn_refresh_search)
        search_layout.addLayout(search_use_row)
        layout.addWidget(search_group)

        layout.addWidget(rag_group)

        topology_group = QGroupBox("Topology Repair")
        topology_layout = QGridLayout(topology_group)
        self.chk_topology_repair = QCheckBox("Enable automatic topology repair workflow")
        self.chk_topology_preview_only = QCheckBox("Preview only (do not commit to source layers)")
        self.chk_topology_preview_only.setChecked(True)
        self.repair_tolerance_spin = QDoubleSpinBox()
        self.repair_tolerance_spin.setDecimals(4)
        self.repair_tolerance_spin.setRange(0.0001, 1000000000.0)
        self.repair_tolerance_spin.setValue(0.01)
        self.repair_tolerance_spin.setSuffix(" m")
        topology_layout.addWidget(self.chk_topology_repair, 0, 0, 1, 2)
        topology_layout.addWidget(self.chk_topology_preview_only, 1, 0, 1, 2)
        topology_layout.addWidget(QLabel("Repair tolerance:"), 2, 0)
        topology_layout.addWidget(self.repair_tolerance_spin, 2, 1)
        self.btn_sketch_highlight = QPushButton("Sketch Area and Highlight Elements")
        self.btn_connect_highlighted = QPushButton("Connect Highlighted Elements")
        topology_layout.addWidget(self.btn_sketch_highlight, 3, 0, 1, 2)
        topology_layout.addWidget(self.btn_connect_highlighted, 4, 0, 1, 2)
        layout.addWidget(topology_group)

        highlighted_group = QGroupBox("Highlighted Elements")
        highlighted_layout = QVBoxLayout(highlighted_group)
        self.lbl_highlighted_count = QLabel("Found: 0")
        self.highlighted_elements_list = QListWidget()
        self.highlighted_elements_list.setSelectionMode(QListWidget.MultiSelection)
        highlighted_layout.addWidget(self.lbl_highlighted_count)
        highlighted_layout.addWidget(self.highlighted_elements_list)
        layout.addWidget(highlighted_group)

        export_group = QGroupBox("Report Export")
        export_layout = QGridLayout(export_group)
        self.chk_export_json = QCheckBox("JSON")
        self.chk_export_html = QCheckBox("HTML")
        self.chk_export_pdf = QCheckBox("PDF")
        self.chk_export_html.setChecked(True)
        self.chk_export_json.setChecked(True)
        self.btn_pick_export_dir = QPushButton("Select Export Folder")
        self.lbl_export_dir = QLabel("No export folder selected")
        export_layout.addWidget(QLabel("Formats:"), 0, 0)
        export_layout.addWidget(self.chk_export_json, 0, 1)
        export_layout.addWidget(self.chk_export_html, 0, 2)
        export_layout.addWidget(self.chk_export_pdf, 0, 3)
        export_layout.addWidget(self.btn_pick_export_dir, 1, 0, 1, 2)
        export_layout.addWidget(self.lbl_export_dir, 1, 2, 1, 2)
        layout.addWidget(export_group)

        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setPlaceholderText("Validation report will appear here.")
        layout.addWidget(self.results)

        self.status_badge = QLabel("Mode: fill-empty | Scope: selected area | Pending edits: no")
        self.status_badge.setStyleSheet(
            "QLabel {"
            "background-color: #e8f1f8;"
            "border: 1px solid #8bb6d6;"
            "border-radius: 4px;"
            "padding: 6px;"
            "font-weight: 600;"
            "}"
        )
        layout.addWidget(self.status_badge)

        buttons = QDialogButtonBox()
        self.btn_run = buttons.addButton("Run Checks", QDialogButtonBox.AcceptRole)
        self.btn_store_immutable = buttons.addButton("Store In Immutable Catalogue", QDialogButtonBox.ActionRole)
        self.btn_close = buttons.addButton("Close", QDialogButtonBox.RejectRole)
        layout.addWidget(buttons)

        scroll.setWidget(container)
        tab_layout.addWidget(scroll)
        self.tabs.addTab(tab, "Validation")

        self.btn_pick_export_dir.clicked.connect(self.pick_export_dir)

    def _build_rules_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Profile:"))
        self.profile_manage = QComboBox()
        top_row.addWidget(self.profile_manage)
        self.btn_rules_reload = QPushButton("Reload")
        self.btn_rules_new = QPushButton("New Guideline")
        self.btn_rules_delete = QPushButton("Delete Guideline")
        top_row.addWidget(self.btn_rules_reload)
        top_row.addWidget(self.btn_rules_new)
        top_row.addWidget(self.btn_rules_delete)
        tab_layout.addLayout(top_row)

        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Guidelines in selected profile:"))
        self.rules_list = QListWidget()
        left_layout.addWidget(self.rules_list)

        right = QWidget()
        right_layout = QVBoxLayout(right)

        assistant_group = QGroupBox("Guideline Assistant (plain language)")
        assistant_layout = QVBoxLayout(assistant_group)
        self.rule_nl_input = QTextEdit()
        self.rule_nl_input.setPlaceholderText(
            "Example: In cadastre layers, owner must be mandatory and not empty.\n"
            "Or: For roads, check near endpoints within 0.5 meters using elevation field z."
        )
        self.rule_nl_examples = QComboBox()
        self.rule_nl_examples.addItems([
            "Choose an example...",
            "In cadastre layers, owner must be mandatory and not empty.",
            "If copyright is empty, set copyright to 'Copyright {year}'.",
            "For roads, check near endpoints within 0.5 meters using elevation.",
            "If a road is crossing a river create a segment for the crossing and name that element bridge.",
        ])
        self.btn_rule_nl_use_example = QPushButton("Use Example")
        example_row = QHBoxLayout()
        example_row.addWidget(self.rule_nl_examples)
        example_row.addWidget(self.btn_rule_nl_use_example)
        self.btn_rule_nl_generate = QPushButton("Generate Guideline Draft")
        self.lbl_rule_nl_hint = QLabel("Uses Ollama to fill id, name, description, keywords, operation, and params.")
        assistant_layout.addWidget(self.rule_nl_input)
        assistant_layout.addLayout(example_row)
        assistant_layout.addWidget(self.btn_rule_nl_generate)
        assistant_layout.addWidget(self.lbl_rule_nl_hint)
        right_layout.addWidget(assistant_group)

        form = QGridLayout()
        self.rule_id_input = QLineEdit()
        self.rule_name_input = QLineEdit()
        self.rule_description_input = QLineEdit()
        self.rule_keywords_input = QLineEdit()
        self.rule_action_input = QComboBox()
        self.rule_action_input.addItems([
            "require_field_not_empty",
            "set_field_if_empty",
            "check_road_endpoint_snap_candidates",
            "create_bridge_segment_at_road_river_crossing",
        ])
        self.rule_params_input = QTextEdit()
        self.rule_params_input.setPlaceholderText('{"field":"copyright","value_template":"Copyright {year}"}')

        form.addWidget(QLabel("id"), 0, 0)
        form.addWidget(self.rule_id_input, 0, 1)
        form.addWidget(QLabel("name"), 1, 0)
        form.addWidget(self.rule_name_input, 1, 1)
        form.addWidget(QLabel("description"), 2, 0)
        form.addWidget(self.rule_description_input, 2, 1)
        form.addWidget(QLabel("keywords (comma-separated)"), 3, 0)
        form.addWidget(self.rule_keywords_input, 3, 1)
        form.addWidget(QLabel("operation"), 4, 0)
        form.addWidget(self.rule_action_input, 4, 1)
        form.addWidget(QLabel("params (JSON)"), 5, 0)
        form.addWidget(self.rule_params_input, 5, 1)
        right_layout.addLayout(form)

        save_row = QHBoxLayout()
        self.btn_rules_save = QPushButton("Save Guideline")
        self.btn_rules_save_all = QPushButton("Save Profile")
        save_row.addWidget(self.btn_rules_save)
        save_row.addWidget(self.btn_rules_save_all)
        right_layout.addLayout(save_row)

        self.rules_message = QLabel("")
        right_layout.addWidget(self.rules_message)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        tab_layout.addWidget(splitter)

        self.tabs.addTab(tab, "Guidelines Manager")

    def set_layers(self, layers):
        self.layer_list.clear()
        for layer in layers:
            item = QListWidgetItem(layer.name())
            item.setData(Qt.UserRole, layer.id())
            item.setCheckState(Qt.Checked)
            self.layer_list.addItem(item)

    def selected_layer_ids(self):
        ids = []
        for i in range(self.layer_list.count()):
            item = self.layer_list.item(i)
            if item.checkState() == Qt.Checked:
                ids.append(item.data(Qt.UserRole))
        return ids

    def required_fields(self):
        raw = self.required_fields_input.text().strip()
        if not raw:
            return []
        return [part.strip() for part in raw.split(",") if part.strip()]

    def set_profiles(self, profile_names):
        self.rule_profile.clear()
        self.rule_profile.addItems(profile_names)
        self.profile_manage.clear()
        self.profile_manage.addItems(profile_names)

    def pick_export_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select report export folder")
        if not folder:
            return
        self.export_dir = folder
        self.lbl_export_dir.setText(folder)

    def set_status_badge(self, text):
        self.status_badge.setText(text)

    def set_rules_message(self, text):
        self.rules_message.setText(text)

    def set_highlighted_elements(self, rows):
        self.highlighted_elements_list.clear()
        for row in rows:
            self.highlighted_elements_list.addItem(row)
        self.lbl_highlighted_count.setText("Found: {}".format(len(rows)))

    def clear_highlighted_elements(self):
        self.highlighted_elements_list.clear()
        self.lbl_highlighted_count.setText("Found: 0")
