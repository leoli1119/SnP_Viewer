import numpy as np
from Tkinter import *
import os
import re
import random
from scipy import interpolate

# interactive plotting
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import matplotlib.cm as cm

# my Stuff
from get_user_file_constraints import UserLimits
from Utils import smith
from Utils import moving_average
from Utils import power_gain
from Utils import vswr_circles
from Utils import spec_lines
from UI import UserInterface
from converter import convert_snp_csv
import syntax

# # import pdb;pdb.set_trace()
# if white_background:
#
# ----------User input
root = Tk()
user_input = UserInterface(master=root)  # creates instance of UI
user_input.mainloop()  # keeps loop open until user hits 'Go'
files = user_input.filez  # first file set
root.destroy()  # closes UI

# convert_data to pandas df
frames = []
order = []
for f in files:
    frames.append(convert_snp_csv(f))
    extension = os.path.splitext(f)[1]
    num = [int(s) for s in re.findall(r'\d+', extension)]  # get file extension
    order.append(num[0])  # get 'n' number associated with SnP  (order)

# get user constrains
file_type = max(order)  # finds highest order snp file
root = Tk()
user_val = UserLimits(file_type, master=root)
user_val.mainloop()
root.destroy()

white_background = False
if user_val.white_background.get() == 1:
    white_background = True
    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')

# necessary variable definitions
counter = 0
plots = {}
data = {}
traces = {}
colors = {}
markers = {}
got_lr = False

# *******************Setup interactive plotting*********************************

app = QtGui.QApplication([])
layout = QtGui.QGridLayout()
win = pg.GraphicsWindow(title="Basic plotting examples")
win.setLayout(layout)
win.resize(1000, 600)
win.setWindowTitle('Smith_Charts')
pg.setConfigOptions(antialias=True)  # Enable anti-aliasing for prettier plots

# ******************************Add Widgets*************************************
edit = QtGui.QPlainTextEdit()
edit.setPlainText(
    '#You can write python code in this window:\n#For example:\n' +
    "plots['Magnitude_S12'].setTitle('Test')")
highlight = syntax.PythonHighlighter(edit.document())

# Code input area and run button
editProxy = QtGui.QGraphicsProxyWidget()
editProxy.setWidget(edit)
button = QtGui.QPushButton('Run Code')
buttonProxy = QtGui.QGraphicsProxyWidget()
buttonProxy.setWidget(button)

# Create Radio Buttons for plot togeling
radios = {}
radio_proxies = []

color_map = iter(cm.gist_rainbow(np.linspace(0, 1, len(frames))))
for df in frames:
    trace = str(df['sourcefile'].iloc[0])
    red, green, blue, a = next(color_map)
    red = int(red * 255)
    green = int(green * 255)
    blue = int(blue * 255)

    colors[trace] = QtGui.QColor(red, green, blue)
    radios[trace] = QtGui.QCheckBox(trace)
    radios[trace].setStyleSheet('background-color:black;color: rgb(' +
                                str(red) + ',' +
                                str(green) + ',' +
                                str(blue) + ')')
    radios[trace].toggle()
    radio_proxies.append(QtGui.QGraphicsProxyWidget())
    radio_proxies[len(radio_proxies) - 1].setWidget(radios[trace])

# marker Stuff
mrkr_button = QtGui.QPushButton('Add Marker')
mrkr_buttonProxy = QtGui.QGraphicsProxyWidget()
mrkr_buttonProxy.setWidget(mrkr_button)
mrkr_input = QtGui.QLineEdit('Enter Frequency in MHz')
mrkr_inputProxy = QtGui.QGraphicsProxyWidget()
mrkr_inputProxy.setWidget(mrkr_input)
rmrkr_button = QtGui.QPushButton('Remove Markers')
rmrkr_buttonProxy = QtGui.QGraphicsProxyWidget()
rmrkr_buttonProxy.setWidget(rmrkr_button)

# combo Box
combo = QtGui.QComboBox()
combo.addItem("Pre-Canned-Funcitons")
combo.addItem("Power_Gain")
combo.addItem("moving_average")
combo.addItem("vswr_circles")
combo.addItem('spec_lines')
comboProxy = QtGui.QGraphicsProxyWidget()
comboProxy.setWidget(combo)

widget = QtGui.QGraphicsWidget()
layout = QtGui.QGraphicsGridLayout(widget)
layout.addItem(editProxy, 0, 0, 4, 1)
layout.addItem(buttonProxy, 0, 1)
layout.addItem(mrkr_buttonProxy, 1, 1)
layout.addItem(mrkr_inputProxy, 1, 2)
layout.addItem(rmrkr_buttonProxy, 1, 3)
layout.addItem(comboProxy, 2, 1)

