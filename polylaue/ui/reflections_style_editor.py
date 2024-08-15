# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from PySide6.QtCore import QObject, Signal

from polylaue.ui.reflections_style import ReflectionsStyle
from polylaue.ui.utils.block_signals import block_signals
from polylaue.ui.utils.ui_loader import UiLoader


class ReflectionsStyleEditor(QObject):
    """Emitted when the style is modified"""

    style_edited = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = UiLoader().load_file('reflections_style_editor.ui', parent)

        self.setup_connections()

    def setup_connections(self):
        self.ui.symbol.currentIndexChanged.connect(self.modified)
        self.ui.point_size.valueChanged.connect(self.modified)
        self.ui.outline_thickness.valueChanged.connect(self.modified)
        self.ui.fill.toggled.connect(self.modified)
        self.ui.offset_x.valueChanged.connect(self.modified)
        self.ui.offset_y.valueChanged.connect(self.modified)

    def modified(self):
        self.style_edited.emit()

    @property
    def style(self) -> ReflectionsStyle:
        return ReflectionsStyle(**self.style_dict)

    @style.setter
    def style(self, v: ReflectionsStyle):
        self.style_dict = v.asdict()

    @property
    def style_dict(self) -> dict:
        return {
            'symbol': self.ui.symbol.currentText(),
            'size': self.ui.point_size.value(),
            'pen_width': self.ui.outline_thickness.value(),
            'use_brush': self.ui.fill.isChecked(),
            'offset_x': self.ui.offset_x.value(),
            'offset_y': self.ui.offset_y.value(),
        }

    @style_dict.setter
    def style_dict(self, d: dict):
        setters = {
            'symbol': self.ui.symbol.setCurrentText,
            'size': self.ui.point_size.setValue,
            'pen_width': self.ui.outline_thickness.setValue,
            'use_brush': self.ui.fill.setChecked,
            'offset_x': self.ui.offset_x.setValue,
            'offset_y': self.ui.offset_y.setValue,
        }

        with block_signals(*self.all_widgets):
            for k, v in d.items():
                setters[k](v)

    @property
    def all_widgets(self):
        return [
            getattr(self.ui, x)
            for x in (
                'symbol',
                'size',
                'outline',
                'fill',
                'offset_x',
                'offset_y',
            )
        ]
