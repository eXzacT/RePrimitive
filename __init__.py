import bpy
from bpy.app.handlers import persistent
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


def set_hidden_property(property_type: str, name: str, value: str | int | float | bool | Euler) -> None:
    """ Adds a hidden property to the active object """
    ob = bpy.context.object
    name = 'reprimitive_' + name

    match property_type:
        case 'str':
            prop = bpy.props.StringProperty(options={'HIDDEN'})
        case 'int':
            prop = bpy.props.IntProperty(options={'HIDDEN'})
        case 'float':
            prop = bpy.props.FloatProperty(options={'HIDDEN'})
        case 'bool':
            prop = bpy.props.BoolProperty(options={'HIDDEN'})
        case 'vector':
            prop = bpy.props.FloatVectorProperty(options={'HIDDEN'})

    setattr(bpy.types.Object, name, prop)
    setattr(ob, name, value)


@persistent
def on_primitive_object_create_or_edit(dummy) -> None:
    """ Hook into the object creation event and set hidden properties, only if the object was created with primitive operators """
    last_operator = bpy.context.active_operator
    ob = bpy.context.object
    if last_operator and ob:
        # The object doesn't have type yet, if it's a primitive set properties
        if not ob.get('reprimitive_ob_type'):
            match last_operator.name:
                case 'Add Circle' | 'Tweak Circle':
                    set_hidden_property('str', 'ob_type', 'circle')
                    set_hidden_property('int', 'vertices',
                                        last_operator.properties.vertices)
                    set_hidden_property('float', 'radius',
                                        last_operator.properties.radius)
                    set_hidden_property(
                        'str', 'fill', last_operator.properties.fill_type)
                case 'Add Cylinder' | 'Tweak Cylinder':
                    set_hidden_property('str', 'ob_type', 'cylinder')
                    set_hidden_property('int', 'vertices',
                                        last_operator.properties.vertices)
                    set_hidden_property('float', 'radius',
                                        last_operator.properties.radius)
                    set_hidden_property(
                        'float', 'depth', last_operator.properties.depth)
                    set_hidden_property(
                        'str', 'fill', last_operator.properties.end_fill_type)
                case 'Add Cone' | 'Tweak Cone':
                    set_hidden_property('str', 'ob_type', 'cone')
                    set_hidden_property('int', 'vertices',
                                        last_operator.properties.vertices)
                    set_hidden_property(
                        'float', 'depth', last_operator.properties.depth)
                    set_hidden_property('float', 'radius1',
                                        last_operator.properties.radius1)
                    set_hidden_property('float', 'radius2',
                                        last_operator.properties.radius2)
                    set_hidden_property(
                        'str', 'fill', last_operator.properties.end_fill_type)
                case 'Add Torus' | 'Tweak Torus':
                    set_hidden_property('str', 'ob_type', 'torus')
                    set_hidden_property(
                        'int', 'major_segments', last_operator.properties.major_segments)
                    set_hidden_property(
                        'int', 'minor_segments', last_operator.properties.minor_segments)
                    set_hidden_property(
                        'str', 'dimensions_mode', last_operator.properties.mode)
                    set_hidden_property(
                        'float', 'major_radius', last_operator.properties.major_radius)
                    set_hidden_property(
                        'float', 'minor_radius', last_operator.properties.minor_radius)
                    set_hidden_property(
                        'float', 'abso_major_rad', last_operator.properties.abso_major_rad)
                    set_hidden_property(
                        'float', 'abso_minor_rad', last_operator.properties.abso_minor_rad)
                case 'Add Ico Sphere' | 'Tweak Ico Sphere':
                    set_hidden_property('str', 'ob_type', 'icosphere')
                    set_hidden_property(
                        'int', 'subdivisions', last_operator.properties.subdivisions)
                    set_hidden_property('float', 'radius',
                                        last_operator.properties.radius)
                case 'Add UV Sphere' | 'Tweak UV Sphere':
                    set_hidden_property('str', 'ob_type', 'sphere')
                    set_hidden_property('int', 'segments',
                                        last_operator.properties.segments)
                    set_hidden_property(
                        'int', 'rings', last_operator.properties.ring_count)
                    set_hidden_property('float', 'radius',
                                        last_operator.properties.radius)
                case _:
                    return

        # It's a primitive object since it has the ob_type property and transform was applied
        elif last_operator.name == 'Apply Object Transform':
            if not get_object_property(ob, 'applying_transform'):
                set_hidden_property('bool', 'applying_transform', True)
                rot_after = ob.rotation_euler.copy()
                loc_after = ob.location.copy()
                scale_after = ob.scale.copy()

                # Were the location, rotation or scale applied?
                bpy.ops.ed.undo()
                ob = bpy.context.object
                applied_rot = rot_after != ob.rotation_euler
                applied_loc = loc_after != ob.location
                applied_scale = scale_after != ob.scale

                if applied_rot:
                    if (rot := get_object_property(ob, 'applied_rot')):
                        set_hidden_property('vector', 'applied_rot',
                                            (ob.rotation_euler.to_matrix() @ Euler(rot).to_matrix()).to_euler())
                    else:
                        set_hidden_property(
                            'vector', 'applied_rot', ob.rotation_euler.copy())

                if applied_scale:  # Recalculate radius and depth
                    match ob['reprimitive_ob_type']:
                        case 'circle' | 'sphere' | 'icosphere':
                            ob['reprimitive_radius'] = ob.scale[0] * \
                                ob['reprimitive_radius']
                        case 'cylinder':
                            ob['reprimitive_radius'] = ob.scale[0] * \
                                ob['reprimitive_radius']
                            ob['reprimitive_depth'] = ob.scale[2] * \
                                ob['reprimitive_depth']
                        case 'cone':
                            ob['reprimitive_radius1'] = ob.scale[0] * \
                                ob['reprimitive_radius1']
                            ob['reprimitive_radius2'] = ob.scale[0] * \
                                ob['reprimitive_radius2']
                            ob['reprimitive_depth'] = ob.scale[2] * \
                                ob['reprimitive_depth']
                        case 'torus':
                            ob['reprimitive_major_radius'] = ob.scale[0] * \
                                ob['reprimitive_major_radius']
                            ob['reprimitive_minor_radius'] = ob.scale[0] * \
                                ob['reprimitive_minor_radius']
                            ob['reprimitive_abso_major_rad'] = ob.scale[0] * \
                                ob['reprimitive_abso_major_rad']
                            ob['reprimitive_abso_minor_ad'] = ob.scale[0] * \
                                ob['reprimitive_abso_minor_ad']

                bpy.ops.object.transform_apply(
                    location=applied_loc, rotation=applied_rot, scale=applied_scale)


def register():
    # Register all classes
    addon_updater_ops.register(bl_info)
    for cls in classes:
        bpy.utils.register_class(cls)

    # Adding keybinds
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    key_assign_list = [
        ("object.reprimitive", "A", "PRESS", True, True, False),
    ]
    if kc:
        km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
        for (idname, key, event, ctrl, alt, shift) in key_assign_list:
            kmi = km.keymap_items.new(
                idname, key, event, ctrl=ctrl, alt=alt, shift=shift)
            addon_keymaps.append((km, kmi))

    # Registering the handler
    # bpy.app.handlers.depsgraph_update_post.append(on_primitive_object_create_or_edit)

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

    # Removing the handler
    bpy.app.handlers.depsgraph_update_post.remove(
        on_primitive_object_create_or_edit)

    # Registering menu from Object dropdown
    bpy.types.VIEW3D_MT_object.remove(menu_func)