for i, proxy in enumerate(radio_proxies):
    layout.addItem(proxy, 2, i + 2)

widget.setLayout(layout)
win.addItem(widget, 0, 0, 1, file_type)
win.nextRow()


def run_code():
    code = str(edit.toPlainText())
    exec code


def add_marker():
    global markers

    for t, value0 in traces.iteritems():

        for name_of_curve_, value1 in traces[t].iteritems():

            if radios[name_of_curve_].isChecked():

                markers[t].append(pg.CurvePoint(value1))
                if 'Smith' in t:
                    try:
                        f_mhz = float(mrkr_input.text())

                        # find real value
                        fr = interpolate.interp1d(
                            data[name_of_curve_]['MHz'],
                            data[name_of_curve_][
                                'S' + str(t[-2]) + str(t[-1]) + 'R'])
                        r_val = fr(f_mhz)

                        # find Imaginary value
                        fi = interpolate.interp1d(
                            data[name_of_curve_]['MHz'],
                            data[name_of_curve_][
                                'S' + str(t[-2]) + str(t[-1]) + 'I'])
                        i_val = fi(f_mhz)

                        markers[t].append(
                            pg.ArrowItem(pos=(r_val, i_val), angle=0))

                        # current marker is last marker added
                        last_value = len(markers[t]) - 1
                        current_marker = markers[t][last_value]
                        # add marker to plot
                        plots[t].addItem(current_marker)
                        # add text with data values to marker
                        text2 = pg.TextItem("test", anchor=(0.5, -1.0))
                        text2.setText('[%0.1f, %0.1f]' % (r_val, i_val))
                        text2.setParentItem(markers[t][last_value])
                    except (ValueError, IndexError):
                        print "unable to find frequency within range"
                else:
                    try:
                        f1 = interpolate.interp1d(
                            data[name_of_curve_]['MHz'],
                            data[name_of_curve_][
                                'S' + str(t[-2]) + str(t[-1]) + '_Mag'])

                        f_mhz = float(mrkr_input.text())
                        val = f1(f_mhz)
                        markers[t].append(
                            pg.ArrowItem(pos=(f_mhz, val), angle=0))

                        # current marker is last marker added
                        last_value = len(markers[t]) - 1
                        current_marker = markers[t][last_value]
                        plots[t].addItem(current_marker)
                        text2 = pg.TextItem("test", anchor=(0.5, -1.0))
                        text2.setText('[%0.1f, %0.1f]' % (f_mhz, val))
                        text2.setParentItem(markers[t][last_value])
                    except (ValueError, IndexError):
                        print "unable to find frequency within range"


def remove_markers():
    for title_, Marker_arrows in markers.iteritems():
        for mark in Marker_arrows:
            plots[title_].removeItem(mark)
        markers[title_] = []


def combo_func():
    """
    update combo
    """
    if combo.currentText() == 'moving_average':
        edit.setPlainText(moving_average)
    if combo.currentText() == 'Power_Gain':
        edit.setPlainText(power_gain)
    if combo.currentText() == 'vswr_circles':
        edit.setPlainText(vswr_circles)
    if combo.currentText() == 'spec_lines':
        edit.setPlainText(spec_lines)


button.clicked.connect(run_code)
mrkr_button.clicked.connect(add_marker)
rmrkr_button.clicked.connect(remove_markers)
combo.currentIndexChanged.connect(combo_func)

# ----------------------------End Add Widgets -------------------------------

# --------------------------------Build Graphs--------------------------------

