import bpy
import bmesh
import numpy as np
from math import cos, atan

from mathutils import Vector, Euler, Matrix
from bpy.app import version

# TODO all selected objects bpy.context.selected_objects

TOLERANCE = 1e-5


def floats_are_same(f1: float, f2: float) -> bool:
    """ Check if two floats are the same within a certain tolerance """
    return abs(f1 - f2) <= TOLERANCE


def vector_distance(point1: Vector, point2: Vector) -> float:
    return (point2 - point1).length


def vectors_are_same(point1: Vector, point2: Vector) -> bool:
    """ Check if two vectors are the same within a certain tolerance """
    return vector_distance(point1, point2) <= TOLERANCE


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


def get_object_property(ob: bpy.types.Object, key: str, default: str | int | float | bool = None) -> str | int | float | bool | Euler:
    return ob.get('reprimitive_'+key, default)


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


def reparent(child: bpy.types.Object, parent: bpy.types.Object) -> None:
    """ Add self as a parent to the child again and keep its transforms """
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


def replace_object(**kwargs) -> None:
    """ Replaces the currently selected object with a new one of the same type and properties """
    original_ob = bpy.context.object
    difference = kwargs.pop('difference')
    cut_heights = kwargs.pop('cut_heights', [])
    location = kwargs.pop('location') + difference

    if kwargs.get('align') == 'VIEW':
        # Remove rotation so the operator aligns the object to view and not to the rotation
        kwargs.pop('rotation')

    ob_type = kwargs.pop('ob_type')
    match ob_type:
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
    insert_loop_cuts(new_ob, cut_heights)

    copy_data(original_ob, new_ob, difference)
    delete_and_copy_name(original_ob, new_ob)


def delete_and_copy_name(original_ob: bpy.types.Object, new_ob: bpy.types.Object) -> None:
    name = original_ob.name
    mesh_name = original_ob.data.name
    bpy.data.meshes.remove(bpy.data.meshes[mesh_name])
    new_ob.name = name
    new_ob.data.name = mesh_name


def copy_data(original_ob: bpy.types.Object, new_ob: bpy.types.Object, difference: Vector) -> None:
    # As of 4.1 and higher auto_smooth was removed
    if version >= (4, 1, 0):
        if original_ob.data.polygons and original_ob.data.polygons[0].use_smooth:
            bpy.ops.object.shade_smooth_by_angle()
    else:
        if original_ob.data.use_auto_smooth:
            bpy.ops.object.shade_smooth(
                use_auto_smooth=True, auto_smooth_angle=original_ob.data.auto_smooth_angle)
        else:  # Didn't have autosmooth but polygons are still smooth, use shade smooth, not auto_smooth
            if original_ob.data.polygons and original_ob.data.polygons[0].use_smooth:
                bpy.ops.object.shade_smooth()

    parent = original_ob.parent
    if parent:
        reparent(new_ob, parent)

    # Check if any objects in the scene have modifiers that point to the original object, point them to new one instead
    for ob in bpy.context.scene.objects:
        if ob.type == 'MESH':
            for mod in ob.modifiers:
                if hasattr(mod, 'object') and mod.object == original_ob:
                    mod.object = new_ob

    for child in original_ob.children:
        reparent(child, new_ob)

    # Make the original object active then copy all the modifiers and materials to the new object
    bpy.context.view_layer.objects.active = original_ob
    bpy.ops.object.make_links_data(type='MODIFIERS')
    bpy.ops.object.make_links_data(type='MATERIAL')

    select_object(new_ob)

    # Move the new object in every collection the original object is in
    for coll in original_ob.users_collection:
        if new_ob.name not in coll.objects:
            coll.objects.link(new_ob)
    # Remove the new object from every collection the original object wasn't in
    for coll in new_ob.users_collection:
        if original_ob.name not in coll.objects:
            coll.objects.unlink(new_ob)

    set_origin(new_ob.location - difference)
    new_ob.scale = original_ob.scale.copy()
    new_ob.display_type = original_ob.display_type

    # Copy all the custom properties but skip reprimitive props because we already covered that part of the code in the handler(on_primitive_object_create_or_edit)
    for prop in original_ob.keys():
        if prop.startswith('reprimitive'):
            continue
        new_ob[prop] = original_ob[prop]


