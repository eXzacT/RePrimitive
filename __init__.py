import bpy
from .operators import *
from .ui import RePrimitivePanel
from .prefs import RePrimitivePrefs
from . import addon_updater_ops

bl_info = {
    "name": "RePrimitive",
    "author": "Damjan Anđelković <damjan.andelkovic1@gmail.com>",
    "version": (3, 0, 0),
    "blender": (4, 1, 0),
    "category": "Object",
    "description": "Manipulate primitives at any point in time without recreating them from scratch manually.",
}

classes = (
    RePrimitive,
    RePrimitiveAuto,
    RePrimitivePieMenu,
    RePrimitivePrefs,
    RePrimitivePanel,
    RePrimitiveCircle,
    RePrimitiveCone,
    RePrimitiveCylinder,
    RePrimitiveTorus,
    RePrimitiveIcoSphere,
    RePrimitiveUVSphere,
)

addon_keymaps = []


def menu_func(self, context):
    self.layout.operator(RePrimitive.bl_idname, text=RePrimitive.bl_label)


def register():
    # Register all classes
    addon_updater_ops.register(bl_info)
    for cls in classes:
        bpy.utils.register_class(cls)

    # Adding keybinds
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:

        km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
        kmi = km.keymap_items.new(
            "object.reprimitive_pie", 'A', 'PRESS', ctrl=True, alt=True)
        addon_keymaps.append((km, kmi))
        kmi = km.keymap_items.new("object.reprimitive_auto", 'Q', 'PRESS')
        addon_keymaps.append((km, kmi))

    # Registering menu in Object dropdown menu
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    # Removing all keybinds
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    # Unregistering all classes
    addon_updater_ops.unregister()
    for cls in classes:
        bpy.utils.unregister_class(cls)

    # Removing menu from Object dropdown
    bpy.types.VIEW3D_MT_object.remove(menu_func)
