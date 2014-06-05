#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2012 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import re
from decimal import Decimal
from electrum import bitcoin

RE_ADDRESS = '[1-9A-HJ-NP-Za-km-z]{26,}'
RE_ALIAS = '(.*?)\s*\<([1-9A-HJ-NP-Za-km-z]{26,})\>'

frozen_style = "QWidget { background-color:none; border:none;}"
normal_style = "QTextEdit { }"

class PayToEdit(QTextEdit):

    def __init__(self, amount_edit):
        QTextEdit.__init__(self)
        self.amount_edit = amount_edit
        self.document().contentsChanged.connect(self.update_size)
        self.heightMin = 0
        self.heightMax = 150
        self.setMinimumHeight(27)
        self.setMaximumHeight(27)
        self.c = None

    def lock_amount(self):
        self.amount_edit.setFrozen(True)

    def unlock_amount(self):
        self.amount_edit.setFrozen(False)

    def setFrozen(self, b):
        self.setReadOnly(b)
        self.setStyleSheet(frozen_style if b else normal_style)

    def setGreen(self):
        self.setStyleSheet("QWidget { background-color:#00ff00;}")

    def parse_address_and_amount(self, line):
        x, y = line.split(',')
        address = self.parse_address(x)
        amount = self.parse_amount(y)
        return address, amount


    def parse_amount(self, x):
        p = pow(10, self.amount_edit.decimal_point())
        return int( p * Decimal(x.strip()))


    def parse_address(self, line):
        r = line.strip()
        m = re.match('^'+RE_ALIAS+'$', r)
        address = m.group(2) if m else r
        assert bitcoin.is_address(address)
        return address


    def check_text(self):
        # filter out empty lines
        lines = filter( lambda x: x, self.lines())
        outputs = []
        total = 0

        if len(lines) == 1:
            try:
                self.payto_address = self.parse_address(lines[0])
            except:
                self.payto_address = None

            if self.payto_address:
                self.unlock_amount()
                return

        for line in lines:
            try:
                to_address, amount = self.parse_address_and_amount(line)
            except:
                continue
                
            outputs.append((to_address, amount))
            total += amount

        self.outputs = outputs
        self.payto_address = None

        if total:
            self.amount_edit.setAmount(total)
        else:
            self.amount_edit.setText("")

        if total or len(lines)>1:
            self.lock_amount()
        else:
            self.unlock_amount()



    def get_outputs(self):

        if self.payto_address:
            
            if not bitcoin.is_address(self.payto_address):
                QMessageBox.warning(self, _('Error'), _('Invalid Bitcoin Address') + ':\n' + to_address, _('OK'))
                return

            try:
                amount = self.amount_edit.get_amount()
            except Exception:
                QMessageBox.warning(self, _('Error'), _('Invalid Amount'), _('OK'))
                return

            outputs = [(self.payto_address, amount)]
            return outputs

        return self.outputs


    def lines(self):
        return str(self.toPlainText()).split('\n')


    def is_multiline(self):
        return len(self.lines()) > 1


    def update_size(self):
        docHeight = self.document().size().height()
        if self.heightMin <= docHeight <= self.heightMax:
            self.setMinimumHeight(docHeight + 2)
            self.setMaximumHeight(docHeight + 2)


    def setCompleter(self, completer):
        self.c = completer
        self.c.setWidget(self)
        self.c.setCompletionMode(QCompleter.PopupCompletion)
        self.c.activated.connect(self.insertCompletion)


    def insertCompletion(self, completion):
        if self.c.widget() != self:
            return
        tc = self.textCursor()
        extra = completion.length() - self.c.completionPrefix().length()
        tc.movePosition(QTextCursor.Left)
        tc.movePosition(QTextCursor.EndOfWord)
        tc.insertText(completion.right(extra))
        self.setTextCursor(tc)
        self.check_text()
 

    def textUnderCursor(self):
        tc = self.textCursor()
        tc.select(QTextCursor.WordUnderCursor)
        return tc.selectedText()


    def keyPressEvent(self, e):
        if self.c.popup().isVisible():
            if e.key() in [Qt.Key_Enter, Qt.Key_Return]:
                e.ignore()
                return

        if e.key() in [Qt.Key_Tab]:
            e.ignore()
            return

        if e.key() in [Qt.Key_Down, Qt.Key_Up] and not self.is_multiline():
            e.ignore()
            return

        isShortcut = (e.modifiers() and Qt.ControlModifier) and e.key() == Qt.Key_E

        if not self.c or not isShortcut:
            QTextEdit.keyPressEvent(self, e)
            self.check_text()


        ctrlOrShift = e.modifiers() and (Qt.ControlModifier or Qt.ShiftModifier)
        if self.c is None or (ctrlOrShift and e.text().isEmpty()):
            return

        eow = QString("~!@#$%^&*()_+{}|:\"<>?,./;'[]\\-=")
        hasModifier = (e.modifiers() != Qt.NoModifier) and not ctrlOrShift;
        completionPrefix = self.textUnderCursor()

        if not isShortcut and (hasModifier or e.text().isEmpty() or completionPrefix.length() < 1 or eow.contains(e.text().right(1)) ):
            self.c.popup().hide()
            return

        if completionPrefix != self.c.completionPrefix():
            self.c.setCompletionPrefix(completionPrefix);
            self.c.popup().setCurrentIndex(self.c.completionModel().index(0, 0))

        cr = self.cursorRect()
        cr.setWidth(self.c.popup().sizeHintForColumn(0) + self.c.popup().verticalScrollBar().sizeHint().width())
        self.c.complete(cr)


