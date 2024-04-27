import bpy
from bpy.types import Panel
from bpy.app import version
from . import addon_updater_ops


class RePrimitivePanel(Panel):
    bl_idname = 'VIEW3D_PT_RePrimitive_Panel'
    bl_label = 'RePrimitive'
    bl_space_type = 'VIEW_3D'
    bl_context = "objectmode"
    bl_region_type = 'TOOLS' if version < (2, 80) else 'UI'
    bl_category = "RePrimitive"

    # if the panel is enabled show it
    @classmethod
    def poll(cls, context):
        return bpy.context.preferences.addons[__package__].preferences.show_reprimitive_panel

    def draw(self, context):
        layout = self.layout

        # Call to check for update in background.
        addon_updater_ops.check_for_update_background()

        # RePrimitive pie menu button
        row = layout.row()
        row.scale_y = 1.6
        row.operator("object.reprimitive_pie", text="RePrimitive Pie Menu")

        # RePrimitive button
        row = layout.row()
        row.scale_y = 1.6
        row.operator("object.reprimitive_auto", text="RePrimitive")

        # Call built-in function with draw code/checks.
        addon_updater_ops.update_notice_box_ui(self, context)

        return