# def fill_face(ob: bpy.types.Object) -> int:
#     """ Fills in the missing faces of an object, returns how many faces we filled """

#     original_mode = bpy.context.object.mode
#     faces = len(ob.data.polygons)
    # bm = bmesh.new()
#     bm.from_mesh(ob.data)

#     # Fill holes and update the mesh then return to original mode
#     bpy.ops.object.mode_set(mode='EDIT')
#     bpy.ops.mesh.select_all(action='SELECT')
#     bpy.ops.mesh.fill_holes(sides=0)
#     bpy.ops.mesh.select_all(action='DESELECT')
#     ob.update_from_editmode()
#     bpy.ops.object.mode_set(mode=original_mode)

#     return len(ob.data.polygons) - faces


# def delete_filled(ob: bpy.types.Object, difference: int) -> None:
#     """ Deletes the filled in faces, sharp tipped cone and circle have 1 filled, cylinder and cylindrical cone have 2 """

#     if not difference:
#         return

#     select_object(ob)

#     # Store original mode, enter edit mode and delete select filled faces
#     original_mode = bpy.context.object.mode
#     bpy.ops.object.mode_set(mode='EDIT')
#     bm = bmesh.from_edit_mesh(ob.data)
#     bm.faces.ensure_lookup_table()
#     bm.faces[-1].select_set(True)
#     if difference == 2:
#         bm.faces[-2].select_set(True)

#     # Delete them and restore original mode
#     bpy.ops.mesh.delete(type='ONLY_FACE')
#     bpy.ops.object.mode_set(mode=original_mode)


def calculate_object_location_and_difference(ob: bpy.types.Object) -> tuple[Vector, Vector]:
    """ Returns object origin and how far it's from it """
    selected = bpy.context.object

    origin = ob.matrix_world.translation.copy()
    select_object(ob)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
    true_loc = ob.location.copy()
    set_origin(origin)

    bpy.ops.object.select_all(action='DESELECT')
    select_object(selected)

    return origin, true_loc - origin


def calculate_object_location_and_difference_no_origin_to_geometry(ob: bpy.types.Object, **kwargs) -> tuple[Vector, Vector]:
    """ Because origin to geometry doesn't work for cones or objects with loop cuts we have to spawn another object that looks exactly the same and compare the distance between the verts """

    cut_heights = kwargs.pop('cut_heights', [])
    ob_type = kwargs.pop('ob_type')

    # Save the scale and clear it, we need the scale to be 1,1,1 to get the correct distance between the objects
    saved_scale = ob.scale.copy()
    bpy.ops.object.scale_clear(clear_delta=False)
    original_origin = ob.matrix_world.translation.copy()

    # Add the exact same object and get the distances between 2 of their verts
    match ob_type:
        case 'cone':
            bpy.ops.mesh.primitive_cone_add(location=original_origin, **kwargs)
        case 'cylinder':
            bpy.ops.mesh.primitive_cylinder_add(
                location=original_origin, **kwargs)

    twin_ob = bpy.context.active_object
    insert_loop_cuts(twin_ob, cut_heights)

    difference = (ob.matrix_world @ ob.data.vertices[0].co) - (
        twin_ob.matrix_world @ twin_ob.data.vertices[0].co)

    # Delete twin object, restore scale and reselect the original object
    bpy.data.meshes.remove(bpy.data.meshes[twin_ob.data.name])
    ob.scale = saved_scale
    select_object(ob)

    return original_origin, difference


