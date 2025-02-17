# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QWidget, QPushButton, QDialog, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QFileDialog,
                             QHBoxLayout, QFrame, QLabel, QApplication,
                             QToolBar, QAction)

from PyQt5.QtCore import QSize, pyqtSlot, pyqtSignal, QMetaObject, Qt
from PyQt5.QtGui import QIcon
import OCC.Display.backend
back = OCC.Display.backend.load_backend()

from OCC.Display.qtDisplay import qtViewer3d
from OCC.Core.AIS import AIS_Shaded,AIS_WireFrame, AIS_ColoredShape, \
    AIS_Axis, AIS_Line
from OCC.Core.Aspect import Aspect_GDM_Lines, Aspect_GT_Rectangular, Aspect_GFM_VER
from OCC.Core.Quantity import Quantity_NOC_BLACK as BLACK, \
    Quantity_TOC_RGB as TOC_RGB, Quantity_Color
from OCC.Core.Geom import Geom_CylindricalSurface, Geom_Plane, Geom_Circle,\
     Geom_TrimmedCurve, Geom_Axis1Placement, Geom_Axis2Placement, Geom_Line
from OCC.Core.gp import gp_Trsf, gp_Vec, gp_Ax3, gp_Dir, gp_Pnt, gp_Ax1

from ..utils import layout, get_save_filename
from ..mixins import ComponentMixin
from ..icons import icon
from ..cq_utils import to_occ_color

from pyqtgraph.parametertree import Parameter
import qtawesome as qta


