"""Мутационная проверка 2.0: нарочно ломает сети-оформители, законы и запасной вариант и
смотрит, что тесты это ловят.

    python tools/mutate.py            # все мутанты
    python tools/mutate.py laws       # только с этим словом в имени

Прогон - общий aikit.mutate (копия из PythonAiGames/aikit 0.2.2): сначала те же тесты без
мутанта (красные - стоп, код 2), файл правится на месте и восстанавливается в finally.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aikit.mutate import main as run_all  # noqa: E402

LAYOUT = "tests/test_design_layout.py"
RUNTIME = "tests/test_design_runtime.py"
TILES = "tests/test_design_tiles.py"
LOOK = "tests/test_look.py"

# (имя, файл, было, стало, тесты)
MUTANTS = [
    ("laws: наложение не видно", "game/design/laws.py",
     "if pa == pb and _overlap(rects[a], rects[b]):", "if False:", LAYOUT),
    ("laws: размер под содержимое не проверяется", "game/design/laws.py",
     "if w < nw - SIZE_SLACK or h < nh - SIZE_SLACK:", "if False:", LAYOUT),
    ("laws: вне окна не видно", "game/design/laws.py",
     "        if not _inside(r, box):", "        if False:", LAYOUT),
    ("laws: контраст не проверяется", "game/design/laws.py", "        if not c >= lo:", "        if False:",
     LAYOUT + " " + RUNTIME),
    ("laws: тайл чужого вида не виден", "game/design/laws.py",
     "        for i in np.nonzero(nearest != kinds)[0][:5]:", "        for i in []:", "tests/test_design_nets.py"),
    ("layout: раскладки кода не выключаются", "game/design/layout.py",
     "        lay.setEnabled(False)", "        lay.setEnabled(True)", RUNTIME + " -k laid_out"),
    ("runtime: без пересэмплирования", "game/design/runtime.py",
     "        for attempt in range(1 + RESAMPLES):\n            if attempt:\n                z = self.z.copy()",
     "        for attempt in range(1):\n            if attempt:\n                z = self.z.copy()", RUNTIME),
    ("runtime: запасной вариант не включает код", "game/design/runtime.py",
     "        z = self.z\n        screen.set_knobs(knobs(z))\n        if check_layout(screen, L.capture(screen)):",
     "        z = self.z\n        L.apply(screen, rects or {})\n        if False:", RUNTIME),
    ("runtime: запасной без раскладки 1.1", "game/design/runtime.py",
     "            z = np.zeros(Z_DIM)\n            screen.set_knobs(knobs(z))", "            pass",
     RUNTIME + " -k fallback_reaches"),
    ("runtime: старая раскладка без повторной проверки", "game/design/runtime.py",
     "                if not check_layout(screen, rects):\n                    L.apply(screen, rects)",
     "                if True:\n                    L.apply(screen, rects)", "tests/test_game_ui.py -k text_fits"),
    ("widget: язык дизайнеру после текстов", "game/ui/widget.py",
     "                self.apply_theme(self.ctx.theme, relayout=False)\n            self.retranslate()",
     "                pass\n            self.retranslate()\n            if self.design is not None:\n"
     "                self.apply_theme(self.ctx.theme)", RUNTIME + " -k language_switch"),
    ("runtime: судит страницы до раскладки окна", "game/design/runtime.py",
     "        if screen.width() < MIN_SIZE[0] or screen.height() < MIN_SIZE[1]:",
     "        if False:", RUNTIME + " -k transient"),
    ("runtime: тайлы художника без законов", "game/design/runtime.py",
     "bad = check_tiles(drawn, code_tiles(keys, palette, z), kinds, self.limit)", "bad = []", RUNTIME),
    ("runtime: новая партия без новой руки", "game/design/runtime.py",
     "        self.z = sample_z(self.rng)\n        self._sets.clear()", "        self._sets.clear()",
     RUNTIME + " -k painter"),
    ("journal: запасной вариант не пишется на диск", "game/design/journal.py",
     "[-LAST:]\n        self.save()", "[-LAST:]", RUNTIME + " -k journal"),
    ("tiles: связь с соседом не видна", "game/design/tiles.py",
     "            incoming |= (nd == cells.OPPOSITE[e]) * (1 << e)", "            incoming |= 0", TILES),
    ("tiles: место в змейке не считается", "game/design/tiles.py",
     "                t[rc] = int(round((T_LEVELS - 1) * i / n))", "                t[rc] = 0", TILES),
    ("settings: карточки снова не на всю высоту", "game/ui/screens.py",
     "        outer.addLayout(cards, 1)", "        outer.addLayout(cards, 0)\n        outer.addStretch(1)",
     "tests/test_screens_elements.py"),
    ("stats: запасной вариант не показан", "game/ui/screens.py",
     "code=b(journal.get(\"layout_fallbacks\", 0)", "code=b(0", "tests/test_game_ui.py -k design"),
    # 2.1: свой вид «террариум» и находки проверки 17.10
    ("look: флажок без вида включённого", "game/ui/theme.py",
     "QCheckBox::indicator:checked {{ background: {t['accent']}; border-color: {t['accent']}; image: none; }}",
     "QCheckBox::indicator:checked {{ image: none; }}", LOOK + " -k checkbox"),
    ("look: масштаб окна не растёт", "game/design/knobs.py",
     "    return max(1.0, min(2.0, round(k * 20) / 20))", "    return 1.0", LOOK + " -k \"4k or scale\""),
    ("look: брошенный матч не поражение", "game/ui/screens.py",
     "        st.record_match(self.store.stats, self.level, False)\n", "", LOOK + " -k abandoned"),
    ("look: брошенный до раунда - поражение", "game/ui/screens.py",
     "        if m is None or m.phase == M.MATCH_OVER or self.rounds_done == 0:",
     "        if m is None or m.phase == M.MATCH_OVER:", LOOK + " -k before_first"),
    ("look: закрытие окна посреди матча молчит", "game/ui/widget.py",
     "        self.match_screen.abandon()\n", "", LOOK + " -k closing"),
    ("look: фон меню тикает в скрытой вкладке", "game/ui/widget.py",
     "        self.menu.pause()                    # живой фон", "        pass                    # живой фон",
     LOOK + " -k living"),
    ("look: настройки без террариума", "game/ui/screens.py",
     "    NAME = \"settings\"\n    TERRARIUM = True", "    NAME = \"settings\"\n    TERRARIUM = False", LOOK + " -k terrarium"),
    ("look: сеть-дизайнер не знает масштаба", "game/design/designer_net.py",
     "    x[12 + Z_DIM] = scale_for(w, h) - 1.0", "    x[12 + Z_DIM] = 0.0", "tests/test_design_nets.py -k inputs"),
]


if __name__ == "__main__":
    sys.exit(run_all(ROOT, MUTANTS, sys.argv[1:]))
