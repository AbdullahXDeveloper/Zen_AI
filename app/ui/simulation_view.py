"""
app/ui/simulation_view.py
Zen AI — Module 12: World Simulation Frontend
Theme: Deep red / crimson  #c0392b
Left panel: Simulation config
Right panel: Results with per-entity impact cards + global outcome
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QLineEdit, QComboBox,
    QTextEdit, QSizePolicy, QSplitter
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor

from app.database.db_init import get_session
from app.database import crud
from app.database.models import Universe, Character, Faction, Location, Artifact, Event

ACCENT = "#c0392b"
IMPACT_COLORS = {
    "major":    "#e74c3c",
    "moderate": "#f39c12",
    "minor":    "#3498db",
    "none":     "#2A2A2A",
}
IMPACT_ICONS = {
    "major": "💥", "moderate": "⚡", "minor": "🔹", "none": "○",
}
ENTITY_ICONS = {
    "character": "👤", "faction": "⚔", "location": "📍",
    "artifact": "💎", "event": "📅", "universe": "🌐",
}
ENTITY_MODELS = {
    "character": Character, "faction": Faction, "location": Location,
    "artifact": Artifact, "event": Event, "universe": Universe,
}


# ─── Context Loader ──────────────────────────────────────
class LoadSimContextWorker(QThread):
    done  = Signal(list, list, list, list, list, list)  # unis, chars, facs, locs, arts, evts
    error = Signal(str)

    def run(self):
        try:
            s = get_session()
            unis  = [{"id": u.id, "name": u.name}      for u in s.query(Universe).all()]
            chars = [{"id": c.id, "name": c.name, "type": "character", "universe_id": c.universe_id}  for c in s.query(Character).all()]
            facs  = [{"id": f.id, "name": f.name, "type": "faction",   "universe_id": f.universe_id}  for f in s.query(Faction).all()]
            locs  = [{"id": l.id, "name": l.name, "type": "location",  "universe_id": l.universe_id}  for l in s.query(Location).all()]
            arts  = [{"id": a.id, "name": a.name, "type": "artifact",  "universe_id": a.universe_id}  for a in s.query(Artifact).all()]
            evts  = [{"id": e.id, "name": e.name, "type": "event",     "universe_id": e.universe_id}  for e in s.query(Event).all()]
            s.close()
            self.done.emit(unis, chars, facs, locs, arts, evts)
        except Exception as e:
            self.error.emit(str(e))


# ─── Simulation Worker ───────────────────────────────────
class SimulationWorker(QThread):
    progress = Signal(str)
    done     = Signal(dict)
    error    = Signal(str)

    def __init__(self, premise, affected_entities, universe_id, depth):
        super().__init__()
        self.premise           = premise
        self.affected_entities = affected_entities
        self.universe_id       = universe_id
        self.depth             = depth

    def run(self):
        try:
            from app.simulation.engine import run_simulation
            self.progress.emit("Building lore context from database...")
            s = get_session()
            self.progress.emit(f"Running {self.depth} simulation with Ollama...")
            result = run_simulation(
                s,
                premise           = self.premise,
                affected_entities = self.affected_entities,
                universe_id       = self.universe_id,
                simulation_depth  = self.depth,
            )
            s.close()
            self.done.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ─── Save Worker ─────────────────────────────────────────
class SaveSimWorker(QThread):
    done  = Signal(int)
    error = Signal(str)

    def __init__(self, title, premise, universe_id, affected_entities, result):
        super().__init__()
        self.title             = title
        self.premise           = premise
        self.universe_id       = universe_id
        self.affected_entities = affected_entities
        self.result            = result

    def run(self):
        try:
            s = get_session()
            run = crud.create_simulation_run(
                s,
                title                  = self.title,
                premise                = self.premise,
                universe_id            = self.universe_id,
                affected_entities_json = self.affected_entities,
                generated_outcomes_json= self.result.get("outcomes", []),
                reasoning_text         = self.result.get("reasoning", ""),
            )
            rid = run.id
            s.close()
            self.done.emit(rid)
        except Exception as e:
            self.error.emit(str(e))


# ─── Entity Impact Card ───────────────────────────────────
class ImpactCard(QFrame):
    def __init__(self, outcome: dict):
        super().__init__()
        etype  = outcome.get("entity_type", "unknown")
        impact = outcome.get("impact", "none")
        name   = outcome.get("entity_name", "—")
        text   = outcome.get("outcome_text", "—")
        color  = IMPACT_COLORS.get(impact, "#333")
        icon   = ENTITY_ICONS.get(etype, "❓")
        imp_icon = IMPACT_ICONS.get(impact, "○")

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setStyleSheet(f"""
            QFrame {{
                background: #0D0D0D;
                border: 1px solid #181818;
                border-left: 4px solid {color};
                border-radius: 8px;
            }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(6)

        # Header row
        hdr = QHBoxLayout()
        name_lbl = QLabel(f"{icon}  {name}")
        name_lbl.setStyleSheet("color: #CCCCCC; font-size: 13px; font-weight: 700; background: transparent; border: none;")

        impact_lbl = QLabel(f"{imp_icon} {impact.upper()}")
        impact_lbl.setStyleSheet(
            f"color: {color}; font-size: 10px; font-weight: 700; "
            f"background: {color}18; border: 1px solid {color}44; "
            "border-radius: 4px; padding: 2px 8px;"
        )
        type_lbl = QLabel(etype.title())
        type_lbl.setStyleSheet("color: #2A2A2A; font-size: 10px; background: transparent; border: none;")

        hdr.addWidget(name_lbl)
        hdr.addStretch()
        hdr.addWidget(type_lbl)
        hdr.addSpacing(8)
        hdr.addWidget(impact_lbl)
        lay.addLayout(hdr)

        # Outcome text
        txt = QLabel(text)
        txt.setWordWrap(True)
        txt.setStyleSheet("color: #555; font-size: 12px; line-height: 1.5; background: transparent; border: none;")
        lay.addWidget(txt)


# ─── Main Simulation View ─────────────────────────────────
class SimulationViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._ctx_worker  = None
        self._sim_worker  = None
        self._save_worker = None
        self._all_entities = []   # [{id, name, type, universe_id}, ...]
        self._universes   = []
        self._selected    = []    # [{entity_type, entity_id, entity_name}, ...]
        self._last_result = None
        self._setup_ui()
        self._load_context()

    # ── UI Setup ──────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setStyleSheet("background: #0D0D0D;")

        # ── Top bar ──
        top_bar = QFrame()
        top_bar.setFixedHeight(64)
        top_bar.setStyleSheet("background: #0D0D0D; border-bottom: 1px solid #1A1A1A;")
        b = QHBoxLayout(top_bar)
        b.setContentsMargins(32, 0, 32, 0)

        title = QLabel("🌐  World Simulation")
        title.setStyleSheet(f"color: {ACCENT}; font-size: 20px; font-weight: 900; letter-spacing: 2px; background: transparent; border: none;")
        self._top_status = QLabel("Ollama-powered what-if scenario engine for the Zendrix multiverse")
        self._top_status.setStyleSheet("color: #2A2A2A; font-size: 11px; background: transparent; border: none;")
        b.addWidget(title)
        b.addStretch()
        b.addWidget(self._top_status)
        root.addWidget(top_bar)

        # ── Splitter ──
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1A1A1A; width: 1px; }")

        # ────── LEFT: Config ──────
        left = QFrame()
        left.setMinimumWidth(360)
        left.setMaximumWidth(440)
        left.setStyleSheet("background: #080808; border: none;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #080808; } QScrollBar:vertical { background: #111; width: 5px; } QScrollBar::handle:vertical { background: #2A2A2A; border-radius: 2px; }")

        fw = QWidget()
        fw.setStyleSheet("background: #080808;")
        fl = QVBoxLayout(fw)
        fl.setContentsMargins(24, 24, 24, 24)
        fl.setSpacing(12)

        def _lbl(t):
            l = QLabel(t)
            l.setStyleSheet("color: #333; font-size: 10px; font-weight: 700; letter-spacing: 1px; background: transparent; border: none;")
            return l

        fs = f"""
            QLineEdit, QTextEdit, QComboBox {{
                background: #0D0D0D; color: #CCCCCC;
                border: 1px solid #1A1A1A; border-radius: 7px;
                padding: 8px 12px; font-size: 13px;
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
            QComboBox QAbstractItemView {{ background: #111; color: #CCC; selection-background-color: {ACCENT}; }}
        """

        # Universe
        fl.addWidget(_lbl("TARGET UNIVERSE  (optional)"))
        self._uni_combo = QComboBox()
        self._uni_combo.addItem("— All / Universe-Independent —", None)
        self._uni_combo.setStyleSheet(fs)
        self._uni_combo.currentIndexChanged.connect(self._filter_entity_combo)
        fl.addWidget(self._uni_combo)

        # Depth
        fl.addWidget(_lbl("SIMULATION DEPTH"))
        self._depth_combo = QComboBox()
        self._depth_combo.addItem("⚡  Quick  (~1-2 min)", "quick")
        self._depth_combo.addItem("🔬  Standard  (~3-5 min)", "standard")
        self._depth_combo.addItem("🌊  Deep  (~8-12 min)", "deep")
        self._depth_combo.setCurrentIndex(1)
        self._depth_combo.setStyleSheet(fs)
        fl.addWidget(self._depth_combo)

        # Affected Entities
        fl.addWidget(_lbl("AFFECTED ENTITIES  (optional multi-select)"))

        entity_row = QHBoxLayout()
        self._entity_type_combo = QComboBox()
        for et in ["character", "faction", "location", "artifact", "event", "universe"]:
            icon = ENTITY_ICONS.get(et, "")
            self._entity_type_combo.addItem(f"{icon} {et.title()}", et)
        self._entity_type_combo.setStyleSheet(fs)
        self._entity_type_combo.currentIndexChanged.connect(self._filter_entity_combo)

        self._entity_combo = QComboBox()
        self._entity_combo.setStyleSheet(fs)

        add_btn = QPushButton("＋")
        add_btn.setFixedSize(36, 34)
        add_btn.setStyleSheet(f"QPushButton {{ background: {ACCENT}22; color: {ACCENT}; border: 1px solid {ACCENT}44; border-radius: 6px; font-size: 16px; font-weight: 700; }} QPushButton:hover {{ background: {ACCENT}44; }}")
        add_btn.clicked.connect(self._add_entity)

        entity_row.addWidget(self._entity_type_combo)
        entity_row.addWidget(self._entity_combo)
        entity_row.addWidget(add_btn)
        fl.addLayout(entity_row)

        # Selected entities display
        self._selected_lbl = QLabel("No entities selected  (simulation will be universe-wide)")
        self._selected_lbl.setWordWrap(True)
        self._selected_lbl.setStyleSheet(f"color: #2A2A2A; font-size: 10px; background: transparent; border: none;")
        fl.addWidget(self._selected_lbl)

        self._clear_entities_btn = QPushButton("✕  Clear All Entities")
        self._clear_entities_btn.setFixedHeight(28)
        self._clear_entities_btn.setStyleSheet(f"QPushButton {{ background: transparent; color: #333; border: 1px solid #1A1A1A; border-radius: 5px; font-size: 11px; }} QPushButton:hover {{ color: {ACCENT}; border-color: {ACCENT}44; }}")
        self._clear_entities_btn.clicked.connect(self._clear_entities)
        fl.addWidget(self._clear_entities_btn)

        # Premise
        fl.addWidget(_lbl("SIMULATION PREMISE  *"))
        self._premise_input = QTextEdit()
        self._premise_input.setFixedHeight(140)
        self._premise_input.setPlaceholderText(
            "What-if scenario describe karein...\n\n"
            "e.g. What if OM_X never defeated K in the First Void War? "
            "How would the Zendrix Prime universe change? "
            "Which factions would rise to fill the power vacuum?\n\n"
            "Minimum 20 characters."
        )
        self._premise_input.setStyleSheet(fs)
        fl.addWidget(self._premise_input)

        # Run button
        self._run_btn = QPushButton("🌐  Run Simulation")
        self._run_btn.setFixedHeight(46)
        self._run_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}; color: #FFF;
                border: none; border-radius: 10px;
                font-size: 15px; font-weight: 800;
            }}
            QPushButton:hover {{ background: #e74c3c; }}
            QPushButton:disabled {{ background: #1A0500; color: #444; }}
        """)
        self._run_btn.clicked.connect(self._run_simulation)
        fl.addWidget(self._run_btn)

        self._run_status = QLabel("")
        self._run_status.setAlignment(Qt.AlignCenter)
        self._run_status.setStyleSheet(f"color: {ACCENT}; font-size: 11px; background: transparent; border: none;")
        fl.addWidget(self._run_status)
        fl.addStretch()

        scroll.setWidget(fw)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.addWidget(scroll)
        splitter.addWidget(left)

        # ────── RIGHT: Results ──────
        right = QFrame()
        right.setStyleSheet("background: #0D0D0D; border: none;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        # Results header
        res_hdr = QFrame()
        res_hdr.setFixedHeight(54)
        res_hdr.setStyleSheet("background: #0D0D0D; border-bottom: 1px solid #141414;")
        rh = QHBoxLayout(res_hdr)
        rh.setContentsMargins(28, 0, 28, 0)
        rh.setSpacing(12)

        self._result_title = QLabel("Simulation Results")
        self._result_title.setStyleSheet("color: #222; font-size: 14px; font-weight: 700; background: transparent; border: none;")

        self._save_btn = QPushButton("💾  Save Run")
        self._save_btn.setFixedHeight(30)
        self._save_btn.setEnabled(False)
        self._save_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {ACCENT};
                border: 1px solid {ACCENT}44; border-radius: 7px;
                font-size: 12px; font-weight: 600; padding: 0 14px;
            }}
            QPushButton:hover {{ background: {ACCENT}14; border-color: {ACCENT}; }}
            QPushButton:disabled {{ color: #1A1A1A; border-color: #0F0F0F; }}
        """)
        self._save_btn.clicked.connect(self._save_run)

        self._save_status = QLabel("")
        self._save_status.setStyleSheet("color: #2ecc71; font-size: 11px; background: transparent; border: none;")

        rh.addWidget(self._result_title)
        rh.addStretch()
        rh.addWidget(self._save_status)
        rh.addWidget(self._save_btn)
        rl.addWidget(res_hdr)

        # Results scroll
        self._res_scroll = QScrollArea()
        self._res_scroll.setWidgetResizable(True)
        self._res_scroll.setStyleSheet("QScrollArea { border: none; background: #0D0D0D; } QScrollBar:vertical { background: #111; width: 6px; } QScrollBar::handle:vertical { background: #2A2A2A; border-radius: 3px; }")

        self._res_content = QWidget()
        self._res_content.setStyleSheet("background: #0D0D0D;")
        self._res_layout = QVBoxLayout(self._res_content)
        self._res_layout.setContentsMargins(28, 24, 28, 40)
        self._res_layout.setSpacing(16)
        self._res_layout.setAlignment(Qt.AlignTop)

        self._show_placeholder()
        self._res_scroll.setWidget(self._res_content)
        rl.addWidget(self._res_scroll)

        splitter.addWidget(right)
        splitter.setSizes([400, 880])
        root.addWidget(splitter)

    # ── Context Load ──────────────────────────────────────

    def _load_context(self):
        self._ctx_worker = LoadSimContextWorker()
        self._ctx_worker.done.connect(self._on_context)
        self._ctx_worker.error.connect(lambda e: print(f"[Sim] ctx error: {e}"))
        self._ctx_worker.start()

    def _on_context(self, unis, chars, facs, locs, arts, evts):
        self._universes    = unis
        self._all_entities = chars + facs + locs + arts + evts

        self._uni_combo.blockSignals(True)
        self._uni_combo.clear()
        self._uni_combo.addItem("— All / Universe-Independent —", None)
        for u in unis:
            self._uni_combo.addItem(f"🌐  {u['name']}", u["id"])
        self._uni_combo.blockSignals(False)

        self._filter_entity_combo()

    def _filter_entity_combo(self):
        etype = self._entity_type_combo.currentData()
        uid   = self._uni_combo.currentData()
        self._entity_combo.clear()
        self._entity_combo.addItem("— Select entity —", None)
        for e in self._all_entities:
            if e["type"] != etype:
                continue
            if uid and e.get("universe_id") != uid:
                continue
            self._entity_combo.addItem(e["name"], e)

    def _add_entity(self):
        e = self._entity_combo.currentData()
        if not e:
            return
        entry = {"entity_type": e["type"], "entity_id": e["id"], "entity_name": e["name"]}
        if entry not in self._selected:
            self._selected.append(entry)
            self._update_selected_lbl()

    def _update_selected_lbl(self):
        if not self._selected:
            self._selected_lbl.setText("No entities selected  (simulation will be universe-wide)")
            return
        lines = "  |  ".join(
            f"{ENTITY_ICONS.get(s['entity_type'], '')} {s['entity_name']}"
            for s in self._selected
        )
        self._selected_lbl.setText(f"{len(self._selected)} selected:  {lines}")
        self._selected_lbl.setStyleSheet(f"color: {ACCENT}99; font-size: 10px; background: transparent; border: none;")

    def _clear_entities(self):
        self._selected = []
        self._update_selected_lbl()
        self._selected_lbl.setStyleSheet("color: #2A2A2A; font-size: 10px; background: transparent; border: none;")

    # ── Simulation Run ────────────────────────────────────

    def _run_simulation(self):
        premise = self._premise_input.toPlainText().strip()
        if len(premise) < 20:
            self._run_status.setText("⚠  Premise too short — min 20 chars")
            return

        self._run_btn.setEnabled(False)
        self._save_btn.setEnabled(False)
        self._last_result = None
        self._run_status.setText("Initializing...")
        self._result_title.setText("Running...")
        self._result_title.setStyleSheet(f"color: {ACCENT}55; font-size: 14px; font-weight: 700; background: transparent; border: none;")
        self._clear_results()
        self._show_running()

        uid   = self._uni_combo.currentData()
        depth = self._depth_combo.currentData()

        self._sim_worker = SimulationWorker(
            premise           = premise,
            affected_entities = [{"entity_type": s["entity_type"], "entity_id": s["entity_id"]} for s in self._selected],
            universe_id       = uid,
            depth             = depth,
        )
        self._sim_worker.progress.connect(self._run_status.setText)
        self._sim_worker.done.connect(self._on_result)
        self._sim_worker.error.connect(self._on_error)
        self._sim_worker.start()

    def _on_result(self, result: dict):
        self._run_btn.setEnabled(True)
        self._run_status.setText("")
        self._last_result = result
        self._clear_results()

        title = result.get("title", "Simulation Results")
        self._result_title.setText(f"🌐  {title}")
        self._result_title.setStyleSheet(f"color: {ACCENT}; font-size: 14px; font-weight: 700; background: transparent; border: none;")
        self._save_btn.setEnabled(True)

        # ── Reasoning ──
        reasoning = result.get("reasoning", "")
        if reasoning:
            self._res_layout.addWidget(self._section("AI REASONING"))
            rl = QLabel(reasoning)
            rl.setWordWrap(True)
            rl.setStyleSheet("color: #333; font-size: 12px; line-height: 1.6; background: transparent; border: none;")
            self._res_layout.addWidget(rl)

        # ── Entity Outcomes ──
        outcomes = result.get("outcomes", [])
        if outcomes:
            self._res_layout.addWidget(self._section(f"ENTITY OUTCOMES  ({len(outcomes)})"))
            for o in outcomes:
                card = ImpactCard(o)
                self._res_layout.addWidget(card)

        # ── Global Outcome ──
        global_out = result.get("global_outcome", "")
        if global_out:
            self._res_layout.addWidget(self._section("GLOBAL WORLD OUTCOME"))
            gl = QLabel(global_out)
            gl.setWordWrap(True)
            gl.setStyleSheet(f"color: #555; font-size: 13px; line-height: 1.7; padding: 16px; background: {ACCENT}08; border: 1px solid {ACCENT}22; border-radius: 8px; border-left: 4px solid {ACCENT};")
            self._res_layout.addWidget(gl)

        # ── New Events ──
        new_events = result.get("new_events", [])
        if new_events:
            self._res_layout.addWidget(self._section("NEW EVENTS THAT WOULD EMERGE"))
            for ev in new_events:
                elbl = QLabel(f"📅  {ev}")
                elbl.setWordWrap(True)
                elbl.setStyleSheet("color: #e74c3c88; font-size: 12px; background: transparent; border: none; padding: 3px 0;")
                self._res_layout.addWidget(elbl)

        # ── Timeline Shift ──
        tl = result.get("timeline_shift", "")
        if tl and tl != "No significant shift":
            self._res_layout.addWidget(self._section("TIMELINE SHIFT"))
            tll = QLabel(f"⏱  {tl}")
            tll.setWordWrap(True)
            tll.setStyleSheet("color: #9b59b6; font-size: 12px; background: transparent; border: none;")
            self._res_layout.addWidget(tll)

        self._res_layout.addStretch()

    def _on_error(self, msg: str):
        self._run_btn.setEnabled(True)
        self._run_status.setText(f"⚠  Error: {msg[:80]}")
        self._clear_results()
        self._result_title.setText("Simulation Failed")
        self._result_title.setStyleSheet("color: #e74c3c; font-size: 14px; font-weight: 700; background: transparent; border: none;")
        err_lbl = QLabel(f"[Error]\n{msg}\n\nOllama chal raha hai?\nCheck: ollama serve")
        err_lbl.setAlignment(Qt.AlignCenter)
        err_lbl.setStyleSheet("color: #333; font-size: 13px; padding: 60px; background: transparent; border: none;")
        self._res_layout.addWidget(err_lbl)

    # ── Save ──────────────────────────────────────────────

    def _save_run(self):
        if not self._last_result:
            return
        self._save_btn.setEnabled(False)
        self._save_status.setText("Saving...")
        self._save_worker = SaveSimWorker(
            title             = self._last_result.get("title", "Simulation Run"),
            premise           = self._premise_input.toPlainText().strip(),
            universe_id       = self._uni_combo.currentData(),
            affected_entities = [{"entity_type": s["entity_type"], "entity_id": s["entity_id"]} for s in self._selected],
            result            = self._last_result,
        )
        self._save_worker.done.connect(self._on_saved)
        self._save_worker.error.connect(lambda e: self._save_status.setText(f"⚠  {e}"))
        self._save_worker.start()

    def _on_saved(self, rid: int):
        self._save_status.setText(f"✅  Saved  (Run #{rid})")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self._save_status.setText(""))

    # ── Helpers ───────────────────────────────────────────

    def _show_placeholder(self):
        lbl = QLabel(
            "Simulation results yahan appear honge...\n\n"
            "Baayin taraf:\n"
            "  1. Universe select karein\n"
            "  2. Affected entities add karein\n"
            "  3. Premise likhein\n"
            "  4. '🌐 Run Simulation' dabain\n\n"
            "Ollama locally reasoning karega aur per-entity outcomes generate karega."
        )
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #1A1A1A; font-size: 13px; line-height: 1.8; padding: 80px; background: transparent; border: none;")
        self._res_layout.addWidget(lbl)

    def _show_running(self):
        lbl = QLabel(
            f"🌐  Simulation chal rahi hai...\n\n"
            "Ollama Zendrix multiverse ke lore se reasoning kar raha hai.\n"
            "Yeh operation 1-10 minute le sakta hai depth ke mutabiq."
        )
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"color: {ACCENT}44; font-size: 13px; line-height: 1.8; padding: 80px; background: transparent; border: none;")
        self._res_layout.addWidget(lbl)

    def _clear_results(self):
        while self._res_layout.count():
            item = self._res_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    @staticmethod
    def _section(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #222; font-size: 10px; font-weight: 700; letter-spacing: 2px; padding-top: 8px; background: transparent; border: none;")
        return lbl
