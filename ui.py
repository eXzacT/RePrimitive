import bpy
from bpy.types import Panel


class RePrimitivePanel(Panel):
    """
    Panel with 2 buttons, rotate and main reprimitive operator
    """

    bl_idname = 'VIEW3D_PT_RePrimitive_Panel'
    bl_label = 'RePrimitive'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"

    # if the object exists and the panel is enabled show it
    @classmethod
    def poll(cls, context):
        return context.object is not None and bpy.context.preferences.addons[__package__].preferences.show_reprimitive_panel

    def draw(self, context):
        layout = self.layout

        # Rotate button
        row = layout.row()
        row.scale_y = 1.6
        row.operator("object.fix_applied_rotation", text="Fix Rotation")

        # RePrimitive button
        row = layout.row()
        row.scale_y = 1.6
        row.operator("object.reprimitive", text="RePrimitive")

        return
