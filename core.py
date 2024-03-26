from collections import defaultdict
from itertools import chain
import bpy
import bmesh
from .localization import *
from math import cos, pi
from mathutils import Vector, Euler, Quaternion

TOLERANCE = 1e-5


def vector_distance(point1: Vector, point2: Vector) -> float:
    return (point2 - point1).length


def vectors_are_same(point1: Vector, point2: Vector) -> bool:
    """ Check if two vectors are the same within a certain tolerance """
    return vector_distance(point1, point2) <= TOLERANCE


def float_distance(c1: Vector, c2: Vector) -> float:
    return abs(c1 - c2)


def floats_are_same(c1: float, c2: float) -> bool:
    """ Check if two floats are the same within a certain tolerance """
    return float_distance(c1, c2) <= TOLERANCE


def save_and_reset_transforms(ob: bpy.types.Object) -> tuple[Vector, Euler]:

    saved_loc = Vector(ob.location)
    saved_rot = Euler(ob.rotation_euler)
    ob.location = (0, 0, 0)
    ob.rotation_euler = (0, 0, 0)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    return saved_loc, saved_rot


def fill_face(ob: bpy.types.Object) -> tuple[bool, int, int]:

    difference = 0
    count = len(ob.data.polygons)

    # Select everything and add faces in case the object has no cap(nothing will happen if it already has them)
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.fill_holes(sides=0)
    bpy.ops.mesh.select_all(action='DESELECT')

    bpy.ops.object.editmode_toggle()
    bpy.ops.object.editmode_toggle()

    new_count = len(ob.data.polygons)
    difference = new_count - count

    # Did we fill a face?
    return difference > 0, new_count, difference


def calculate_circle_radius(ob: bpy.types.Object) -> int:

    saved_loc, saved_rot = save_and_reset_transforms(ob)

    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()

    # Second because if the fill type is TRIFAN then there will be an extra vertex in the middle and it's at [0]th position
    V = bm.verts[1].co
    radius = vector_distance(Vector((0, 0, 0)), V)

    # Return to original rotation rotation
    bm.free()
    ob.location = saved_loc
    ob.rotation_euler = saved_rot

    return radius


def calculate_polygon_radius(vertices: int, tip_vertex: Vector, neighbour_vertex: Vector) -> int:
    """
    Look at https://drive.google.com/file/d/1azAUlG_XHxRG6XNy6xukxYQXmLwCqx1y/view?usp=sharing
    """

    c = 2*pi/vertices
    a = (pi-c)/2
    B_angle_1 = pi/2-a
    AB = vector_distance(tip_vertex, neighbour_vertex)
    BD = AB*cos(B_angle_1)
    B_angle_2 = pi/2-c
    BC = BD/cos(B_angle_2)

    return BC


def find_tip_and_neighbour_vert(ob: bpy.types.Object) -> tuple[Vector, Vector]:
    """
    Returns the furthest vertex from the middle and the one above it
    Look at https://drive.google.com/file/d/1vxOz5l6AhCBY4ArNSKlRR037CkDBoPA8/view?usp=sharing
    """

    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()

    # Blender always orders these in exactly the way we need, so we can just get first and second
    tip_vert = bm.verts[0].co
    neighbour_vert = bm.verts[1].co

    return tip_vert, neighbour_vert


def save_location_rotation(ob: bpy.types.Object) -> tuple[Vector, Euler, int]:
    """ Returns the true location and (possibly true) rotation of an object, at this point we can't be certain if the object is rotated, what matters is that we fix the location """

    # Save origin before changing it
    origin = Vector(ob.matrix_world.translation)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')

    return Vector(ob.matrix_world.translation), Euler(ob.rotation_euler), origin


