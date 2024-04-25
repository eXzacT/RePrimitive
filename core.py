import bpy
import bmesh
import numpy as np

from bpy.types import Object
from mathutils import Vector, Euler, Matrix
from bpy.app import version

# TODO Reapply loop cuts
# TODO Linked objects
# TODO Cylinder location
# TODO Cone calc properties


TOLERANCE = 1e-5
CUBE_NAME = "cube_to_delete_123#"


# def floats_are_same(f1: float, f2: float) -> bool:
#     """ Check if two floats are the same within a certain tolerance """
#     return abs(f1 - f2) <= TOLERANCE


def vector_distance(point1: Vector, point2: Vector) -> float:
    return (point2 - point1).length


def vectors_are_same(point1: Vector, point2: Vector) -> bool:
    """ Check if two vectors are the same within a certain tolerance """
    return vector_distance(point1, point2) <= TOLERANCE


def get_object_property(ob: Object, key: str, default: str | int | float | bool = None) -> str | int | float | bool | Euler:
    return ob.get('reprimitive_'+key, default)


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

    set_origin(new_ob.location - difference)
    new_ob.scale = original_ob.scale.copy()
    new_ob.display_type = original_ob.display_type

    # Copy all the custom properties but skip reprimitive props because we already covered that part of the code in the handler(on_primitive_object_create_or_edit)
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
    copy_modifiers_and_delete_original(original_ob, new_ob, difference)


def fill_face(ob: Object) -> int:
    """ Fills in the missing faces of an object, returns how many faces we filled """

    original_mode = bpy.context.object.mode
    faces = len(ob.data.polygons)
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.new()
    bm.from_mesh(ob.data)

    # Fill holes and update the mesh then return to original mode
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.fill_holes(sides=0)
    bpy.ops.mesh.select_all(action='DESELECT')
    ob.update_from_editmode()
    bpy.ops.object.mode_set(mode=original_mode)

    return len(ob.data.polygons) - faces


def delete_filled(ob: Object, difference: int) -> None:
    """ Deletes the filled in faces, sharp tipped cone and circle have 1 filled, cylinder and cylindrical cone have 2 """

    if not difference:
        return

    # Make the object active
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)

    # Store original mode, enter edit mode and delete select filled faces
    original_mode = bpy.context.object.mode
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    bm.faces[-1].select_set(True)
    if difference == 2:
        bm.faces[-2].select_set(True)

    # Delete them and restore original mode
    bpy.ops.mesh.delete(type='ONLY_FACE')
    bpy.ops.object.mode_set(mode=original_mode)


def find_ob_type(ob: Object) -> str:
    # I'm not sure if this is possible to do without a bunch of if statements
    ob = bpy.context.object
    ob_type = ''

    # Fill face fills in a face for circle with trifan cap so I need this extra check in the beginning
    # Perhaps I can find a better way to fill faces
    if ob.data.polygons and all(vectors_are_same(f.normal, ob.data.polygons[0].normal) for f in ob.data.polygons):
        ob_type = 'circle'
        filled = 0
    else:
        # Remember how many faces the object has before filling holes(only cone, cylinder, circle)
        filled = fill_face(ob)
        faces = len(ob.data.polygons)

        # If the object has all quads it's most likely a torus
        if all(len(f.vertices) == 4 for f in ob.data.polygons):
            if faces == 1:  # Edge case circle with 4 verts
                ob_type = 'circle'
            elif faces == 6:  # Edge case cuboid
                ob_type = 'cylinder'
            else:
                ob_type = 'torus'
        # If the object has all triangles it's an icosphere or a cone/circle with trifan cap
        elif all(len(f.vertices) == 3 for f in ob.data.polygons):
            if faces+1 == len(ob.data.vertices) or faces == 1:
                ob_type = 'circle'
            elif faces == 4 or faces == 6:  # Edge case pyramid with ngon cap or trifan cap
                ob_type = 'cone'
            else:
                # Get the number of edges for each vertex
                bm = bmesh.new()
                bm.from_mesh(ob.data)
                unique_vert_edges = list(
                    set(len(v.link_edges) for v in bm.verts))

                # For icosphere some verts have 5 edges, some have 6, so their difference will be 1
                if abs(unique_vert_edges[0]-unique_vert_edges[1]) == 1:
                    ob_type = 'icosphere'
                else:
                    ob_type = 'cone'
                    # ob["sharp_tipped"] = True

        # Has to be a circle, we filled the face and there's only 1
        elif faces == 1:
            ob_type = 'circle'
        else:
            ngons = [round(f.area, 4)
                     for f in ob.data.polygons if len(f.vertices) > 4]
            if len(ngons) == 1:
                ob_type = 'cone'
                # ob["sharp_tipped"] = True
            # Could be either a cylinder or a cylindrical cone, but they have different areas
            elif len(ngons) == 2:
                if ngons[0] == ngons[1]:
                    ob_type = 'cylinder'
                else:
                    ob_type = 'cone'
            else:  # Could still be a cylinder/cone with trifan cap or sphere
                quads = sum(
                    1 for f in ob.data.polygons if len(f.vertices) == 4)
                if quads == 3:  # Edge case cylinder with 5 faces, 3 of them will be quads and top/bottom caps will be triangles if trifan or triangle if ngon cap
                    ob_type = 'cylinder'
                elif (len(ob.data.vertices)-2) / 2 == faces/3:
                    bm = bmesh.new()
                    bm.from_mesh(ob.data)
                    unique_edge_lengths = set(
                        round(edge.calc_length(), 4) for edge in bm.edges)

                    # Cone has 5 unique edge lengths when it has a trifan cap
                    if len(unique_edge_lengths) == 5:
                        ob_type = 'cone'
                    else:
                        ob_type = 'cylinder'
                else:
                    ob_type = 'sphere'

    delete_filled(ob, filled)
    return ob_type