class OCCViewer(QWidget,ComponentMixin):

    name = '3D Viewer'

    preferences = Parameter.create(name='Pref',children=[
        {'name': 'Fit automatically', 'type': 'bool', 'value': True},
        {'name': 'Use gradient', 'type': 'bool', 'value': False},
        {'name': 'Background color', 'type': 'color', 'value': (95,95,95)},
        {'name': 'Background color (aux)', 'type': 'color', 'value': (30,30,30)},
        {'name': 'Default object color', 'type': 'color', 'value': "FF0"}])

    IMAGE_EXTENSIONS = 'png'

    sigObjectSelected = pyqtSignal(list)

    def __init__(self,parent=None):

        super(OCCViewer,self).__init__(parent)
        ComponentMixin.__init__(self)

        self.canvas = qtViewer3d()
        self.canvas.InitDriver()
        self.canvas.sig_topods_selected.connect(self.handle_selection)

        self.create_actions(self)

        self.layout_ = layout(self,
                             [self.canvas,],
                             top_widget=self,
                             margin=0)
        
        self.updatePreferences()

    def updatePreferences(self,*args):

        color1 = to_occ_color(self.preferences['Background color'])
        color2 = to_occ_color(self.preferences['Background color (aux)'])

        if not self.preferences['Use gradient']:
            color2 = color1
        self.canvas._display.View.SetBgGradientColors(color1,color2,True)
        
        self.canvas.update()

    def create_actions(self,parent):

        self._actions =  \
                {'View' : [QAction(qta.icon('fa.arrows-alt'),
                                   'Fit',
                                   parent,
                                   triggered=self.fit),
                          QAction(QIcon(':/images/icons/isometric_view.svg'),
                                  'Iso',
                                  parent,
                                  triggered=self.iso_view),
                          QAction(QIcon(':/images/icons/top_view.svg'),
                                  'Top',
                                  parent,
                                  triggered=self.top_view),
                          QAction(QIcon(':/images/icons/bottom_view.svg'),
                                  'Bottom',
                                  parent,
                                  triggered=self.bottom_view),
                          QAction(QIcon(':/images/icons/front_view.svg'),
                                  'Front',
                                  parent,
                                  triggered=self.front_view),
                          QAction(QIcon(':/images/icons/back_view.svg'),
                                  'Back',
                                  parent,
                                  triggered=self.back_view),
                          QAction(QIcon(':/images/icons/left_side_view.svg'),
                                  'Left',
                                  parent,
                                  triggered=self.left_view),
                          QAction(QIcon(':/images/icons/right_side_view.svg'),
                                  'Right',
                                  parent,
                                  triggered=self.right_view),
                          QAction(qta.icon('fa.square-o'),
                                  'Wireframe',
                                  parent,
                                  triggered=self.wireframe_view),
                                  QAction(qta.icon('fa.square'),
                                          'Shaded',
                                          parent,
                                          triggered=self.shaded_view)],
                 'Tools' : [QAction(icon('screenshot'),
                                   'Screenshot',
                                   parent,
                                   triggered=self.save_screenshot)]}

    def toolbarActions(self):

        return self._actions['View']


    def clear(self):

        self.displayed_shapes = []
        self.displayed_ais = []
        self.canvas._display.EraseAll()
        context = self._get_context()
        context.PurgeDisplay()
        context.RemoveAll()

    def _display(self,shape):

        ais = self.canvas._display.DisplayShape(shape)

        self.displayed_shapes.append(shape)
        self.displayed_ais.append(ais)

        self.canvas._display.Repaint()

    @pyqtSlot(object)
    def display(self,ais):

        context = self._get_context()
        context.Display(ais)

        self.canvas._display.Repaint()

        if self.preferences['Fit automatically']: self.fit()

    @pyqtSlot(list)
    @pyqtSlot(list,bool)
    def display_many(self,ais_list,fit=None):

        context = self._get_context()
        for ais in ais_list:
            context.Display(ais)

        self.canvas._display.Repaint()

        if self.preferences['Fit automatically'] and fit is None:
            self.fit()
        elif fit:
            self.fit()

    @pyqtSlot(QTreeWidgetItem,int)
    def update_item(self,item,col):

        ctx = self._get_context()
        if item.checkState(0):
            ctx.Display(item.ais)
        else:
            ctx.Erase(item.ais)

    @pyqtSlot(list)
    def remove_items(self,ais_items):

        ctx = self._get_context()
        for ais in ais_items: ctx.Erase(ais)

    @pyqtSlot()
    def redraw(self):

        self._get_viewer().Redraw()

    def fit(self):

        self.canvas._display.FitAll()

    def iso_view(self):

        v = self._get_view()
        v.SetProj(1,1,1)
        v.SetTwist(0)

    def bottom_view(self):

        v = self._get_view()
        v.SetProj(0,0,-1)
        v.SetTwist(0)

    def top_view(self):

        v = self._get_view()
        v.SetProj(0,0,1)
        v.SetTwist(0)

    def front_view(self):

        v = self._get_view()
        v.SetProj(0,1,0)
        v.SetTwist(0)

    def back_view(self):

        v = self._get_view()
        v.SetProj(0,-1,0)
        v.SetTwist(0)

    def left_view(self):

        v = self._get_view()
        v.SetProj(-1,0,0)
        v.SetTwist(0)

    def right_view(self):

        v = self._get_view()
        v.SetProj(1,0,0)
        v.SetTwist(0)

    def shaded_view(self):

        c = self._get_context()
        c.SetDisplayMode(AIS_Shaded)

    def wireframe_view(self):

        c = self._get_context()
        c.SetDisplayMode(AIS_WireFrame)

    def show_grid(self,
                  step=1.,
                  size=10.+1e-6,
                  color1=(.7,.7,.7),
                  color2=(0,0,0)):

        viewer = self._get_viewer()
        viewer.ActivateGrid(Aspect_GT_Rectangular,
                            Aspect_GDM_Lines)
        viewer.SetRectangularGridGraphicValues(size, size, 0)
        viewer.SetRectangularGridValues(0, 0, step, step, 0)
        grid = viewer.Grid()
        grid.SetColors(Quantity_Color(*color1,TOC_RGB),
                       Quantity_Color(*color2,TOC_RGB))

    def hide_grid(self):

        viewer = self._get_viewer()
        viewer.DeactivateGrid()

    @pyqtSlot(bool,float)
    @pyqtSlot(bool)
    def toggle_grid(self,
                    value : bool,
                    dim : float = 10.):

        if value:
            self.show_grid(step=dim/20,size=dim+1e-9)
        else:
            self.hide_grid()

    @pyqtSlot(gp_Ax3)
    def set_grid_orientation(self,orientation : gp_Ax3):

        viewer = self._get_viewer()
        viewer.SetPrivilegedPlane(orientation)

    def show_axis(self,origin = (0,0,0), direction=(0,0,1)):

        ax_placement = Geom_Axis1Placement(gp_Ax1(gp_Pnt(*origin),
                                                  gp_Dir(*direction)))
        ax = AIS_Axis(ax_placement)
        self._display_ais(ax)

    def show_line(self,origin = (0,0,0), direction=(0,0,1)):

        line_placement = Geom_Line(gp_Ax1(gp_Pnt(*origin),
                                   gp_Dir(*direction)))
        line = AIS_Line(line_placement)
        self._display_ais(line)

    def save_screenshot(self):

        fname = get_save_filename(self.IMAGE_EXTENSIONS)
        if fname is not '':
             self._get_view().Dump(fname)

    def _display_ais(self,ais):

        self._get_context().Display(ais)


    def _get_view(self):

        return self.canvas._display.GetView()

    def _get_viewer(self):

        return self.canvas._display.GetViewer()

    def _get_context(self):

        return self.canvas._display.GetContext()

    @pyqtSlot(list)
    def handle_selection(self,obj):

        self.sigObjectSelected.emit(obj)

    @pyqtSlot(list)
    def set_selected(self,ais):

        ctx = self._get_context()
        ctx.ClearSelected(False)

        for obj in ais:
            ctx.AddOrRemoveSelected(obj,False)

        self.redraw()


if __name__ == "__main__":

    import sys
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox

    app = QApplication(sys.argv)
    viewer = OCCViewer()
    viewer.show_line()

    dlg = QDialog()
    dlg.setFixedHeight(400)
    dlg.setFixedWidth(600)

    layout(dlg,(viewer,),dlg)
    dlg.show()

    box = BRepPrimAPI_MakeBox(20,20,30)
    box_ais = AIS_ColoredShape(box.Shape())
    viewer.display(box_ais)

    sys.exit(app.exec_())