def calculate_object_rotation(original_ob: bpy.types.Object, **kwargs) -> Euler:
    ob_type = kwargs.pop('ob_type')
    cut_heights = kwargs.pop('cut_heights', [])
    sharp_tipped_cone = kwargs.pop('sharp_tipped', False)

    match ob_type:
        case 'circle':
            bpy.ops.mesh.primitive_circle_add(**kwargs)
        case 'cone':
            bpy.ops.mesh.primitive_cone_add(**kwargs)
        case 'cylinder':
            bpy.ops.mesh.primitive_cylinder_add(**kwargs)
        case 'icosphere':
            bpy.ops.mesh.primitive_ico_sphere_add(**kwargs)
        case 'torus':
            bpy.ops.mesh.primitive_torus_add(**kwargs)
        case 'sphere':
            bpy.ops.mesh.primitive_uv_sphere_add(**kwargs)

    new_ob = bpy.context.active_object
    insert_loop_cuts(new_ob, cut_heights)

    # I need to find a universal way to get the verts of the first face of any object if it's even possible
    # By getting same verts of both objects we can calculate how the twin object should be rotated to match the original
    if ob_type == 'sphere':
        # Sphere has random face order but verts are always in the same order
        # For example, faces 1 in object 1 and face 2 in object 2 are faces with same verts (1,2,3,4)
        face_verts_orig, indices = get_first_face_verts_and_their_indices(
            original_ob)
        face_verts_new = [new_ob.matrix_world @
                          new_ob.data.vertices[idx].co for idx in indices]
    elif sharp_tipped_cone:  # Sharp tipped cone has random vert order when it has loop cuts
        face_verts_orig, vert_count = get_cone_face(original_ob)
        face_verts_new = get_cone_face(new_ob, vert_count)
    else:  # Works for every other object
        face_verts_orig, _ = get_first_face_verts_and_their_indices(
            original_ob)
        face_verts_new, _ = get_first_face_verts_and_their_indices(new_ob)

    # Delete the twin object and reselect the original one
    bpy.data.meshes.remove(bpy.data.meshes[new_ob.data.name])
    select_object(original_ob)
    return calculate_matching_rotation(face_verts_orig, face_verts_new)


def get_first_face_verts_and_their_indices(ob: bpy.types.Object) -> tuple[list[Vector], list[int]]:
    """ Gets the world location and indices of all vertices that make up a first face """
    if not ob.data.polygons:  # Circle is the only object potentially without a face face, just get verts
        return [ob.matrix_world @ v.co for v in ob.data.vertices], [v.index for v in ob.data.vertices]

    indices = ob.data.polygons[0].vertices
    return [ob.matrix_world @ ob.data.vertices[idx].co for idx in indices], indices


def get_cone_face(ob: bpy.types.Object, face_vert_count: int = None) -> tuple[list[Vector], list[int]]:
    """ Gets the world location and indices of all vertices that make up a first face """
    if not ob.data.polygons:  # Circle is the only object potentially without a face face, just get verts
        return [ob.matrix_world @ v.co for v in ob.data.vertices], [v.index for v in ob.data.vertices]

    bm = bmesh.new()
    bm = bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()

    vert1 = bm.verts[0]
    vert2 = bm.verts[1]

    if face_vert_count:
        # Get the faces that both vertices are a part of
        faces = set(vert1.link_faces).intersection(vert2.link_faces)
        for face in faces:
            if len(face.verts) == face_vert_count:
                return [ob.matrix_world @ v.co for v in face.verts]

    # Get the first face that both vertices are a part of, also get total verts of that face
    # We will use that vert count to get the same face from the other object because the order of faces might be different
    face = list(set(vert1.link_faces).intersection(vert2.link_faces))[0]
    total_verts = len(face.verts)

    return [ob.matrix_world @ v.co for v in face.verts], total_verts


def calculate_matching_rotation(face_verts_orig: list[Vector], face_verts_new: list[Vector]) -> Euler:
    """ Calculate the optimal rotation matrix to align two sets of vertices. """

    pts_orig = np.array([v.to_tuple() for v in face_verts_orig])
    pts_new = np.array([v.to_tuple() for v in face_verts_new])

    # Center the points around the origin
    pts_orig -= pts_orig.mean(axis=0)
    pts_new -= pts_new.mean(axis=0)

    # Compute covariance matrix
    H = np.dot(pts_new.T, pts_orig)

    # Compute singular value decomposition
    U, _, Vt = np.linalg.svd(H)

    # Compute optimal rotation matrix
    R = np.dot(Vt.T, U.T)

    # Ensure a proper rotation matrix (no reflection)
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = np.dot(Vt.T, U.T)

    return Matrix(R.tolist()).to_euler()