def fix_cone_origin_and_save_location_rotation(ob: bpy.types.Object, applied_rotation: bool) -> tuple[Vector, Euler, int]:
    """ Returns the true location and (possibly true) rotation of an object, at this point we can't be certain if the object is rotated, what matters is that we fix the location """

    # If the rotation was applied then at this point object is upside down so we move it
    shift_value = -ob.dimensions.z/4 if applied_rotation else ob.dimensions.z/4

    # Save origin before changing it
    origin = Vector(ob.matrix_world.translation)

    # Fill in the missing faces so origin to center of volume would work for any type of cone
    bpy.ops.object.editmode_toggle()
    was_filled, total_faces, difference = fill_face(ob)
    bpy.ops.object.editmode_toggle()

    # Save the original location and rotation
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_VOLUME', center='MEDIAN')
    saved_rot = Euler(ob.rotation_euler)
    saved_loc = Vector(ob.matrix_world.translation)

    # Reset object location rotation then move the cursor where the cone origin should be and apply origin
    cursor_loc = Vector(bpy.context.scene.cursor.location)
    ob.rotation_euler = (0, 0, 0)
    ob.location = (0, 0, 0)
    bpy.context.scene.cursor.location = (0, 0, shift_value)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
    bpy.context.scene.cursor.location = cursor_loc  # Restore cursor location

    # if we filled in a face delete it
    if was_filled:

        bpy.ops.object.editmode_toggle()
        bm = bmesh.from_edit_mesh(ob.data)

        bpy.ops.mesh.select_all(action='DESELECT')
        bm.faces.ensure_lookup_table()
        bm.faces[total_faces-1].select_set(True)

        # if we added 2 faces select the other one aswell
        if difference == 2:
            bm.faces[total_faces-2].select_set(True)
        bpy.ops.mesh.delete(type='FACE')

        bpy.ops.object.editmode_toggle()

    # Restore original object rotation and location, but because we moved the origin we have to move the object on local Z for the object to be at the same spot it was when its origin was broken
    ob.location = saved_loc
    ob.rotation_euler = saved_rot
    bpy.ops.transform.translate(
        value=(0, 0, shift_value), orient_type='LOCAL')

    return Vector(ob.matrix_world.translation), saved_rot, origin


def rotate_around_axis_followed_by_euler_rotation(axis: str, angle: float, euler_rotation: Euler) -> Euler:
    """
    Used to calculate final rotation and done in 2 steps:
        1. First rotating on given axis by given angle
        2. Then rotating on all three axes
    """

    if axis == 'Z':
        quat1 = Quaternion((0, 0, 1), angle)
    elif axis == 'X':
        quat1 = Quaternion((1, 0, 0), angle)
    else:
        quat1 = Quaternion((0, 1, 0), angle)

    quat2 = euler_rotation.to_quaternion()
    quat_outer_product = quat2 @ quat1

    return quat_outer_product.to_euler()


def calculate_torus_major_segments(ob: bpy.types.Object) -> int:

    saved_loc, saved_rot = save_and_reset_transforms(ob)

    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    middle = Vector((0, 0, 0))

    # Get the distance of any vert to the center, then look for all the verts that belong to that ring
    ring_vert = bm.verts[0].co
    dist = vector_distance(ring_vert, middle)

    # Checking for same Z isn't enough because we can have an inner ring at same Z which shouldn't be counted, it has different dist though
    # Look at https://drive.google.com/file/d/12uINdegB93RPiPTYzLv5-8PSNVTv8J8S/view?usp=sharing
    segments = sum([floats_are_same(v.co.z, ring_vert.z)
                   and floats_are_same(vector_distance(v.co, middle), dist) for v in bm.verts])

    # Restore original object location/rotation
    bm.free()
    ob.location = saved_loc
    ob.rotation_euler = saved_rot

    return segments


def restore_origin(original_origin: Vector) -> None:
    """Restores the origin by moving the 3D cursor to the original location and setting the origin to cursor"""
    cursor_loc = Vector(bpy.context.scene.cursor.location)
    bpy.context.scene.cursor.location = original_origin
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
    bpy.context.scene.cursor.location = cursor_loc


def calculate_sphere_segments(ob):

    # save both and reset to 0, return it to original after
    saved_loc, saved_rot = save_and_reset_transforms(ob)

    bm = bmesh.new()
    bm.from_mesh(ob.data)

    i = 0

    # pick a vert that will never be top or bottom
    bm.verts.ensure_lookup_table()
    tempZ = round(bm.verts[4].co[2], 4)

    # compare all the other vert Z values with the Z value we picked previously
    # this gives us number of segments
    for v in bm.verts:
        current_vert = v.co
        if round(current_vert[2], 4) == tempZ:
            i += 1

    bm.free()

    # restore original object location/rotation
    ob.location = saved_loc
    ob.rotation_euler = saved_rot

    return i


def calculate_icosphere_radius(ob):

    # save both and reset to 0, return it to original after
    saved_loc, saved_rot = save_and_reset_transforms(ob)

    bm = bmesh.new()
    bm.from_mesh(ob.data)

    bm.verts.ensure_lookup_table()
    radius = vector_distance(bm.verts[0].co, Vector((0, 0, 0)))

    ob.location = saved_loc
    ob.rotation_euler = saved_rot
    bm.free()

    return radius


def is_cone_cylindrical(ob: bpy.types.Object) -> bool:
    ''' Cylindrical cones have the same location when origin is set to bounds or median '''
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    loc_origin_bounds = Vector(ob.location)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
    loc_origin_median = Vector(ob.location)

    return vectors_are_same(loc_origin_bounds, loc_origin_median)


