from pathlib import Path

from PySide6.QtWidgets import (
    QMessageBox,
)

from polylaue.model.editable import (
    default_path_validator,
    Editable,
    ParameterDescription,
    ParameterValue,
    ValidationError,
)


def empty_folder_validator(
    name: str,
    value,
    description: ParameterDescription,
    params: dict[str, ParameterValue],
    editable: Editable,
):
    default_path_validator(name, value, description, params, editable)

    current_params = editable.get_parameters()

    if value == current_params.get(name):
        return

    path = Path(value).resolve()

    if any(path.iterdir()):
        confirm_dialog = QMessageBox()
        confirm_dialog.setWindowTitle("Confirm directory choice")
        confirm_dialog.setText(
            "The chosen directory is not empty and data could be overwritten:"
            f"\n\n{path}\n\n"
            "Use this directory anyway?"
        )
        confirm_dialog.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm_dialog.exec() == QMessageBox.StandardButton.Yes:
            return
        else:
            raise ValidationError(
                f"The directory wasn't used because it isn't empty."
            )

    return