def calculate_cylinder_properties(ob: bpy.types.Object) -> tuple[int, list[float], float, float,  str]:
    """ Calculates number of verts, loop cut height percentages, radius, depth and fill type """

    total_verts = len(ob.data.vertices)
    total_faces = len(ob.data.polygons)
    deselect_all_verts()

    # Selecting entire ring from 2 verts doesn't work in these 2 cases, so just select the verts manually
    if total_verts == 6:
        select_verts(ob, [0, 2, 4])
    elif total_verts == 8 and total_faces:
        select_verts(ob, [0, 2, 4, 6])
    else:
        select_ring_from_verts(ob, [2, 4])

    selected = get_selected_verts(ob)
    radius = calculate_radius(selected)
    verts = len(selected)
    loop_cuts = total_verts//verts - 2  # Don't count top and bottom rings hence -2

    # Verts forming an edge from bottom to top are always subsequent
    depth = vector_distance(ob.data.vertices[0].co, ob.data.vertices[1].co)

    if verts * (loop_cuts+2) == total_verts-2:  # 2 extra verts means it's a trifan cap
        fill_type = 'TRIFAN'
    # If the cylinder has 32 side faces, adding 2 loop cuts will make every side have 3 times as much faces
    elif verts * (loop_cuts+1) == total_faces:
        fill_type = 'NOTHING'
    else:
        fill_type = 'NGON'

    return verts, calculate_cylinder_height_percentages(ob, depth), radius, depth,  fill_type


def calculate_cone_properties(ob: bpy.types.Object) -> tuple[bool, int, list[float], float, float, float, str]:
    """ Calculates whether it's a sharp tipped cone, number of verts, loop cut height percentages, radius, depth, cap type and fill type """

    total_verts = len(ob.data.vertices)
    total_faces = len(ob.data.polygons)
    deselect_all_verts()

    if is_sharp_tipped(ob):
        if total_verts == 4:  # Three sided pyramid with ngon or nothing fill
            select_verts(ob, [0, 1, 2])
        elif total_verts == 5 and total_faces == 4:  # Four sided pyramid with ngon or nothing fill
            select_verts(ob, [0, 1, 2, 3])
        else:
            # 0th vert is potentially a middle vert so skip it
            select_ring_from_verts(ob, [1, 2])

        # It has to be a bottom face since the bottom isn't allowed to have radius 0 in blender when creating a cone
        radius_top = 0
        selected_bottom = get_selected_verts(ob)
        verts = len(selected_bottom)
        center_bottom = calculate_center(selected_bottom)
        radius_bottom = calculate_radius(selected_bottom, center_bottom)

        loop_cuts = total_verts//verts - 1  # Don't count the bottom ring hence -1
        # Example 32 verts 0 loop cuts and trifan, that's 34 total
        if verts * (loop_cuts+1) == total_verts-2:
            fill_type = 'TRIFAN'
        elif verts * (loop_cuts+1) == total_faces:
            fill_type = 'NOTHING'
        else:
            fill_type = 'NGON'

        # The vert at the top has index that follows the last vert in the bottom ring
        top_index = verts + 1 if fill_type == 'TRIFAN' else verts
        depth = vector_distance(center_bottom, ob.data.vertices[top_index].co)
        return True, verts, calculate_sharp_cone_cut_height_percentages(ob, radius_bottom, depth), radius_bottom, radius_top, depth,  fill_type

    if total_verts == 6:
        select_verts(ob, [0, 2, 4])
    elif total_verts == 8 and total_faces == 6:
        select_verts(ob, [0, 2, 4, 6])
    else:  # Select 2 neighbouring verts on the base and use them to select the entire ring
        select_ring_from_verts(ob, [2, 4])
    selected_bottom = get_selected_verts(ob)
    center_bottom = calculate_center(selected_bottom)
    radius_bottom = calculate_radius(selected_bottom, center_bottom)

    # Now do the same but for top verts
    if total_verts == 6:
        select_verts(ob, [1, 3, 5])
    elif total_verts == 8 and total_faces == 6:
        select_verts(ob, [1, 3, 5, 7])
    else:  # Select 2 neighbouring verts on the base and use them to select the entire ring
        select_ring_from_verts(ob, [3, 5])
    selected_top = get_selected_verts(ob)
    center_top = calculate_center(selected_top)
    radius_top = calculate_radius(selected_top, center_top)

    depth = vector_distance(center_bottom, center_top)
    # Any of them is fine since both top and bottom have the same amount of verts
    verts = len(selected_top)
    loop_cuts = total_verts//verts - 2  # Don't count top and bottom rings hence -2

    if verts * (loop_cuts+2) == total_verts-2:  # 2 extra verts means it's a trifan cap
        fill_type = 'TRIFAN'
    # If the cylindrical cone has 32 side faces, adding 2 loop cuts will make every side have 3 times as much faces
    elif verts * (loop_cuts+1) == total_faces:
        fill_type = 'NOTHING'
    else:
        fill_type = 'NGON'

    return False, verts, calculate_cylindrical_cone_cut_height_percentages(ob, radius_bottom, radius_top, depth), radius_bottom, radius_top, depth, fill_type