def calculate_cone_properties(ob: bpy.types.Object) -> tuple[float, float, int, str, bool]:
    """ Calculates bottom/top radius, number of verts,cap type and if it's sharp tipped"""

    # We already fixed the rotation at this point now just have to reset it to 0,0,0 so z values are correct
    saved_rot = Euler(ob.rotation_euler)
    ob.rotation_euler = (0, 0, 0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

    top_vertices, bottom_vertices = [], []
    min_z, max_z = float('inf'), float('-inf')

    # Classify vertices as belonging to the top or bottom
    for v in ob.data.vertices:
        z = v.co.z
        if z > max_z + TOLERANCE:
            max_z = z
            top_vertices = [v]
        elif floats_are_same(z, max_z):
            top_vertices.append(v)

        if z < min_z - TOLERANCE:
            min_z = z
            bottom_vertices = [v]
        elif floats_are_same(z, min_z):
            bottom_vertices.append(v)

    # Calculate radii
    def calculate_radius_from_face_verts(vertices) -> int:
        if len(vertices) <= 1:
            return 0
        center = sum((v.co for v in vertices), Vector()) / len(vertices)
        return sum(vector_distance(v.co, center) for v in vertices) / len(vertices)

    top_radius = calculate_radius_from_face_verts(top_vertices)
    bottom_radius = calculate_radius_from_face_verts(bottom_vertices)

    sharp_tipped = len(top_vertices) == 1 or len(bottom_vertices) == 1

    # Determine cap type based on face normals and vertex count
    cap_faces = [f for f in ob.data.polygons if abs(f.normal.z) > 0.99]
    cap_type = 'NOTHING' if len(cap_faces) == 0 else (
        'NGON' if len(cap_faces) <= 2 else 'TRIFAN')

    # Vertices count for the larger end, subtract 1 if cap is trifan
    verts_count = max(len(top_vertices), len(bottom_vertices))
    verts_count = verts_count-1 if cap_type == 'TRIFAN' else verts_count

    # Restore original object rotation
    ob.rotation_euler = saved_rot

    return bottom_radius, top_radius, verts_count, cap_type, sharp_tipped


def calculate_cylinder_properties(ob: bpy.types.Object) -> tuple[float, int, str]:
    """ Calculates radius, number of verts and cap type"""

    # Center the object and remember it's current location/rotation
    saved_loc, saved_rot = save_and_reset_transforms(ob)

    # Get third vert because if cap was trifan, [0] and [1] are middle verts
    cap_vert = ob.data.vertices[2].co
    cap_verts = [v for v in ob.data.vertices
                 if floats_are_same(v.co.z, cap_vert.z)]

    # Radius is the distance between a cap vert and a center fake vert(we centered the object so it's at 0,0,z)
    radius = vector_distance(cap_vert, Vector((0, 0, cap_vert.z)))

    # Get all the faces with normal pointing up or down, since the object is centered, the normal will be [0,0,1] or [0,0,-1]
    cap_faces = [f for f in ob.data.polygons if abs(f.normal[2]) > 0.99]
    if len(cap_faces) == 0:
        cap_type = 'NOTHING'
    elif len(cap_faces) <= 2:
        cap_type = 'NGON'
    else:
        cap_type = 'TRIFAN'

    # Restore original object location/rotation
    ob.location = saved_loc
    ob.rotation_euler = saved_rot

    verts = len(cap_verts)-1 if cap_type == 'TRIFAN' else len(cap_verts)
    return radius, verts, cap_type


def applied_rotation_circle(ob: bpy.types.Object) -> bool:
    """ Checks if the circle verts have more than 1 unique Z value """

    saved_rot = Euler(ob.rotation_euler)
    bpy.ops.object.rotation_clear(clear_delta=False)
    z = ob.data.vertices[0].co.z

    applied = any(abs(z - v.co.z) > TOLERANCE for v in ob.data.vertices)

    ob.rotation_euler = saved_rot

    return applied


def applied_rotation_cone_or_cylinder(ob: bpy.types.Object) -> bool:
    """ Check if cone or cylinder have verts with more than 2 unique Z values """

    # Clear the rotation because we want the object sitting flat on x/y axes
    saved_rot = Euler(ob.rotation_euler)
    bpy.ops.object.rotation_clear(clear_delta=False)

    zs = set()

    for v in ob.data.vertices:

        z = round(v.co.z, 5)
        zs.add(z)

        if len(zs) > 2:
            return True

    ob.rotation_euler = saved_rot
    return False


def applied_rotation_torus(ob: bpy.types.Object) -> bool:
    """ Check if torus has more verts with different [Z] than minor segments """

    # Clear the rotation because we want the object sitting flat on x/y axes
    saved_rot = Euler(ob.rotation_euler)
    bpy.ops.object.rotation_clear(clear_delta=False)
    zs = set()

    for v in ob.data.vertices:
        z = round(v.co.z, 5)
        zs.add(z)

    ob.rotation_euler = saved_rot

    # total polygons = major segments*minor segments
    # At this point we don't know how many major or minor segments torus has but we know how many polygons
    # We also know that minimum number of both segments is 3, that means if we assume that there is 3 major segments then we get the max amount of minor segments
    return len(zs) > len(ob.data.polygons)/3


def applied_rotation_sphere(ob: bpy.types.Object) -> bool:
    """ Check how many verts have different Z values, if the sphere is slightly rotated 
        it's gonna have more verts with different Zs than there are rings """

    # Clear the rotation because we want the object sitting flat on x/y axes
    saved_rot = Euler(ob.rotation_euler)
    bpy.ops.object.rotation_clear(clear_delta=False)
    zs = set()

    for v in ob.data.vertices:

        z = round(v.co.z, 5)
        zs.add(z)

    ob.rotation_euler = saved_rot

    # total polygons = segments*rings
    # At this point we don't know how many segments or rings sphere has, but we know how many polygons
    # We also know that the minimum number of both rings and segments is 3
    # By assuming the worst case scenario which is sphere having 3 segments we can say it has polygons/3 rings
    return len(zs)-1 > len(ob.data.polygons)/3


def select_smallest_from_selected_faces(faces) -> None:
    bpy.ops.mesh.select_all(action='DESELECT')
    faces[min([(f.calc_area(), idx)
               for idx, f in enumerate(faces)])[1]].select_set(True)


def show_or_hide_modifiers_in_viewport(ob, visibility) -> bool:
    """ Modifiers change some object data so we disable them before calculating said data """

    was_changed = False
    for mod in getattr(ob, "modifiers", []):
        # If modifier viewport visibility is different from given visibility
        if mod.show_viewport != visibility:
            mod.show_viewport = visibility
            was_changed = True

    return was_changed


def calculate_z_offset(N: int) -> float:
    """ Calculates the offset necessary to match the rotation after using fix rotation operator
        it is equal to the interior angle between two sides divided by -2
        look at https://drive.google.com/file/d/1FCij1TjPVtvxHkxPpxW_ekRujkDkQivQ/view?usp=sharing """

    interior_angles = pi-(2*pi/N)
    z_offset = -interior_angles/2

    return z_offset


def copy_modifiers_and_delete_original(original_ob: bpy.types.Object, new_ob: bpy.types.Object) -> None:

    parent = original_ob.parent
    name = original_ob.name

    # Copy over display type and keep the same shading
    new_ob.display_type = original_ob.display_type
    if original_ob.data.polygons and original_ob.data.polygons[0].use_smooth:
        bpy.ops.object.shade_smooth()

    # Remember all the collections the object belonged to since we will delete it
    original_collections = original_ob.users_collection

    if parent:
        new_ob.parent = parent
        new_ob.matrix_parent_inverse = parent.matrix_world.inverted()  # Keep transform

        # If the parent has some modifiers that point to the original object, point them to new one instead
        for mod in parent.modifiers:
            if hasattr(mod, 'object') and mod.object == original_ob:
                mod.object = new_ob

    for child in original_ob.children:
        child.parent = new_ob
        child.matrix_parent_inverse = new_ob.matrix_world.inverted()  # Keep transform

    # Make the original object active then copy all the modifiers and materials to the new object
    bpy.context.view_layer.objects.active = original_ob
    bpy.ops.object.make_links_data(type='MODIFIERS')
    bpy.ops.object.make_links_data(type='MATERIAL')

    # Delete the original object mesh, this will also delete the object
    bpy.data.meshes.remove(bpy.data.meshes[original_ob.data.name])

    # Select the newly created object
    new_ob.select_set(True)
    bpy.context.view_layer.objects.active = new_ob

    # Rename the new object to match the original, and add it to all the collections the original object belonged to
    new_ob.name = name
    for col in original_collections:
        if name not in col.objects:
            col.objects.link(new_ob)


def select_unique_faces(ob: bpy.types.Object) -> None:
    """ Select faces that appear only once or twice, otherwise select the first one """
    bm = bmesh.from_edit_mesh(ob.data)
    area_faces = defaultdict(list)

    # Group faces by their area
    for face in bm.faces:
        area = round(face.calc_area(), 4)
        area_faces[area].append(face)

    # Get unique faces (appear only once or twice)
    unique_faces = chain.from_iterable(
        faces for faces in area_faces.values() if len(faces) <= 2)

    # Deselect everything and select unique faces
    bpy.ops.mesh.select_all(action='DESELECT')
    if len(unique_faces) > 0:
        for face in unique_faces:
            face.select_set = True
    else:
        bm.faces[0].select_set(True)


def select_rotational_cylinder(ob: bpy.types.Object):
    """
    Select or create faces that are needed to properly rotate the cylinder
    #TODO Refactor
    """

    # change selection to faces
    bpy.context.tool_settings.mesh_select_mode = (False, False, True)

    was_filled, total_faces, difference = fill_face(ob)
    bm = bmesh.from_edit_mesh(ob.data)

    # try to select ngons
    bpy.ops.mesh.select_face_by_sides(number=4, type='GREATER')

    # ngon cap-------------------------------------------------------------------------------------------------------------------
    if len([f for f in bm.faces if f.select]) != 0:

        # deselect 1 and align view to selection
        bpy.ops.mesh.select_nth(skip=1, nth=1)
        bpy.ops.view3d.view_axis(type='TOP', align_active=True)

    # cylinder is a rectangle
    elif len(bm.faces) == 6:

        # select top/bottom face and align to selection
        bm.faces.ensure_lookup_table()
        bm.faces[5].select_set(True)
        bpy.ops.view3d.view_axis(type='TOP', align_active=True)

    elif len(bm.faces) == 5:

        # select top/bottom face and align to selection
        bm.faces.ensure_lookup_table()
        bm.faces[4].select_set(True)
        bpy.ops.view3d.view_axis(type='TOP', align_active=True)

    # cap is made of triangles------------------------------------------------------------
    else:

        # this selects one of the faces on top/bottom, we get the full face using coplanar
        bm.faces.ensure_lookup_table()
        bm.faces[total_faces-2].select_set(True)
        bpy.ops.mesh.select_similar(type='FACE_COPLANAR', threshold=0.01)

        # dissolve selected faces,left with an ngon
        bpy.ops.mesh.dissolve_faces()

        # align view to selection and poke faces back
        bpy.ops.view3d.view_axis(type='TOP', align_active=True)
        bpy.ops.mesh.poke()

    # delete cap if we added it
    if was_filled:

        # select last 2 added faces and delete them
        bm.faces.ensure_lookup_table()
        bm.faces[total_faces-1].select_set(True)
        bm.faces[total_faces-2].select_set(True)
        bpy.ops.mesh.delete(type='FACE')


def select_rotational_cone(ob: bpy.types.Object):
    """ Select or create faces that are needed to properly rotate the cone """

    # Change selection to faces
    bpy.context.tool_settings.mesh_select_mode = (False, False, True)

    was_filled, total_faces, difference = fill_face(ob)
    bm = bmesh.from_edit_mesh(ob.data)

    # try to select ngons
    bpy.ops.mesh.select_face_by_sides(number=4, type='GREATER')
    selected_faces = [f for f in bm.faces if f.select]
    selected = len(selected_faces)

    # single ngon cap-------------------------------------------------------------------------------------------------------------------
    if selected == 1:

        # align view to selection
        bpy.ops.view3d.view_axis(type='TOP', align_active=True)

    # double ngon cap-------------------------------------------------------------------------------------------------------------------
    elif selected == 2:

        select_smallest_from_selected_faces(selected_faces)

        # align view to selection
        bpy.ops.view3d.view_axis(type='TOP', align_active=True)

    # if nothing got selected try to select quads
    else:

        bpy.ops.mesh.select_face_by_sides(number=4, type='EQUAL')
        selected_faces = [f for f in bm.faces if f.select]
        selected = len(selected_faces)
        # quad cap----------------------------
        if selected == 1:

            # align view to selection
            bpy.ops.view3d.view_axis(type='TOP', align_active=True)

        # double quad cap-----------------------------
        elif selected == 2:

            # first select the pair that only appears once(top and bottom, not sides)
            select_unique_faces(ob)
            # then select the smaller one
            selected_faces = [f for f in bm.faces if f.select]
            select_smallest_from_selected_faces(selected_faces)

            # align view to selection
            bpy.ops.view3d.view_axis(type='TOP', align_active=True)

        # edge case when cone is made of six quads, both top and bottom base, and sides are all quads
        elif selected == 6:

            # first select the pair that only appears once(top and bottom, not sides)
            select_unique_faces(ob)
            # then select the smaller one
            selected_faces = [f for f in bm.faces if f.select]
            select_smallest_from_selected_faces(selected_faces)

            # align view to selection
            bpy.ops.view3d.view_axis(type='TOP', align_active=True)

        # cap is made of triangles------------------------------------------------------------------------------------------------------------
        else:

            # selection to verts
            bpy.context.tool_settings.mesh_select_mode = (True, False, False)

            # special case when cone is a pyramid but cap isn't trifan
            if len(ob.data.vertices) == 4:

                # this will select the base and align to it, if all faces are same then it doesn't matter
                select_unique_faces(ob)
                bpy.ops.view3d.view_axis(type='TOP', align_active=True)

                # delete cap if we added it
                if was_filled:
                    bpy.ops.mesh.delete(type='FACE')

                return

            # special case when cone is a half pyramid but cap isn't trifan
            if len(ob.data.vertices) == 6:

                # this will select the top and botom base
                select_unique_faces(ob)

                # select the smaller of the two and align to it
                selected_faces = [f for f in bm.faces if f.select]
                select_smallest_from_selected_faces(selected_faces)
                bpy.ops.view3d.view_axis(type='TOP', align_active=True)

                # delete cap if we added it
                if was_filled:

                    bm.faces.ensure_lookup_table()
                    bm.faces[total_faces-1].select_set(True)
                    # if we added 2 faces delete it aswell
                    if difference == 2:
                        bm.faces[total_faces-2].select_set(True)
                    bpy.ops.mesh.delete(type='FACE')

                return

            # this will select everything but the cap vert, invert to get it
            bpy.ops.mesh.edges_select_sharp(sharpness=0.0174533)
            bpy.ops.mesh.select_all(action='INVERT')
            selected_faces = [v for v in bm.verts if v.select]
            selected = len(selected_faces)

            # cone has 1 side
            if selected == 1:

                # select all the faces touching the cap vert, this selects the entire base
                bpy.ops.mesh.select_more(use_face_step=True)
                bpy.ops.mesh.dissolve_faces()
                bpy.ops.view3d.view_axis(type='TOP', align_active=True)
                bpy.ops.mesh.poke()

                return

            # cone has two sides we have to dissolve the middle verts and select the smaller face
            else:

                # change select mode to faces and select all the triangles
                bpy.context.tool_settings.mesh_select_mode = (
                    False, False, True)
                bpy.ops.mesh.select_face_by_sides(number=3, type='EQUAL')

                # dissolve faces, we'll end up with 1 face on each side
                bpy.ops.mesh.dissolve_faces()

                selected_faces = [f for f in bm.faces if f.select]
                select_smallest_from_selected_faces(selected_faces)

                # align view to selection
                bpy.ops.view3d.view_axis(type='TOP', align_active=True)

                # we deselected one of them previously, reselect it and poke both faces
                selected_faces[0].select_set(True)
                selected_faces[1].select_set(True)
                bpy.ops.mesh.poke()

    # if we filled in a face delete it
    if was_filled:

        bpy.ops.mesh.select_all(action='DESELECT')
        bm.faces.ensure_lookup_table()
        bm.faces[total_faces-1].select_set(True)

        # if we added 2 faces select the other one aswell
        if difference == 2:
            bm.faces[total_faces-2].select_set(True)
        bpy.ops.mesh.delete(type='FACE')


def insert_middle_face_torus(ob):
    """
    select the middle torus ring and fill in a face, we need this to properly rotate
    """

    bm = bmesh.from_edit_mesh(ob.data)
    i = 0
    # select two different verts in the same ring by comparing their distances to middle
    for v in bm.verts:

        current_vert = v.co
        # if first time in the loop initialize distance from the current point to the middle
        if i == 0:
            shared_distance = round(vector_distance(
                current_vert, Vector((0, 0, 0))), 4)
            v.select = True
            i += 1
            continue

        if round(vector_distance(current_vert, Vector((0, 0, 0))), 4) == shared_distance:
            # select the other vert if it has same distance
            v.select = True
            # break as soon as we get second one we can select the entire ring by knowing just the 2 of them
            break

    # confirm selection
    bpy.ops.object.editmode_toggle()
    bpy.ops.object.editmode_toggle()

    # now that we have 2 verts on same ring selected we just have to use select ring command
    bpy.ops.mesh.loop_multi_select(ring=False)

    # after that we'll fill in a face and change selection to faces
    bpy.ops.mesh.edge_face_add()
    bpy.context.tool_settings.mesh_select_mode = (False, False, True)

    # align to selected face and delete it, we don't need it anymore, discard it like others discard us
    bpy.ops.view3d.view_axis(type='TOP', align_active=True)
    bpy.ops.mesh.delete(type='FACE')

    return

# Individual functions that replace the current mesh with a new one that looks the same-----------------------------------------------------------------


def replace_circle(vertices, radius, cap_fill, location, rotation, align, b_UV: bool, origin: Vector) -> None:

    # original object reference
    original_ob = bpy.context.active_object

    if align != "WORLD":
        bpy.ops.mesh.primitive_circle_add(vertices=vertices, radius=radius, fill_type=cap_fill, location=location, calc_uvs=b_UV,
                                          align=align)
    else:
        bpy.ops.mesh.primitive_circle_add(vertices=vertices, radius=radius, fill_type=cap_fill, location=location, rotation=rotation,
                                          calc_uvs=b_UV)

    new_ob = bpy.context.active_object
    copy_modifiers_and_delete_original(original_ob, new_ob)
    restore_origin(origin)


def replace_cone(vertices, radius1, radius2, depth, cap_fill, location, rotation, align, b_UV, origin: Vector) -> None:

    # original object reference
    original_ob = bpy.context.active_object

    # add a new object that matches the original object
    if align != "WORLD":

        bpy.ops.mesh.primitive_cone_add(end_fill_type=cap_fill, depth=depth, radius1=radius1, radius2=radius2, vertices=vertices,
                                        location=location, calc_uvs=b_UV, align=align)
    else:
        bpy.ops.mesh.primitive_cone_add(end_fill_type=cap_fill, depth=depth, radius1=radius1, radius2=radius2, vertices=vertices,
                                        location=location, calc_uvs=b_UV, rotation=rotation)

    new_ob = bpy.context.active_object
    copy_modifiers_and_delete_original(original_ob, new_ob)
    restore_origin(origin)


def replace_cylinder(vertices, radius, depth, cap_fill, location, rotation, align, b_UV, origin: Vector) -> None:
    # original object reference
    original_ob = bpy.context.active_object

    if align != "WORLD":
        bpy.ops.mesh.primitive_cylinder_add(end_fill_type=cap_fill, depth=depth, radius=radius, vertices=vertices, location=location,
                                            calc_uvs=b_UV, align=align)
    else:
        bpy.ops.mesh.primitive_cylinder_add(
            end_fill_type=cap_fill, depth=depth, radius=radius, vertices=vertices, location=location, rotation=rotation, calc_uvs=b_UV)

    new_ob = bpy.context.active_object
    copy_modifiers_and_delete_original(original_ob, new_ob)
    restore_origin(origin)


def replace_icosphere(subdivisions, radius, location, rotation, align, b_UV, origin: Vector) -> None:

    # original object reference
    original_ob = bpy.context.active_object

    if align != "WORLD":
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=subdivisions, radius=radius, location=location, calc_uvs=b_UV, align=align)
    else:
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=radius, location=location, rotation=rotation,
                                              calc_uvs=b_UV)

    new_ob = bpy.context.active_object
    copy_modifiers_and_delete_original(original_ob, new_ob)
    restore_origin(origin)


