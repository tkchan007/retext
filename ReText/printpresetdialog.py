# vim: ts=4:sw=4:expandtab

# This file is part of ReText (tkchan007/retext fork)
#
# Dialog for managing named print layout presets (margins + print font).
# Selecting a preset in the list immediately makes it the active one used
# by Print / Print Preview / Export to PDF; editing its fields only takes
# effect once Save is pressed.

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDoubleSpinBox,
    QFontDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ReText import globalSettings
from ReText.printpresets import (
    DEFAULT_PRESET,
    deletePreset,
    listPresets,
    loadPreset,
    newPresetId,
    savePreset,
)

DEFAULT_ROW_ID = ''  # sentinel used both in the list widget and in
                     # globalSettings.activePrintPresetId to mean "no
                     # custom preset -- use the built-in default"


def _describeFont(fontString):
    if not fontString:
        return '(document default)'
    font = QFont()
    font.fromString(fontString)
    return f'{font.family()}, {font.pointSize()}pt'


class PrintPresetDialog(QDialog):

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(self.tr('Print layout presets'))
        self.currentPresetId = None
        self.currentPreset = None

        self.list = QListWidget(self)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.currentItemChanged.connect(self._onSelectionChanged)

        self.newButton = QPushButton(self.tr('New...'), self)
        self.renameButton = QPushButton(self.tr('Rename...'), self)
        self.deleteButton = QPushButton(self.tr('Delete'), self)
        self.newButton.clicked.connect(self._onNew)
        self.renameButton.clicked.connect(self._onRename)
        self.deleteButton.clicked.connect(self._onDelete)

        listButtons = QHBoxLayout()
        listButtons.addWidget(self.newButton)
        listButtons.addWidget(self.renameButton)
        listButtons.addWidget(self.deleteButton)

        listLayout = QVBoxLayout()
        listLayout.addWidget(self.list)
        listLayout.addLayout(listButtons)

        self.marginTop = self._makeMarginSpinBox()
        self.marginBottom = self._makeMarginSpinBox()
        self.marginLeft = self._makeMarginSpinBox()
        self.marginRight = self._makeMarginSpinBox()

        self.fontLabel = QLabel(self)
        self.fontButton = QPushButton(self.tr('Change...'), self)
        self.fontButton.clicked.connect(self._onChangeFont)
        fontRow = QHBoxLayout()
        fontRow.addWidget(self.fontLabel, stretch=1)
        fontRow.addWidget(self.fontButton)

        self.saveButton = QPushButton(self.tr('Save'), self)
        self.saveButton.clicked.connect(self._onSave)

        form = QFormLayout()
        form.addRow(self.tr('Top margin (in):'), self.marginTop)
        form.addRow(self.tr('Bottom margin (in):'), self.marginBottom)
        form.addRow(self.tr('Left margin (in):'), self.marginLeft)
        form.addRow(self.tr('Right margin (in):'), self.marginRight)
        form.addRow(self.tr('Print font:'), fontRow)

        editLayout = QVBoxLayout()
        editLayout.addLayout(form)
        editLayout.addWidget(self.saveButton, alignment=Qt.AlignmentFlag.AlignLeft)
        editLayout.addStretch(1)

        closeButton = QPushButton(self.tr('Close'), self)
        closeButton.clicked.connect(self.accept)

        mainLayout = QHBoxLayout()
        mainLayout.addLayout(listLayout, stretch=1)
        mainLayout.addLayout(editLayout, stretch=2)

        outerLayout = QVBoxLayout(self)
        outerLayout.addLayout(mainLayout)
        outerLayout.addWidget(closeButton, alignment=Qt.AlignmentFlag.AlignRight)

        self._reloadList()

    def _makeMarginSpinBox(self):
        spinBox = QDoubleSpinBox(self)
        spinBox.setRange(0, 5)
        spinBox.setSingleStep(0.05)
        spinBox.setDecimals(2)
        return spinBox

    def _reloadList(self, selectId=None):
        self.list.blockSignals(True)
        self.list.clear()
        defaultItem = QListWidgetItem(DEFAULT_PRESET['name'])
        defaultItem.setData(Qt.ItemDataRole.UserRole, DEFAULT_ROW_ID)
        self.list.addItem(defaultItem)
        rowToSelect = 0
        for index, (presetId, name) in enumerate(listPresets(), start=1):
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, presetId)
            self.list.addItem(item)
            if presetId == selectId:
                rowToSelect = index
        if selectId is None and globalSettings.activePrintPresetId:
            for row in range(self.list.count()):
                if self.list.item(row).data(Qt.ItemDataRole.UserRole) == \
                        globalSettings.activePrintPresetId:
                    rowToSelect = row
                    break
        self.list.blockSignals(False)
        self.list.setCurrentRow(rowToSelect)

    def _onSelectionChanged(self, current, previous):
        if current is None:
            return
        presetId = current.data(Qt.ItemDataRole.UserRole)
        self.currentPresetId = presetId
        if presetId == DEFAULT_ROW_ID:
            self.currentPreset = dict(DEFAULT_PRESET)
        else:
            self.currentPreset = loadPreset(presetId) or dict(DEFAULT_PRESET)
        self._loadFormFromCurrentPreset()

        isDefault = presetId == DEFAULT_ROW_ID
        self.renameButton.setEnabled(not isDefault)
        self.deleteButton.setEnabled(not isDefault)
        self.saveButton.setEnabled(not isDefault)
        for spinBox in (self.marginTop, self.marginBottom, self.marginLeft, self.marginRight):
            spinBox.setEnabled(not isDefault)
        self.fontButton.setEnabled(not isDefault)

        # Selecting a preset immediately makes it the active one.
        globalSettings.activePrintPresetId = presetId

    def _loadFormFromCurrentPreset(self):
        preset = self.currentPreset
        self.marginTop.setValue(preset['marginTop'])
        self.marginBottom.setValue(preset['marginBottom'])
        self.marginLeft.setValue(preset['marginLeft'])
        self.marginRight.setValue(preset['marginRight'])
        self.fontLabel.setText(_describeFont(preset['printFont']))

    def _onChangeFont(self):
        initialFont = QFont()
        if self.currentPreset['printFont']:
            initialFont.fromString(self.currentPreset['printFont'])
        font, ok = QFontDialog.getFont(initialFont, self)
        if ok:
            self.currentPreset['printFont'] = font.toString()
            self.fontLabel.setText(_describeFont(self.currentPreset['printFont']))

    def _onSave(self):
        if self.currentPresetId == DEFAULT_ROW_ID:
            return
        self.currentPreset['marginTop'] = self.marginTop.value()
        self.currentPreset['marginBottom'] = self.marginBottom.value()
        self.currentPreset['marginLeft'] = self.marginLeft.value()
        self.currentPreset['marginRight'] = self.marginRight.value()
        savePreset(self.currentPresetId, self.currentPreset)

    def _onNew(self):
        name, ok = QInputDialog.getText(self, self.tr('New print preset'),
            self.tr('Name:'))
        if not ok or not name.strip():
            return
        presetId = newPresetId()
        preset = dict(DEFAULT_PRESET)
        preset['name'] = name.strip()
        savePreset(presetId, preset)
        self._reloadList(selectId=presetId)

    def _onRename(self):
        if self.currentPresetId == DEFAULT_ROW_ID:
            return
        name, ok = QInputDialog.getText(self, self.tr('Rename print preset'),
            self.tr('Name:'), text=self.currentPreset['name'])
        if not ok or not name.strip():
            return
        self.currentPreset['name'] = name.strip()
        savePreset(self.currentPresetId, self.currentPreset)
        self._reloadList(selectId=self.currentPresetId)

    def _onDelete(self):
        if self.currentPresetId == DEFAULT_ROW_ID:
            return
        answer = QMessageBox.question(self, self.tr('Delete print preset'),
            self.tr('Delete preset "%s"?') % self.currentPreset['name'])
        if answer != QMessageBox.StandardButton.Yes:
            return
        deletePreset(self.currentPresetId)
        if globalSettings.activePrintPresetId == self.currentPresetId:
            globalSettings.activePrintPresetId = DEFAULT_ROW_ID
        self._reloadList()