def calculate_object_location_and_difference(ob: Object) -> tuple[Vector, Vector]:
    """ Returns object origin and how far it's from it """
    origin = ob.matrix_world.translation.copy()
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
    true_loc = ob.location.copy()
    set_origin(origin)

    return origin, true_loc - origin


def calculate_cone_location_and_difference(ob: Object, **kwargs) -> tuple[Vector, Vector]:
    """ Because origin to geometry doesn't work for cones we have to spawn another cone that looks exactly the same and compare the distance between the verts """

    # Save the scale and clear it, we need the scale to be 1,1,1 to get the correct distance between the objects
    saved_scale = ob.scale.copy()
    bpy.ops.object.scale_clear(clear_delta=False)
    original_origin = ob.matrix_world.translation.copy()

    # Add the exact same object and get the distances between 2 of their verts
    bpy.ops.mesh.primitive_cone_add(location=original_origin, **kwargs)
    twin_ob = bpy.context.active_object
    difference = (ob.matrix_world @ ob.data.vertices[0].co) - (
        twin_ob.matrix_world @ twin_ob.data.vertices[0].co)

    # Delete twin object, reselect the original and restore the scale
    bpy.data.meshes.remove(bpy.data.meshes[twin_ob.data.name])
    ob.select_set(True)
    ob.scale = saved_scale
    bpy.context.view_layer.objects.active = ob

    return original_origin, difference


def calculate_object_rotation(original_ob: Object, **kwargs) -> Euler:
    ob_type = kwargs.pop('ob_type')
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

    # Get the vertices of any face from the original object and then get those same vertices from the new object
    face_verts_orig, indices = get_any_face_verts_and_their_indices(
        original_ob)
    face_verts_new = [new_ob.matrix_world @
                      new_ob.data.vertices[idx].co for idx in indices]

    # Delete the twin object and reselect the original one
    bpy.data.meshes.remove(bpy.data.meshes[new_ob.data.name])
    bpy.context.view_layer.objects.active = original_ob
    original_ob.select_set(True)

    return calculate_matching_rotation(face_verts_orig, face_verts_new)


def get_any_face_verts_and_their_indices(ob: Object) -> tuple[list[Vector], list[int]]:
    """ Gets the vertices world location of any face from the object and their indices """
    if not ob.data.polygons:  # Circle is the only object potentially without a face face, just get verts
        return [ob.matrix_world @ v.co for v in ob.data.vertices], [v.index for v in ob.data.vertices]

    indices = ob.data.polygons[0].vertices
    return [ob.matrix_world @ ob.data.vertices[idx].co for idx in indices], indices


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