def replace_torus(major_segments, minor_segments, major_radius, minor_radius, location, rotation, align, b_UV, origin: Vector) -> None:

    # original object reference
    original_ob = bpy.context.active_object

    if align != "WORLD":
        bpy.ops.mesh.primitive_torus_add(major_segments=major_segments, minor_segments=minor_segments, location=location,
                                         major_radius=major_radius, minor_radius=minor_radius, generate_uvs=b_UV, align=align)
    else:
        bpy.ops.mesh.primitive_torus_add(major_segments=major_segments, minor_segments=minor_segments, location=location,
                                         major_radius=major_radius, minor_radius=minor_radius, generate_uvs=b_UV, rotation=rotation)

    new_ob = bpy.context.active_object
    copy_modifiers_and_delete_original(original_ob, new_ob)
    restore_origin(origin)


def replace_uv_sphere(segments, rings, radius, location, rotation, align, b_UV, origin: Vector) -> None:

    # original object reference
    original_ob = bpy.context.active_object

    if align != "WORLD":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=radius, location=location, calc_uvs=b_UV,
                                             align=align)
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=radius, location=location, rotation=rotation,
                                             calc_uvs=b_UV)

    new_ob = bpy.context.active_object
    copy_modifiers_and_delete_original(original_ob, new_ob)
    restore_origin(origin)


