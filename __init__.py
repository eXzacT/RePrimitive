import bpy
from .operators import RePrimitive, RePrimitiveCircle, RePrimitiveCylinder, RePrimitiveTorus, RePrimitiveIcoSphere, RePrimitiveUVSphere, RePrimitiveCone, FixAppliedRotation, FixAppliedRotationAuto
from .ui import RePrimitivePanel
from .prefs import RePrimitivePrefs, DemoUpdaterPanel
from . import addon_updater_ops

bl_info = {
    "name": "RePrimitive",
    "author": "Damjan Anđelković <damjan.andelkovic1@gmail.com>",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "category": "Object",
    "description": "Manipulate primitives at any point in time without recreating them",
    # "wiki_url": "",
}

classes = (
    RePrimitivePrefs,
    RePrimitivePanel,
    RePrimitive,
    RePrimitiveCircle,
    RePrimitiveCone,
    RePrimitiveCylinder,
    RePrimitiveTorus,
    RePrimitiveIcoSphere,
    RePrimitiveUVSphere,
    FixAppliedRotation,
    FixAppliedRotationAuto,
    DemoUpdaterPanel
)

addon_keymaps = []


def menu_func(self, context):
    self.layout.operator(RePrimitive.bl_idname,
                         text=RePrimitive.bl_label)
    self.layout.operator(FixAppliedRotation.bl_idname,
                         text=FixAppliedRotation.bl_label)


def register():

    addon_updater_ops.register(bl_info)

    # register all classes
    for cls in classes:
        bpy.utils.register_class(cls)

    # adding keybinds
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    key_assign_list = [
        ("object.reprimitive", "A", "PRESS", True, True, False),
        ("object.fix_applied_rotation", "R", "PRESS", True, True, False),
    ]
    if kc:

        km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
        for (idname, key, event, ctrl, alt, shift) in key_assign_list:
            kmi = km.keymap_items.new(
                idname, key, event, ctrl=ctrl, alt=alt, shift=shift)
            addon_keymaps.append((km, kmi))

    # registering menu in Object->
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():

    addon_updater_ops.unregister()

    # removing all keybinds
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    # unregistering all classes
    for cls in classes:
        bpy.utils.unregister_class(cls)

    # unregistering menu from Object->
    bpy.types.VIEW3D_MT_object.remove(menu_func)