def is_sharp_tipped(ob: bpy.types.Object) -> bool:
    """ Check if a cone is sharp tipped or not by checking if all 3 verts(3,4,5) are on the same bottom ring
        The reason why those 3 specifically is because first 2 verts are potentially middle verts in a cap
        This works because Blender always has the same order of verts in primitives """

    if len(ob.data.vertices) == 4:  # Edge case
        return True

    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()

    # Get the third, fourth and fifth vertices, because 0th and 1st are potentially middle cap verts
    vert3 = bm.verts[2]
    vert4 = bm.verts[3]
    vert5 = bm.verts[4]

    # The way blender orders verts in a cylindrical cone/cylinder is top vert, bottom vert, top vert, bottom vert
    # So if the 3rd vert is connected to the 4th and the 4th is connected to the 5th, it's a sharp tipped cone
    return any(e.other_vert(vert3) == vert4 for e in vert3.link_edges) and any(e.other_vert(vert4) == vert5 for e in vert4.link_edges)


def calculate_center(verts: list[Vector]) -> Vector:
    return sum(verts, Vector()) / len(verts)


def calculate_radius(input_data: bpy.types.Object | list[Vector], center: Vector = None) -> float:
    """ Calculate the radius by calculating the center first and then finding the distance to any of the ring verts
        If it's an object use all the verts
        Optional center parameter so we don't have to calculate it twice """

    if isinstance(input_data, list):
        ring_verts = input_data
        if not center:
            center = calculate_center(ring_verts)
        # All of them are ring verts so doesn't matter
        edge_vert = ring_verts[0]
    else:
        ob = input_data
        if not center:
            center = calculate_center([v.co for v in ob.data.vertices])
        # 2nd vert is always on the ring, 0th and 1st are potentially middle verts
        edge_vert = ob.data.vertices[2].co

    return round(vector_distance(center, edge_vert), 5)


def deselect_all_verts() -> None:
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.editmode_toggle()


def get_selected_verts(ob: bpy.types.Object) -> list[Vector]:
    return [v.co for v in ob.data.vertices if v.select]


def select_verts(ob: bpy.types.Object, indices: list[int]) -> None:
    deselect_all_verts()
    for idx in indices:
        ob.data.vertices[idx].select = True


def select_entire_ring() -> None:
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')
    bpy.ops.mesh.loop_multi_select(ring=False)
    bpy.ops.object.editmode_toggle()


def select_ring_from_verts(ob: bpy.types.Object, vert_indices: list[int]) -> None:
    select_verts(ob, vert_indices)
    select_entire_ring()