def calculate_sides(ob):

    total_faces = len(ob.data.polygons)
    total_vertices = len(ob.data.vertices)
    sides = 0
    group = 0

    if ob.data.name.startswith(localization_cylinder):
        group = 1
        if total_faces == (total_vertices/2)+2 or total_faces == total_vertices/2:
            sides = total_vertices/2
        else:
            sides = total_vertices-2/2

    elif ob.data.name.startswith(localization_circle):
        group = 1
        if total_faces == 0:
            cap_type = 'NOTHING'
        elif total_faces == 1:
            cap_type = 'NGON'
        else:
            cap_type = 'TRIFAN'
        if cap_type == 'TRIFAN':
            sides = total_vertices-1
        else:
            sides = total_vertices

    elif ob.data.name.startswith(localization_cone):
        group = 1

        # first rotate it by 180 on Y axis because it will be flipped
        ob.rotation_euler = Euler((0, pi, 0))
        bpy.ops.object.transform_apply(
            location=False, rotation=True, scale=False)

        _, _, sides, _, _ = calculate_cone_properties(ob)

    elif ob.data.name.startswith(localization_sphere):
        group = 1
        sides = calculate_sphere_segments(ob)

    elif ob.data.name.startswith(localization_torus):
        group = 2
        sides = calculate_torus_major_segments(ob)

    elif ob.data.name.startswith(localization_icosphere):
        group = 3

    return sides, group


