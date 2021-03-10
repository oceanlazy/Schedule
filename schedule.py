import sys
import pickle
from math import gcd
from datetime import timedelta, datetime

from PyQt5 import QtCore
from PyQt5.uic import loadUi
from PyQt5.QtMultimedia import QSound
from PyQt5.QtGui import QPalette, QBrush, QPixmap
from PyQt5.QtWidgets import QApplication, QWidget, QDesktopWidget, QInputDialog


class Schedule(QWidget):
    def __init__(self, *args):
        super().__init__(*args)
        loadUi('ui.ui', self)
        self.setWindowState(self.windowState() and ~QtCore.Qt.WindowMinimized or QtCore.Qt.WindowActive)
        self.move(QDesktopWidget().availableGeometry().center() - self.frameGeometry().center())
        self.button_relax.clicked.connect(lambda action: self.start('relax'))
        self.button_work.clicked.connect(lambda action: self.start('work'))
        self.button_pause_continue.clicked.connect(self.pause_continue)
        self.button_pause_continue.hide()
        self.button_settings.clicked.connect(lambda action: self.change_timeout())
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.event_second_passed)
        self.sound_timer = QSound('alarm.wav', self)
        self.epoch = datetime(1970, 1, 1, 0, 0, 0)
        self.prev_minute = 0
        default_session = {'timeout': 45,
                           'countdown': datetime(1970, 1, 1, 0, 45, 0),
                           'prev_action': '',
                           'action': '',
                           'header': 'Ready',
                           'progress': 0,
                           'current_ratio': '0:0',
                           'button_pause_continue': 'Pause',
                           'title': 'Schedule',
                           'day': datetime.now().day,
                           'current_work': self.epoch,
                           'current_relax': self.epoch,
                           'today_work': self.epoch,
                           'today_relax': self.epoch,
                           }

        try:
            with open('session.pickle', 'rb') as file:
                temp_session = pickle.load(file)
            if temp_session['day'] == datetime.now().day:
                self.session = temp_session
            else:
                self.session = default_session
        except (FileNotFoundError, pickle.UnpicklingError):
            self.session = default_session

        if self.session['countdown'].minute != self.session['timeout']:
            self.session['button_pause_continue'] = 'Continue'
            self.button_pause_continue.show()

        self.set_display()
        self.add_bg()

    def change_timeout(self):
        user_input, confirmed = QInputDialog.getText(self, 'Change timeout...',
                                                     'Please insert new timeout',
                                                     text=str(self.session['timeout']),
                                                     flags=QtCore.Qt.WindowTitleHint)
        if confirmed:
            try:
                int_user_input = int(user_input)
            except TypeError:
                return
            else:
                if 1 <= int_user_input <= 60:
                    self.session['timeout'] = int_user_input
                    self.session['countdown'] = datetime(1970, 1, 1, 0, self.session['timeout'], 0)
                    self.session['progress'] = 0
                    self.session['header'] = 'Ready'
                    self.session['title'] = 'Schedule'
                    self.button_pause_continue.hide()
                    self.set_display()

    def set_display(self):
        self.ui_header.setText(self.session['header'])
        self.button_pause_continue.setText(self.session['button_pause_continue'])
        self.ui_timer.setText(self.session['countdown'].strftime('%H:%M:%S'))
        self.ui_progress_bar.setValue(self.session['progress'])
        self.ui_today_work.setText(self.session['today_work'].strftime('%H:%M:%S'))
        self.ui_current_work.setText(self.session['current_work'].strftime('%H:%M:%S'))
        self.ui_today_relax.setText(self.session['today_relax'].strftime('%H:%M:%S'))
        self.ui_current_relax.setText(self.session['current_relax'].strftime('%H:%M:%S'))
        self.ui_current_ratio.setText(self.session['current_ratio'])
        self.setWindowTitle(self.session['title'])

    def add_bg(self):
        palette = QPalette()
        palette.setBrush(QPalette.Background, QBrush(QPixmap("bg.jpg")))
        self.setPalette(palette)

    def event_action(self):
        self.session['today_{}'.format(self.session['action'])] += timedelta(seconds=1)
        if self.session['prev_action'] == self.session['action'] or not self.session['prev_action']:
            self.session['current_{}'.format(self.session['action'])] += timedelta(seconds=1)
        else:
            self.session['prev_action'] = self.session['action']
            self.session['current_{}'.format(self.session['action'])] = datetime(1970, 1, 1, 0, 0, 1)
        if self.session['action'] == 'work':
            self.session['current_relax'] = self.epoch
        else:
            self.session['current_work'] = self.epoch
        self.set_display()

    def get_ratio(self):
        minutes_work = self.session['today_work'].minute
        minutes_relax = self.session['today_relax'].minute
        divisor = gcd(minutes_work, minutes_relax)
        ratio_work = int(minutes_work / divisor) if minutes_work else 0
        ratio_relax = int(minutes_relax / divisor) if minutes_relax else 0
        return ratio_work, ratio_relax

    def event_second_passed(self):
        self.session['countdown'] -= timedelta(seconds=1)
        time_elapsed = self.session['countdown'].minute * 60 + self.session['countdown'].second
        self.session['progress'] = (self.session['timeout'] * 60 - time_elapsed) / (self.session['timeout'] * 60) * 100
        self.event_action()
        if self.session['countdown'].minute != self.prev_minute:
            pass
        self.prev_minute = self.session['countdown'].minute
        self.session['current_ratio'] = '{}:{}'.format(*self.get_ratio())
        self.session['title'] = self.session['countdown'].strftime('%H:%M:%S')
        if not self.session['countdown'].hour \
                and not self.session['countdown'].minute \
                and not self.session['countdown'].second:
            self.session['countdown'] = datetime(1970, 1, 1, 0, self.session['timeout'], 0)
            self.session['progress'] = 0
            self.session['title'] = 'Schedule'
            self.session['header'] = 'Ready'
            self.session['button_pause_continue'] = 'OK'
            self.timer.stop()
            self.sound_timer.play()
            self.button_relax.show()
            self.button_work.show()
            self.button_pause_continue.clicked.disconnect(self.pause_continue)
            self.button_pause_continue.clicked.connect(self.stop_sound)
        self.set_display()

        with open('session.pickle', 'wb') as file:
            pickle.dump(self.session, file)

    def start(self, action):
        self.session['header'] = '{}...'.format(action.capitalize())
        self.session['button_pause_continue'] = 'Pause'
        self.session['prev_action'] = self.session['action'].lower()
        self.session['action'] = action
        self.session['countdown'] = datetime(1970, 1, 1, 0, self.session['timeout'], 0)
        self.session['progress'] = 0
        self.sound_timer.stop()
        try:
            self.button_pause_continue.clicked.disconnect(self.stop_sound)
            self.button_pause_continue.clicked.connect(self.pause_continue)
        except TypeError:
            pass
        self.button_pause_continue.show()
        self.button_settings.hide()
        self.set_display()
        self.timer.start(1000)

    def stop_sound(self):
        self.session['header'] = 'Ready'
        self.sound_timer.stop()
        self.button_settings.show()
        self.button_pause_continue.hide()
        self.button_pause_continue.clicked.disconnect(self.stop_sound)
        self.button_pause_continue.clicked.connect(self.pause_continue)
        self.set_display()

    def pause_continue(self):
        if self.timer.isActive():
            self.session['header'] = 'Pause'.format(self.session['action'].capitalize())
            self.session['button_pause_continue'] = 'Continue'
            self.button_settings.show()
            self.timer.stop()
        else:
            self.session['header'] = '{}...'.format(self.session['action'].capitalize())
            self.session['button_pause_continue'] = 'Pause'
            self.button_settings.hide()
            self.timer.start(1000)
        self.set_display()


app = QApplication(sys.argv)
widget = Schedule()
widget.show()
sys.exit(app.exec_())