def calculate_sphere_segments(ob: bpy.types.Object) -> int:
    return len(ob.data.polygons) - (len(ob.data.vertices)-2)


def get_linked_objects(ob: bpy.types.Object) -> list[bpy.types.Object]:
    return [obj for obj in bpy.context.scene.objects if obj.data == ob.data and obj != ob]


def select_object(ob: bpy.types.Object) -> None:
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def create_linked_ob_at_location(ob: bpy.types.Object, location):
    bpy.ops.object.duplicate(linked=True)

    duplicate = bpy.context.object
    duplicate.location = location
    duplicate.select_set(False)

    select_object(ob)


def draw_buttons(box: bpy.types.UILayout, operator: str) -> None:
    row = box.row()
    split = row.split(factor=0.33)
    split.label(text="")
    split.operator(operator, text="4").vertices = 4
    split.label(text="")

    row = box.row()
    row.operator(operator, text="6").vertices = 6
    row.operator(operator, text="8").vertices = 8
    row.operator(operator, text="12").vertices = 12

    row = box.row()
    row.operator(operator, text="16").vertices = 16
    row.operator(operator, text="24").vertices = 24
    row.operator(operator, text="32").vertices = 32

    row = box.row()
    row.operator(operator, text="64").vertices = 64
    row.operator(operator, text="96").vertices = 96
    row.operator(operator, text="128").vertices = 128


def all_faces_have_x_verts(ob: bpy.types.Object, verts: int) -> bool:
    return all(len(f.vertices) == verts for f in ob.data.polygons)


def are_verts_part_of_same_face(bm, indices: list[int]) -> bool:
    first_vert_faces = set(bm.verts[indices[0]].link_faces)
    return all(any(face in first_vert_faces for face in bm.verts[idx].link_faces) for idx in indices[1:])


def is_cone_or_circle(ob: bpy.types.Object) -> str:
    """ Checks whether an object is a cone or a circle based on the normals of all its faces, circle needs to have a trifan cap"""
    first_normal = ob.data.polygons[0].normal
    return 'circle' if all(vectors_are_same(f.normal, first_normal) for f in ob.data.polygons) else 'cone'


def is_sphere_or_cone(ob: bpy.types.Object) -> str:
    """ Checks whether an object is a sphere or a cone based on the normals of all its faces, sphere needs to have a trifan cap"""
    center = calculate_center([v.co for v in ob.data.vertices])
    first_dist = vector_distance(ob.data.vertices[0].co, center)
    return 'sphere' if all(floats_are_same(vector_distance(v.co, center), first_dist) for v in ob.data.vertices) else 'cone'


def is_cone_or_cylinder(ob: bpy.types.Object) -> str:
    """ Checks whether an object is a cone or a cylinder """
    select_ring_from_verts(ob, [2, 4])
    bottom_radius = calculate_radius(get_selected_verts(ob))
    select_ring_from_verts(ob, [3, 5])
    top_radius = calculate_radius(get_selected_verts(ob))

    return 'cylinder' if bottom_radius == top_radius else 'cone'