def Z_offset_ob(ob: bpy.types.Object) -> None:
    """ After fixing object rotation we might have to rotate it around Z axis to match the original """
    # We have to know how many sides object has and which group it belongs to
    sides, group = calculate_sides(ob)

    # Circle, cone, UVSphere and cylinder
    if group == 1:
        if (sides-2) % 4:
            if ob.data.name.startswith(localization_cone) and sides % 2:
                ob.rotation_euler = Euler((0, 0, pi/2))
            else:
                ob.rotation_euler = Euler((0, 0, -calculate_z_offset(sides)))

    # Torus
    elif group == 2:

        # If you were to cut torus on both X and Y and the quarter piece you get was symmetrical to itself
        if sides % 4 == 0:
            z_offset = calculate_z_offset(sides)
            ob.rotation_euler = Euler((0, 0, -z_offset))

        # Torus is symmetrical on both X and Y but the quarter piece isn't symmetrical
        elif sides % 2 == 0:
            ob.rotation_euler = Euler((0, 0, -pi/2))

        # Torus is only symmetrical on 1 axis
        else:
            ob.rotation_euler = Euler((0, 0, -pi))

    # Unlike other objects icosphere only needs to be rotated on Z for 180
    elif group == 3:
        ob.rotation_euler = Euler((0, 0, -pi))

    # No need to fix the rotation for other types
    return


