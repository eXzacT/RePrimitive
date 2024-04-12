import bpy

from bpy.types import Object
from mathutils import Vector, Euler
from bpy.app import version

# TODO Reapply loop cuts
# TODO Scale bug


def get_object_property(ob: Object, key: str) -> str | int | float | bool | Euler:
    return ob.get('reprimitive_'+key)


def get_ob_original_location_and_difference(ob: Object, **kwargs) -> Vector:
    """ Gets the object true location by creating another object that looks exactly the same, then compares the distance between any vert """

    original_origin = ob.matrix_world.translation.copy()
    match get_object_property(ob, 'ob_type'):
        case 'circle':
            bpy.ops.mesh.primitive_circle_add(
                location=original_origin, **kwargs)
        case 'cone':
            bpy.ops.mesh.primitive_cone_add(location=original_origin, **kwargs)
        case 'cylinder':
            bpy.ops.mesh.primitive_cylinder_add(
                location=original_origin, **kwargs)
        case 'icosphere':
            bpy.ops.mesh.primitive_ico_sphere_add(
                location=original_origin, **kwargs)
        case 'torus':
            bpy.ops.mesh.primitive_torus_add(
                location=original_origin, **kwargs)
        case 'sphere':
            bpy.ops.mesh.primitive_uv_sphere_add(
                location=original_origin, **kwargs)

    temp_ob = bpy.context.active_object
    # Rescale the new object so the distances are correct
    temp_ob.scale = ob.scale.copy()
    difference = (ob.matrix_world @ ob.data.vertices[0].co) - (
        temp_ob.matrix_world @ temp_ob.data.vertices[0].co)
    bpy.data.meshes.remove(bpy.data.meshes[temp_ob.data.name])

    # Reselect the original object
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob

    return original_origin, difference


def get_object_rotation(ob: Object) -> Euler:
    """ Gets the object true rotation in case it was applied by multiplying the object rotation with the applied rotation, otherwise just gets the current rotation """
    if (rot := get_object_property(ob, 'applied_rot')):
        return (ob.rotation_euler.to_matrix() @ Euler(rot).to_matrix()).to_euler()
    return ob.rotation_euler.copy()


def set_origin(origin: Vector) -> None:
    """ Sets the origin of a currently selected object to a given origin by moving the 3D cursor to it and setting the origin to cursor """
    cursor_loc = Vector(bpy.context.scene.cursor.location)
    bpy.context.scene.cursor.location = origin
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
    bpy.context.scene.cursor.location = cursor_loc


def save_and_unparent_children(children: list[bpy.types.Object]) -> list[bpy.types.Object]:
    """ Remove self as a parent from the children and keep their transforms """
    for child in children:
        matrix_world = child.matrix_world
        child.parent = None
        child.matrix_world = matrix_world

    return children


def reparent(child: Object, parent: Object) -> None:
    """ Add self as a parent to the child again and keep its transforms """
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


def copy_modifiers_and_delete_original(original_ob: Object, new_ob: Object, difference: Vector) -> None:
    # Copyover some properties from the original object
    new_ob.display_type = original_ob.display_type
    name = original_ob.name
    mesh_name = original_ob.data.name

    # As of 4.1 and higher auto_smooth was removed
    if version >= (4, 1, 0):
        if original_ob.data.polygons and original_ob.data.polygons[0].use_smooth:
            bpy.ops.object.shade_smooth_by_angle()
    else:
        if original_ob.data.use_auto_smooth:
            bpy.ops.object.shade_smooth(
                use_auto_smooth=True, auto_smooth_angle=original_ob.data.auto_smooth_angle)
        else:  # Didn't have autosmooth but polygons are still smooth, use shade smooth without default variables
            if original_ob.data.polygons and original_ob.data.polygons[0].use_smooth:
                bpy.ops.object.shade_smooth()

    parent = original_ob.parent
    if parent:
        reparent(new_ob, parent)

        # If the parent has some modifiers that point to the original object, point them to new one instead
        for mod in parent.modifiers:
            if hasattr(mod, 'object') and mod.object == original_ob:
                mod.object = new_ob

    for child in original_ob.children:
        reparent(child, new_ob)

    # Make the original object active then copy all the modifiers and materials to the new object
    bpy.context.view_layer.objects.active = original_ob
    bpy.ops.object.make_links_data(type='MODIFIERS')
    bpy.ops.object.make_links_data(type='MATERIAL')

    # Select the newly created object
    new_ob.select_set(True)
    bpy.context.view_layer.objects.active = new_ob

    # Move the new object in every collection the original object is in
    for coll in original_ob.users_collection:
        if new_ob.name not in coll.objects:
            coll.objects.link(new_ob)
    # Remove the new object from every collection the original object wasn't in
    for coll in new_ob.users_collection:
        if original_ob.name not in coll.objects:
            coll.objects.unlink(new_ob)

    set_origin(new_ob.location-difference)
    new_ob.scale = original_ob.scale.copy()

    # Copyover all the custom properties but skip reprimitive props because we already covered that part of the code in the handler(on_primitive_object_create_or_edit)
    for prop in original_ob.keys():
        if prop.startswith('reprimitive'):
            continue
        new_ob[prop] = original_ob[prop]

    # Delete the original object mesh, this will also delete the object, then copy the name
    bpy.data.meshes.remove(bpy.data.meshes[mesh_name])
    new_ob.name = name
    new_ob.data.name = mesh_name


def replace_object(**kwargs) -> None:
    """ Replaces the currently selected object with a new one of the same type and properties """
    original_ob = bpy.context.active_object
    difference = kwargs.pop('difference')
    location = kwargs.pop('location') + difference

    if kwargs.get('align') == 'VIEW':
        # Remove rotation so the operator aligns the object to view and not to the rotation
        kwargs.pop('rotation')

    match get_object_property(original_ob, 'ob_type'):
        case 'circle':
            bpy.ops.mesh.primitive_circle_add(location=location, **kwargs)
        case 'cone':
            bpy.ops.mesh.primitive_cone_add(location=location, **kwargs)
        case 'cylinder':
            bpy.ops.mesh.primitive_cylinder_add(location=location, **kwargs)
        case 'icosphere':
            bpy.ops.mesh.primitive_ico_sphere_add(location=location, **kwargs)
        case 'torus':
            bpy.ops.mesh.primitive_torus_add(location=location, **kwargs)
        case 'sphere':
            bpy.ops.mesh.primitive_uv_sphere_add(location=location, **kwargs)

    new_ob = bpy.context.active_object
    copy_modifiers_and_delete_original(original_ob, new_ob, difference)
