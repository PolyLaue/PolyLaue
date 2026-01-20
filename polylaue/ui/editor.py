# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

import logging

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from polylaue.model.editable import (
    Editable,
    ParameterType,
    ParameterDescription,
    ValidationError,
)

from polylaue.ui.scientificspinbox import ScientificDoubleSpinBox

logger = logging.getLogger(__name__)


class Field:
    def __init__(self, description: ParameterDescription):
        self._description = description
        self._widget = self.create_widget()
        self._widget.setToolTip(description.get('tooltip', ''))

    def create_widget(self) -> QWidget:
        raise NotImplementedError

    @property
    def description(self) -> ParameterDescription:
        return self._description

    @property
    def widget(self) -> QWidget:
        return self._widget

    @property
    def value(self):
        raise NotImplementedError

    @value.setter
    def value(self, v):
        raise NotImplementedError


class IntegerField(Field):
    def create_widget(self) -> QWidget:
        sb = QSpinBox()
        minimum = self._description.get('min')
        maximum = self._description.get('max')
        if minimum is not None:
            sb.setMinimum(int(minimum))
        if maximum is not None:
            sb.setMaximum(int(maximum))

        self._spin_box = sb

        return sb

    @property
    def value(self):
        return self._spin_box.value()

    @value.setter
    def value(self, v):
        self._spin_box.setValue(v)


class FloatField(Field):
    def create_widget(self) -> QWidget:
        sb = ScientificDoubleSpinBox()
        minimum = self._description.get('min')
        maximum = self._description.get('max')
        if minimum is not None:
            sb.setMinimum(minimum)
        if maximum is not None:
            sb.setMaximum(maximum)

        self._spin_box = sb

        return sb

    @property
    def value(self):
        return self._spin_box.value()

    @value.setter
    def value(self, v):
        self._spin_box.setValue(v)


class StringField(Field):
    def create_widget(self) -> QWidget:
        le = QLineEdit()
        self._line_edit = le

        return le

    @property
    def value(self):
        return self._line_edit.text()

    @value.setter
    def value(self, v):
        self._line_edit.setText(v)


class FileField(Field):
    def create_widget(self) -> QWidget:
        w = QWidget()
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        w.setLayout(h_layout)

        le = QLineEdit()
        pb = QPushButton()
        pixmapi = getattr(QStyle, 'SP_FileIcon')
        icon = pb.style().standardIcon(pixmapi)
        pb.setIcon(icon)
        pb.clicked.connect(self.on_select_click)

        h_layout.addWidget(le)
        h_layout.addWidget(pb)

        self._line_edit = le
        self._push_button = pb

        return w

    @property
    def value(self):
        return self._line_edit.text()

    @value.setter
    def value(self, v):
        self._line_edit.setText(v)

    def on_select_click(self):
        filter = ' '.join(
            map(lambda ext: f'*.{ext}', self.description.get('extensions', []))
        )

        selected_file, _filter = QFileDialog.getOpenFileName(
            self.widget,
            f"Select {self.description['label']}",
            self.value,
            filter=filter,
        )

        if not selected_file:
            # User canceled
            return

        self.value = selected_file


class FolderField(Field):
    def create_widget(self) -> QWidget:
        w = QWidget()
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        w.setLayout(h_layout)

        le = QLineEdit()
        pb = QPushButton()
        pixmapi = getattr(QStyle, 'SP_DirIcon')
        icon = pb.style().standardIcon(pixmapi)
        pb.setIcon(icon)
        pb.clicked.connect(self.on_select_click)

        h_layout.addWidget(le)
        h_layout.addWidget(pb)

        self._line_edit = le
        self._push_button = pb

        return w

    @property
    def value(self):
        return self._line_edit.text()

    @value.setter
    def value(self, v):
        self._line_edit.setText(v)

    def on_select_click(self):
        selected_directory = QFileDialog.getExistingDirectory(
            self.widget,
            f"Select {self.description['label']}",
            self.value,
        )

        if not selected_directory:
            # User canceled
            return

        self.value = selected_directory