def smart_selection(ob: bpy.types.Object) -> None:
    """ Selects the necessary face in order to rotate the object properly """

    if ob.data.name.startswith(localization_sphere):

        # Select all quads invert the selection,we get the top and bottom vert
        bpy.ops.mesh.select_face_by_sides(number=4, type='EQUAL')
        bpy.ops.mesh.select_all(action='INVERT')

        # deselect one and select all the surrounding faces
        bpy.ops.mesh.select_nth(skip=1, nth=1, offset=0)
        bpy.ops.mesh.select_more(use_face_step=True)

        # make a duplicate of selected faces and even them out
        bpy.ops.mesh.duplicate()
        bpy.ops.transform.resize(value=(1, 1, 0), orient_type='NORMAL')

        # dissolve faces to get an ngon, align to newly made NGON and then delete it
        bpy.ops.mesh.dissolve_faces()
        bpy.ops.view3d.view_axis(type='TOP', align_active=True)
        bpy.ops.mesh.delete(type='FACE')

    elif ob.data.name.startswith(localization_cylinder):
        select_rotational_cylinder(ob)

    elif ob.data.name.startswith(localization_torus):
        insert_middle_face_torus(ob)

    elif ob.data.name.startswith(localization_circle):
        faces = len(ob.data.polygons)
        circleHadNoCap = False

        # change selection to faces and select everything
        bpy.context.tool_settings.mesh_select_mode = (False, False, True)
        bpy.ops.mesh.select_all(action='SELECT')

        # if circle doesn't have a cap fill it
        if faces == 0:

            circleHadNoCap = True
            bpy.ops.mesh.fill_holes(sides=0)

        # trifan cap --------------------------------------------------------------------------
        if faces > 1:

            bpy.ops.mesh.dissolve_faces()
            bpy.ops.view3d.view_axis(type='TOP', align_active=True)
            bpy.ops.mesh.poke()

            return

        # align to selection
        bpy.ops.view3d.view_axis(type='TOP', align_active=True)

        # delete cap if we added it
        if circleHadNoCap:

            bpy.ops.mesh.delete(type='ONLY_FACE')

    elif ob.data.name.startswith(localization_cone):

        select_rotational_cone(ob)

    elif ob.data.name.startswith(localization_icosphere):

        # select the top vert and surrounding faces
        bm = bmesh.from_edit_mesh(ob.data)
        bm.verts.ensure_lookup_table()
        bm.verts[0].select_set(True)
        bpy.ops.mesh.select_more(use_face_step=True)

        # make a duplicate of selected faces and even them out
        bpy.ops.mesh.duplicate()
        bpy.ops.transform.resize(value=(1, 1, 0), orient_type='NORMAL')

        # dissolve faces to get an ngon, align to newly made NGON and then delete it
        bpy.ops.mesh.dissolve_faces()
        bpy.ops.view3d.view_axis(type='TOP', align_active=True)
        bpy.ops.mesh.delete(type='FACE')

    # else the object is none of the primitive shapes
    else:

        # change selection to faces
        bpy.context.tool_settings.mesh_select_mode = (False, False, True)

        # select first face and align view to selection
        bm = bmesh.from_edit_mesh(ob.data)
        bm.faces.ensure_lookup_table()
        bm.faces[0].select_set(True)

        # align view to selection
        bpy.ops.view3d.view_axis(type='TOP', align_active=True)

    return