for j in range(1, file_type + 1):  # first integer of snp
    for i in range(1, file_type + 1):  # second integer of snp

        if user_val.plot[counter].get() == 1:  # plot true/false

            # title is the main key for dictionaries
            if user_val.graph_type[counter].get() == 1:  # Magnitude title
                title = 'Magnitude_S' + str(j) + str(i)
            else:  # smith chart title
                title = 'Smith_S' + str(j) + str(i)

            plots[title] = win.addPlot(title=title, name=title)
            # legend[title] = plots[title].addLegend(size=(0.001, 0.001))
            traces[title] = {}
            # data[title] = {}
            markers[title] = []

            for df in frames:
                try:
                    name_of_curve = str(df['sourcefile'].iloc[0])  # for legend
                    data[name_of_curve] = df.drop('sourcefile', 1)

                    if user_val.graph_type[counter].get() == 1:  # dB
                        # Plot Magnitude data
                        traces[title][name_of_curve] = \
                            plots[title].plot(x=np.asarray(df['MHz']),
                                              y=np.asarray(df['S' + str(
                                                  j) + str(i) + '_Mag']),
                                              pen=colors[name_of_curve],
                                              row=i - 1, col=j - 1)

                        plots[title].showGrid(x=True, y=True, alpha=.8)

                        if not got_lr:
                            # if we are working on 1st Magnitude plot
                            # set limits of linear region item to max and min
                            lr = pg.LinearRegionItem(
                                [np.asarray(df['MHz']).min(),
                                 np.asarray(df['MHz']).max()])
                            lr.setZValue(-10)  # ???
                            plots[title].addItem(
                                lr)  # add lr object to Magnitude plot
                            got_lr = True  # Don't add more linear-region
                    else:
                        # () impedance = x+yi
                        x = np.asarray(df['S' + str(j) + str(i) + 'R'])
                        y = np.asarray(df['S' + str(j) + str(i) + 'I'])
                        # put smith chart in background
                        smith(p=plots[title],
                              white_backgorund=white_background)

                        # Plot Magnitude data
                        traces[title][name_of_curve] = \
                            plots[title].plot(x,
                                              y,
                                              pen=colors[name_of_curve])

                except KeyError:
                    pass
        counter += 1
    win.nextRow()


# --------------------------------------------------End Build Graphs-----------


def update():
    """
    This func updates the smith carts active region based on vertical bars
    """
    global traces, plots, data, lr
    min_limit, max_limit = lr.getRegion()  # in MHz
    for t, v in plots.iteritems():
        if 'Smith' in t:
            for curve, value1 in traces[t].iteritems():
                df_slice = data[curve][(data[curve]['MHz'] >= min_limit) &
                                       (data[curve]['MHz'] <= max_limit)]

                x_val = np.asarray(
                    df_slice['S' + str(t[-2]) + str(t[-1]) + 'R'])
                y_val = np.asarray(
                    df_slice['S' + str(t[-2]) + str(t[-1]) + 'I'])
                traces[t][curve].setData(x=x_val, y=y_val)


if got_lr:  # if there is a vertical bar then we can update smith charts
    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(50)


def toggle_trace():
    global radios
    for plt, val in plots.iteritems():
        # legend[plt].items = []
        # remove all traces
        for trace_, radio in radios.iteritems():
            try:
                plots[plt].removeItem(traces[plt][trace_])
            except KeyError:
                pass
        # populate necessary traces
        for trace_, radio in radios.iteritems():
            if radio.isChecked():
                try:
                    plots[plt].addItem(traces[plt][trace_])
                except KeyError:
                    pass


# connect all buttons to function
for t, r in radios.iteritems():
    r.stateChanged.connect(toggle_trace)


# links mouse position to data information (in window title)
def mouse_moved(evt):
    pos = evt[0]  # using signal proxy turns original arguments into a tuple
    for plot_, v in plots.iteritems():
        vb = v.vb
        if plots[plot_].sceneBoundingRect().contains(pos):
            mouse_point = vb.mapSceneToView(pos)
            data_point_x = mouse_point.x()
            data_point_y = mouse_point.y()

            if 'Smith' in plot_:  # if mouse in smith chart calculate smith data
                complex_point = np.complex(data_point_x + data_point_y * 1j)
                gamma = np.sqrt(np.square(np.real(complex_point)) +
                                np.square(np.imag(complex_point)))
                vswr = (1 + gamma) / (1 - gamma)
                return_loss = -20 * np.log10(gamma)

                data_string = \
                    ' Impedance: {0}+{1}j VSWR: {2} ReturnLoss: {3}'.format(
                        str(round(np.real(complex_point), 2)),
                        str(round(np.imag(complex_point), 2)),
                        str(round(vswr, 3)),
                        str(round(return_loss, 2)))

            else:  # if mouse in Magnitude plot return Freq & magnitude in dBm
                data_string = '(' + str(round(data_point_x, 3)) + 'MHz' + \
                              ' ,' + str(round(data_point_y, 3)) + 'dBm)'
                # label.setText(data_string)
            win.setWindowTitle('SnP_Plots: ' + data_string)


for plot, value in plots.iteritems():  # link mouse to function for each plot
    proxy = pg.SignalProxy(value.scene().sigMouseMoved,
                           rateLimit=60,
                           slot=mouse_moved)

'''Main Loop'''
# Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