class EnumField(Field):
    def create_widget(self) -> QWidget:
        cb = QComboBox()
        options = self._description.get('options')
        cb.addItems(options)

        self._combo_box = cb

        return cb

    @property
    def value(self) -> str:
        return self._combo_box.currentText()

    @value.setter
    def value(self, v: str):
        self._combo_box.setCurrentText(v)


SCALAR_PARAM_TYPE_TO_FIELD: dict[ParameterType, type[Field]] = {
    'integer': IntegerField,
    'float': FloatField,
    'string': StringField,
    'file': FileField,
    'folder': FolderField,
    'enum': EnumField,
}


class TupleField(Field):
    def __init__(self, description: ParameterDescription):
        element_field_class = SCALAR_PARAM_TYPE_TO_FIELD.get(
            description.get('subtype', 'integer'), IntegerField
        )

        n = description.get('length', 2)
        self._fields = tuple(
            element_field_class(description) for i in range(n)
        )

        super().__init__(description)

    def create_widget(self) -> QWidget:
        w = QWidget()
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        w.setLayout(h_layout)

        for field in self._fields:
            h_layout.addWidget(field.widget)

        return w

    @property
    def value(self):
        return tuple(field.value for field in self._fields)

    @value.setter
    def value(self, v):
        n = self.description.get('length', 2)
        for i in range(n):
            self._fields[i].value = v[i]


PARAM_TYPE_TO_FIELD: dict[ParameterType, type[Field]] = {
    **SCALAR_PARAM_TYPE_TO_FIELD,
    'tuple': TupleField,
}


class Editor:
    def __init__(self, editable: Editable, parent: QWidget = None):
        self.editable = editable

        self.fields = self.create_fields(editable)
        self.ui = self.create_ui(self.fields)

    def create_fields(self, editable: Editable) -> dict[str, Field]:
        parameters_description = editable.get_parameters_description()
        parameters_values = editable.get_parameters()

        fields: dict[str, Field] = {}

        for name, description in parameters_description.items():
            field_class = PARAM_TYPE_TO_FIELD.get(description['type'])

            if field_class is not None:
                field = field_class(description)
                field.value = parameters_values.get(name)
                fields[name] = field

        return fields

    def create_ui(self, fields: dict[str, Field]):
        w = QWidget()
        layout = QGridLayout()
        w.setLayout(layout)

        for row, field in enumerate(fields.values()):
            required = field.description.get('required', True)
            label = QLabel()
            label.setText(
                field.description['label'] + ('*' if required else '')
            )
            label.setToolTip(field.description.get('tooltip', ''))
            layout.addWidget(label, row, 0)
            layout.addWidget(field.widget, row, 1)

        return w


class EditorDialog(QDialog):
    def __init__(self, editable: Editable, parent: QWidget = None):
        super().__init__(parent)
        self.editable = editable
        self.editor = Editor(editable, parent)

        self.setWindowTitle(f'{editable.__class__.__name__} Editor')

        self.setLayout(QVBoxLayout(self))
        layout = self.layout()
        layout.addWidget(self.editor.ui)

        buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.button_box = QDialogButtonBox(buttons, self)
        layout.addWidget(self.button_box)

        self.setMinimumWidth(500)
        self.setFixedHeight(self.sizeHint().height())

        self.setup_connections()

    def setup_connections(self):
        self.button_box.accepted.connect(self.on_accepted)
        self.button_box.rejected.connect(self.on_rejected)

    def on_accepted(self):
        params = {}
        for key, field in self.editor.fields.items():
            params[key] = field.value

        try:
            self.editable.validate_parameters(params)
        except ValidationError as e:
            msg = f'Validation error. Check settings and try again.\n\n{e}'
            logger.critical(msg)
            QMessageBox.critical(self, 'Validation Failed', msg)
            return

        self.editable.set_parameters(params, validate=False)

        self.accept()

    def on_rejected(self):
        self.reject()
