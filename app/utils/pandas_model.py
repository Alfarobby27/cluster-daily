# app/utils/pandas_model.py
from PyQt5.QtCore import QAbstractTableModel, Qt, QVariant

class PandasModel(QAbstractTableModel):
    def __init__(self, df=None):
        super().__init__()
        self._df = df

    def update(self, df):
        self.beginResetModel()
        self._df = df
        self.endResetModel()

    def rowCount(self, parent=None):
        return 0 if self._df is None else len(self._df.index)

    def columnCount(self, parent=None):
        return 0 if self._df is None else len(self._df.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or self._df is None:
            return QVariant()
        if role == Qt.DisplayRole:
            val = self._df.iat[index.row(), index.column()]
            return str(val)
        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if self._df is None:
            return QVariant()
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._df.columns[section])
            else:
                return str(self._df.index[section])
        return QVariant()