def find_ob_type(ob: bpy.types.Object) -> str:
    # Spaghetti, can I improve this?
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()

    verts_edge_count = {}
    for v in bm.verts:
        verts_edge_count[len(v.link_edges)] = verts_edge_count.get(
            len(v.link_edges), 0)+1
    have_common_face = are_verts_part_of_same_face(bm, [0, 1])

    if len(verts_edge_count) == 3:  # cone with loop cuts
        return 'cone'

    if len(verts_edge_count) == 2:
        if verts_edge_count.get(5) == 12:
            return 'icosphere'
        for edge_count, verts in verts_edge_count.items():
            if edge_count != 4:
                if verts == 2:
                    if all_faces_have_x_verts(ob, 3):  # TRIFAN cone
                        return 'cone'
                    elif have_common_face:
                        return is_sphere_or_cone(ob)
                    else:  # TRIFAN cylinder or TRIFAN cylindrical cone
                        return is_cone_or_cylinder(ob)
                # ngon/no fill cylinder/cone with loop cuts
                if verts_edge_count.get(4, False):
                    return is_cone_or_cylinder(ob)
        # Trifan circle or a ngon/nothing sharp tipped cone
        if any([key == 3 for key in verts_edge_count.keys()]):
            return is_cone_or_circle(ob)

    if len(verts_edge_count) == 1:
        edges = list(verts_edge_count.keys())[0]
        if edges == 5:  # 1 subdivision icosphere
            return 'icosphere'
        # Every vert has 4 edges and every polygon is a quad
        if edges == 4:
            if all_faces_have_x_verts(ob, 4):
                return 'torus'
            elif have_common_face:
                return is_sphere_or_cone(ob)
            else:  # TRIFAN cylinder or cone with 4 sides
                return is_cone_or_cylinder(ob)
        if edges == 3:
            if len(ob.data.vertices) == 4:  # TRIFAN circle with 3 sides or a cylinder with 3 sides
                return is_cone_or_circle(ob)
            return is_cone_or_cylinder(ob)  # No fill or ngon cylinder/cone
        if edges == 2:  # No fill or ngon circle
            return 'circle'

    return 'unknown'


def calculate_cylindrical_cone_cut_height_percentages(ob: bpy.types.Object, bottom_radius: float, top_radius: float, height: float) -> list[float]:
    """ Calculate the height percentages of the loop cuts by selecting 1 entire side, there's going to be 2 verts minimum(bottom and top), we will ignore those """

    deselect_all_verts()
    # Select top and bottom vert then all the verts between them
    ob.data.vertices[0].select = True
    ob.data.vertices[1].select = True
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.shortest_path_select(edge_mode='SELECT')
    bpy.ops.object.mode_set(mode='OBJECT')

    angle = atan((bottom_radius - top_radius) / height)

    return sorted([(vector_distance(v.co, ob.data.vertices[0].co) * cos(angle)) / height for v in ob.data.vertices if v.select])[1:-1]


def calculate_sharp_cone_cut_height_percentages(ob: bpy.types.Object, radius: float, height: float) -> list[float]:
    """ Calculate the height percentages of the loop cuts by selecting 1 entire side, there's going to be 2 verts minimum(bottom and top), we will ignore those """

    deselect_all_verts()
    # Select side edge and extend to select the entire side
    ob.data.edges[1].select = True
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.loop_multi_select(ring=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    # By multiplying the distance between verts with the cosine of the angle we get the actual height,
    # and by dividing with the current height we get the height percentage of that loop cut
    angle = atan(radius/height)

    return sorted([(vector_distance(v.co, ob.data.vertices[0].co) * cos(angle)) / height for v in ob.data.vertices if v.select])[1:-1]


def calculate_cylinder_height_percentages(ob: bpy.types.Object, height: float) -> list[float]:
    """ Calculate the height percentages of the loop cuts by selecting 1 entire side, there's going to be 2 verts minimum(bottom and top), we will ignore those"""

    deselect_all_verts()
    # Select side edge and extend to select the entire side
    ob.data.edges[2].select = True
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.loop_multi_select(ring=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    return sorted([vector_distance(v.co, ob.data.vertices[0].co)/height for v in ob.data.vertices if v.select])[1:-1]


def insert_loop_cuts(ob: bpy.types.Object, height_percentages: list[float]) -> None:
    """ Given a list of height percentages insert loop cuts at those heights """
    if not height_percentages:
        return

    bpy.ops.object.select_all(action='DESELECT')
    select_object(ob)
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(ob.data)

    # Calculate actual cut Z heights based on the percentages
    height = ob.dimensions.z
    bottom_z = -height/2
    cut_positions = [bottom_z + p * height for p in height_percentages]

    for height in cut_positions:
        plane_co = (0, 0, height)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], dist=0.01, plane_co=plane_co,
                               plane_no=(0, 0, 1), use_snap_center=False, clear_outer=False, clear_inner=False)

    bpy.ops.object.mode_set(mode='OBJECT')
