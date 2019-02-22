from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication

from UM.Application import Application
from UM.Math.Vector import Vector
from UM.Tool import Tool
from UM.Event import Event, MouseEvent
from UM.Mesh.MeshBuilder import MeshBuilder
from UM.Scene.Selection import Selection

from cura.CuraApplication import CuraApplication
from cura.Scene.CuraSceneNode import CuraSceneNode
from cura.PickingPass import PickingPass

from UM.Operations.GroupedOperation import GroupedOperation
from UM.Operations.AddSceneNodeOperation import AddSceneNodeOperation
from UM.Operations.RemoveSceneNodeOperation import RemoveSceneNodeOperation
from cura.Operations.SetParentOperation import SetParentOperation

from cura.Scene.SliceableObjectDecorator import SliceableObjectDecorator
from cura.Scene.BuildPlateDecorator import BuildPlateDecorator

from UM.Settings.SettingInstance import SettingInstance

import numpy

class ClickAndPlace(Tool):

    def __init__(self):
        super().__init__()
        self._shortcut_key = Qt.Key_P
        self._controller = self.getController()

        self._selection_pass = None

        # Note: if the selection is cleared with this tool active, there is no way to switch to
        # another tool than to reselect an object (by clicking it) because the tool buttons in the
        # toolbar will have been disabled. That is why we need to ignore the first press event
        # after the selection has been cleared.
        Selection.selectionChanged.connect(self._onSelectionChanged)
        self._had_selection = False

        self._had_selection_timer = QTimer()
        self._had_selection_timer.setInterval(0)
        self._had_selection_timer.setSingleShot(True)
        self._had_selection_timer.timeout.connect(self._selectionChangeDelay)

    def event(self, event):
        super().event(event)
        modifiers = QApplication.keyboardModifiers()
        ctrl_is_active = modifiers & Qt.ControlModifier

        if event.type == Event.MousePressEvent and MouseEvent.LeftButton in event.buttons and self._controller.getToolsEnabled():
            if ctrl_is_active:
                self._controller.setActiveTool("TranslateTool")
                return

            if self._selection_pass is None:
                # The selection render pass is used to identify objects in the current view
                self._selection_pass = Application.getInstance().getRenderer().getRenderPass("selection")

            picked_node = self._controller.getScene().findObject(self._selection_pass.getIdAtPosition(event.x, event.y))
            if not picked_node:
                # There is no slicable object at the picked location
                return

            node_stack = picked_node.callDecoration("getStack")
            if node_stack:
                if node_stack.getProperty("anti_overhang_mesh", "value"):
                    self._removeEraserMesh(picked_node)
                    return

                elif node_stack.getProperty("support_mesh", "value") or node_stack.getProperty("infill_mesh", "value") or node_stack.getProperty("cutting_mesh", "value"):
                    # Only "normal" meshes can have anti_overhang_meshes added to them
                    return

            # Create a pass for picking a world-space location from the mouse location
            active_camera = self._controller.getScene().getActiveCamera()
            picking_pass = PickingPass(active_camera.getViewportWidth(), active_camera.getViewportHeight())
            picking_pass.render()

            picked_normal_vertex = picking_pass.getPickedNormalVertex(event.x, event.y)

            # Add the anti_overhang_mesh cube at the picked location
            self._orientateNode(picked_node, picked_normal_vertex)

    def _orientateNode(self, picked_node: CuraSceneNode, normal_vertex: Vector):

        print(normal_vertex)

        CuraApplication.getInstance().getController().getScene().sceneChanged.emit(picked_node)

    def _onSelectionChanged(self):
        # When selection is passed from one object to another object, first the selection is cleared
        # and then it is set to the new object. We are only interested in the change from no selection
        # to a selection or vice-versa, not in a change from one object to another. A timer is used to
        # "merge" a possible clear/select action in a single frame
        if Selection.hasSelection() != self._had_selection:
            self._had_selection_timer.start()

    def _selectionChangeDelay(self):
        has_selection = Selection.hasSelection()
        if not has_selection and self._had_selection:
            self._skip_press = True
        else:
            self._skip_press = False

        self._had_selection = has_selection