def calculate_cylinder_properties(ob: bpy.types.Object) -> tuple[float, float, int, str]:
    """ Calculates radius, depth, cap type and number of verts """

    enter_edit_mode_and_deselect_all()

    # Selecting entire ring from 2 verts doesn't work in these 2 cases, so just select the verts manually
    if len(ob.data.vertices) == 6:
        select_verts(ob, [0, 2, 4])
    elif len(ob.data.vertices) == 8 and len(ob.data.polygons) == 6:
        select_verts(ob, [0, 2, 4, 6])
    else:
        select_ring_from_verts(ob, [2, 4])

    selected = get_selected_verts(ob)
    radius = calculate_radius(selected)

    # Verts forming an edge from bottom to top are always subsequent
    depth = vector_distance(ob.data.vertices[0].co, ob.data.vertices[1].co)

    if len(selected) == len(ob.data.polygons):
        fill_type = 'NOTHING'
    elif len(selected) == len(ob.data.vertices)/2:
        fill_type = 'NGON'
    else:
        fill_type = 'TRIFAN'

    return radius, depth, len(selected), fill_type


def calculate_cone_properties(ob: bpy.types.Object) -> tuple[float, float, float, int, str]:
    """ Calculates radius, depth, cap type and number of verts """

    total_verts = len(ob.data.vertices)
    total_faces = len(ob.data.polygons)
    enter_edit_mode_and_deselect_all()

    if is_sharp_tipped(ob):
        if total_verts == total_faces:
            fill_type = 'NGON'
        elif total_faces == total_verts-1:
            fill_type = 'NOTHING'
        else:
            fill_type = 'TRIFAN'

        if total_verts == 4:
            select_verts(ob, [0, 1, 2])
        elif total_verts == 5:
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

        # The vert at the top has index that follows the last vert in the bottom ring
        top_index = verts + 1 if fill_type == 'TRIFAN' else verts
        depth = vector_distance(center_bottom, ob.data.vertices[top_index].co)

    # Cylindrical
    else:
        if total_verts == 6:
            select_verts(ob, [0, 2, 4])
        elif total_verts == 8 and len(ob.data.polygons) == 6:
            select_verts(ob, [0, 2, 4, 6])
        else:  # Select 2 neighbouring verts on the base and use them to select the entire ring
            select_ring_from_verts(ob, [2, 4])
        selected_bottom = get_selected_verts(ob)

        # Now we have to find the top verts
        enter_edit_mode_and_deselect_all()
        if total_verts == 6:
            select_verts(ob, [1, 3, 5])
        elif total_verts == 8 and len(ob.data.polygons) == 6:
            select_verts(ob, [1, 3, 5, 7])
        else:  # Select 2 neighbouring verts on the base and use them to select the entire ring
            select_ring_from_verts(ob, [3, 5])
        selected_top = get_selected_verts(ob)

        center_bottom = calculate_center(selected_bottom)
        center_top = calculate_center(selected_top)
        radius_bottom = calculate_radius(ob, center_bottom)
        radius_top = calculate_radius(ob, center_top)
        depth = vector_distance(center_bottom, center_top)
        # Any of them is fine since both top and bottom have the same amount of verts
        verts = len(selected_top)

        if len(selected_top) == total_faces:
            fill_type = 'NOTHING'
        elif len(selected_top) == total_verts/2:
            fill_type = 'NGON'
        else:
            fill_type = 'TRIFAN'

    return radius_bottom, radius_top, depth, verts, fill_type


def is_sharp_tipped(ob: Object) -> bool:
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


def calculate_radius(input_data: Object | list[Vector], center: Vector = None) -> float:
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


def enter_edit_mode_and_deselect_all() -> None:
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.editmode_toggle()


def get_selected_verts(ob: Object) -> list[Vector]:
    return [v.co for v in ob.data.vertices if v.select]


def select_verts(ob: Object, indices: list[int]) -> None:
    for idx in indices:
        ob.data.vertices[idx].select = True


def select_entire_ring() -> None:
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.loop_multi_select(ring=False)
    bpy.ops.object.editmode_toggle()


def select_ring_from_verts(ob: Object, vert_indices: list[int]) -> None:
    enter_edit_mode_and_deselect_all()
    select_verts(ob, vert_indices)
    select_entire_ring()


def calculate_sphere_segments(ob: Object) -> int:
    return len(ob.data.polygons) - (len(ob.data.vertices)-2)
