import bpy
import bmesh
from math import cos, pi
from mathutils import Vector, Euler, Quaternion


def distance_vec(point1: Vector, point2: Vector) -> float:
    """
    return distance between two vectors
    """

    return (point2 - point1).length


def save_reset_and_apply_transforms(ob):

    saved_loc = Vector(ob.location)
    saved_rot = Euler(ob.rotation_euler)
    ob.location = (0, 0, 0)
    ob.rotation_euler = (0, 0, 0)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    return saved_loc, saved_rot


def fill_face_if_non_manifold(ob):

    was_filled = False
    difference = 0
    # count number of current faces
    current_polygons = len(ob.data.polygons)

    # select everything and add faces in case the object has no cap(nothing will happen if it already has them)
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.fill_holes(sides=0)
    bpy.ops.mesh.select_all(action='DESELECT')

    bpy.ops.object.editmode_toggle()
    bpy.ops.object.editmode_toggle()

    new_polygons = len(ob.data.polygons)
    # if the new count of faces is different it means we filled in a face
    if new_polygons != current_polygons:
        was_filled = True
        difference = new_polygons-current_polygons

    return was_filled, new_polygons, difference


def calculate_circle_radius(ob):
    """
    calculate and return circle radius
    """

    # save both and reset to 0, return it to original after
    saved_loc, saved_rot = save_reset_and_apply_transforms(ob)

    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()

    # second because if the fill type is TRIFAN then there will be an extra vertex in the middle and it's the first one
    temp_vert = bm.verts[1].co
    radius = distance_vec(Vector((0, 0, 0)), temp_vert)

    # return to original rotation rotation
    ob.location = saved_loc
    ob.rotation_euler = saved_rot
    bm.free()

    return radius


def calculate_polygon_radius(vertices, tip_vertex, neighbour_vertex):
    """
    calculate and return polygon radius, used for torus and cone
    look at https://drive.google.com/file/d/1azAUlG_XHxRG6XNy6xukxYQXmLwCqx1y/view?usp=sharing
    """

    c = 2*pi/vertices
    a = (pi-c)/2
    B_angle_1 = pi/2-a
    AB = distance_vec(tip_vertex, neighbour_vertex)
    BD = AB*cos(B_angle_1)
    B_angle_2 = pi/2-c
    BC = BD/cos(B_angle_2)
    radius = BC

    return radius


def find_tip_and_neighbour_vert(ob):
    """
    returns the furthest vertex from the middle and the one above it
    look at https://drive.google.com/file/d/1vxOz5l6AhCBY4ArNSKlRR037CkDBoPA8/view?usp=sharing
    """

    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()

    # blender is smart so first two verts are actually exactly what we need
    tip_vert = bm.verts[0].co
    neighbour_vert = bm.verts[1].co

    return tip_vert, neighbour_vert


def save_location_rotation(ob):
    """
    return location and rotation, also set origin to geometry if the location is (0,0,0) in case the location was applied
    """

    if ob.location == Vector((0, 0, 0)):
        # this gives us the true location of the object
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')

    return Vector(ob.location), Euler(ob.rotation_euler)


def fix_cone_origin_and_save_location_rotation(ob):
    """
    same as save_location_rotation except this one is specifically for cone to prevent location issues
    origin to geometry doesn't work well with 1 sided cones so we have to fix it
    look at https://drive.google.com/file/d/1tn1tpJ6c1lfMBvkmYQAhpQPUxnCknAI5/view?usp=sharing
    """

    if ob.location == Vector((0, 0, 0)):

        # set origin to generate a location for the object in case the location isn't true (0,0,0) but rather applied
        bpy.ops.object.origin_set(
            type='ORIGIN_CENTER_OF_VOLUME', center='MEDIAN')

        # saving the rotation and setting it to 0 so the object would be moved on Z axis properly
        saved_rot = Euler(ob.rotation_euler)
        ob.rotation_euler = (0, 0, 0)

        # save cursor location and set it to (0,0,0)
        cursor_loc = Vector(bpy.context.scene.cursor.location)
        bpy.context.scene.cursor.location = (0, 0, 0)

        # setting origin to center of volume, this offsets the usual origin when the object is first made so we have to tweak it to match the original
        bpy.ops.object.origin_set(
            type='ORIGIN_CENTER_OF_VOLUME', center='MEDIAN')
        save_location = Vector(ob.location)

        # offsetting the object on Z by the negative offset
        offset = ob.dimensions[2]/4
        ob.location = (0, 0, -offset)

        # setting the origin to cursor(which is on (0,0,0)), now the object origin matches blender's algorithm
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')

        # restore object location and rotation
        ob.location = save_location
        ob.rotation_euler = saved_rot

        # and move it on local Z by the positive offset to restore the original location
        bpy.ops.transform.translate(
            value=(0, 0, offset), orient_axis_ortho='X', orient_type='LOCAL')

        # restore cursor location
        bpy.context.scene.cursor.location = cursor_loc

    return Vector(ob.location), Euler(ob.rotation_euler)


def fix_cone_origin_and_save_location_rotation_special(ob):
    """
    same as above except this one is for FixAppliedRotation class
    this is because in it we're flipping the cone by 180 degrees on Y so we have to flip the offset aswell
    """

    if ob.location == Vector((0, 0, 0)):

        # set origin to generate a location for the object in case the location isn't true (0,0,0) but rather applied
        bpy.ops.object.origin_set(
            type='ORIGIN_CENTER_OF_VOLUME', center='MEDIAN')

        # saving the rotation and setting it to 0 so the object would be moved on Z axis properly
        saved_rot = Euler(ob.rotation_euler)
        ob.rotation_euler = (0, 0, 0)

        # save cursor location and set it to (0,0,0)
        cursor_loc = Vector(bpy.context.scene.cursor.location)
        bpy.context.scene.cursor.location = (0, 0, 0)

        # setting origin to center of volume, this offsets the usual origin when the object is first made so we have to tweak it to match the original
        bpy.ops.object.origin_set(
            type='ORIGIN_CENTER_OF_VOLUME', center='MEDIAN')
        save_location = Vector(ob.location)

        # offsetting the object on Z by the positive offset
        offset = ob.dimensions[2]/4
        ob.location = (0, 0, offset)

        # setting the origin to cursor(which is on (0,0,0)), now the object origin matches blender's algorithm
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')

        # restore object location and rotation
        ob.location = save_location
        ob.rotation_euler = saved_rot

        # and move it on local Z by the negative offset to restore the original location
        bpy.ops.transform.translate(
            value=(0, 0, -offset), orient_axis_ortho='X', orient_type='LOCAL')

        # restore cursor location
        bpy.context.scene.cursor.location = cursor_loc

    return Vector(ob.location), Euler(ob.rotation_euler)


def rotate_around_axis_followed_by_euler_rotation(axis, axis_rotation, euler_rotation):
    '''
    used to calculate final rotation done in 2 steps, first rotating on given axis by given radians and then rotating on all three axes,
    we need this to offset the rotation done by the fix rotation operator
    '''

    if axis == 'Z':
        quat1 = Quaternion((0, 0, 1), axis_rotation)
    elif axis == 'X':
        quat1 = Quaternion((1, 0, 0), axis_rotation)
    else:
        quat1 = Quaternion((0, 1, 0), axis_rotation)

    quat2 = euler_rotation.to_quaternion()
    quat_outer_product = quat2 @ quat1

    return quat_outer_product.to_euler()


def calculate_torus_major_segments(ob):
    """
    calculate and return number of torus segments
    """

    # save both and reset to 0, return it to original after
    saved_loc, saved_rot = save_reset_and_apply_transforms(ob)

    bm = bmesh.new()
    bm.from_mesh(ob.data)
    i = 0

    # we need any vert, just setting the first one
    bm.verts.ensure_lookup_table()
    temp_vert = bm.verts[0].co
    temp_vert_Z = round(temp_vert[2], 5)
    temp_distance = round(distance_vec(temp_vert, Vector((0, 0, 0))), 2)

    # basically find the entire circle of vertices with same Z, this is how we get the segments
    # one other caveat, if the minor segments are uneven then there's an extra row of vertices on the inside with same Z value
    # to fix that we're checking that the distance matches the first found distance from (0,0,0)
    # look at https://drive.google.com/file/d/12uINdegB93RPiPTYzLv5-8PSNVTv8J8S/view?usp=sharing
    for v in bm.verts:
        obMat = ob.matrix_world
        current_vert = obMat @ v.co
        if round(current_vert[2], 5) == temp_vert_Z and round(distance_vec(current_vert, Vector((0, 0, 0))), 2) == temp_distance:
            i += 1

    bm.free()

    # restore original object location/rotation
    ob.location = saved_loc
    ob.rotation_euler = saved_rot

    return i


def calculate_sphere_segments(ob):

    # save both and reset to 0, return it to original after
    saved_loc, saved_rot = save_reset_and_apply_transforms(ob)

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
    saved_loc, saved_rot = save_reset_and_apply_transforms(ob)

    bm = bmesh.new()
    bm.from_mesh(ob.data)

    bm.verts.ensure_lookup_table()
    radius = distance_vec(bm.verts[0].co, Vector((0, 0, 0)))

    ob.location = saved_loc
    ob.rotation_euler = saved_rot
    bm.free()

    return radius


def is_cone_cylindrical(ob):

    # save both and reset to 0, return it to original after
    saved_loc, saved_rot = save_reset_and_apply_transforms(ob)

    # enter edit mode, fill faces if necessary
    bpy.ops.object.editmode_toggle()
    was_filled, total_faces, difference = fill_face_if_non_manifold(ob)
    bm = bmesh.from_edit_mesh(ob.data)

    # initialize
    points_top = []
    points_bottom = []
    i = 0
    top_vert = 0

    # this loop tells us if there are more points than 1 on either side, from that we can find out if the radius should be 0 or more
    for v in bm.verts:

        current_vert = v.co
        # only do this at the start of the loop, remember the first vert, we'll decide whether it's part of top or bottom in the next part
        if i == 0:
            temp_vert_Z = round(current_vert[2], 5)
            temp_vert = current_vert
            i += 1
            continue

        if i == 1:
            # if the second vert has bigger Z value than the temp_vert we'll assign temp vert as top one
            if round(current_vert[2], 5) < temp_vert_Z:

                points_top.append(temp_vert)
                top_vert = round(temp_vert[2], 5)
                # also append the current vert to bottom
                points_bottom.append(current_vert)

            # if the second vert Z value is same as the first vert we found then it means the other side has only 1 vert, this is just how blender orders verts
            # example [(0,0,-1),(0,1,-1),.............,(0,1,1)]
            elif round(current_vert[2], 5) == temp_vert_Z:

                points_top.append(current_vert)
                points_top.append(temp_vert)
                top_vert = temp_vert_Z

                # adding the last vert because we're breaking the loop here
                bm.verts.ensure_lookup_table()
                last_vert = bm.verts[len(bm.verts)-1]
                points_bottom.append(last_vert.co)
                # also switching the arrays if necessary
                if round(last_vert.co[2], 5) > temp_vert_Z:
                    top_vert = round(last_vert.co[2], 5)
                    temp_array = points_top
                    points_top = points_bottom
                    points_bottom = temp_array
                break

            # otherwise do the opposite from the first if
            else:

                points_top.append(current_vert)
                top_vert = round(current_vert[2], 5)
                # also append the temp vert to bottom
                points_bottom.append(temp_vert)
            i += 1
            continue

        # if the current vert Z axis value is same as the one we initialized as top -> append it to top_points
        if round(current_vert[2], 5) == top_vert:
            points_top.append(current_vert)

        # otherwise append it to bottom
        else:
            points_bottom.append(current_vert)

        # if we found more than 1 for each side then we can just exit
        if len(points_bottom) > 1 and len(points_top) > 1:
            break

    # delete the cap if it didn't have one
    if was_filled:

        bm.faces.ensure_lookup_table()
        bm.faces[total_faces-1].select_set(True)
        # if we added 2 faces delete it aswell
        if difference == 2:
            bm.faces[total_faces-2].select_set(True)

        bpy.ops.mesh.delete(type='FACE')

    # restore location and rotation
    ob.location = saved_loc
    ob.rotation_euler = saved_rot
    bpy.ops.object.editmode_toggle()
    bm.free()

    return len(points_bottom) > 1 and len(points_top) > 1


def calculate_cone_radiuses(ob):

    # save both and reset to 0, return it to original after
    saved_loc, saved_rot = save_reset_and_apply_transforms(ob)

    # enter edit mode, fill faces if necessary
    bpy.ops.object.editmode_toggle()
    was_filled, total_faces, difference = fill_face_if_non_manifold(ob)
    bm = bmesh.from_edit_mesh(ob.data)

    # initialize
    points_top = []
    points_bottom = []
    i = 0
    top_vert = 0

    # this loop tells us if there are more points than 1 on either side, from that we can find out if the radius should be 0 or more
    for v in bm.verts:

        current_vert = v.co
        # only do this at the start of the loop, remember the first vert, we'll decide whether it's part of top or bottom in the next part
        if i == 0:
            temp_vert_Z = round(current_vert[2], 5)
            temp_vert = current_vert
            i += 1
            continue

        if i == 1:
            # if the second vert has bigger Z value than the temp_vert we'll assign temp vert as top one
            if round(current_vert[2], 5) < temp_vert_Z:

                points_top.append(temp_vert)
                top_vert = round(temp_vert[2], 5)
                # also append the current vert to bottom
                points_bottom.append(current_vert)

            # if the second vert Z value is same as the first vert we found then it means the other side has only 1 vert, this is just how blender orders verts
            # example [(0,0,-1),(0,1,-1),.............,(0,1,1)]
            elif round(current_vert[2], 5) == temp_vert_Z:

                points_top.append(current_vert)
                points_top.append(temp_vert)
                top_vert = temp_vert_Z

                # adding the last vert because we're breaking the loop here
                bm.verts.ensure_lookup_table()
                last_vert = bm.verts[len(bm.verts)-1]
                points_bottom.append(last_vert.co)
                # also switching the arrays if necessary
                if round(last_vert.co[2], 5) > temp_vert_Z:
                    top_vert = round(last_vert.co[2], 5)
                    temp_array = points_top
                    points_top = points_bottom
                    points_bottom = temp_array
                break

            # otherwise do the opposite from the first if
            else:

                points_top.append(current_vert)
                top_vert = round(current_vert[2], 5)
                # also append the temp vert to bottom
                points_bottom.append(temp_vert)
            i += 1
            continue

        # if the current vert Z axis value is same as the one we initialized as top -> append it to top_points
        if round(current_vert[2], 5) == top_vert:
            points_top.append(current_vert)

        # otherwise append it to bottom
        else:
            points_bottom.append(current_vert)

        # if we found more than 1 for each side then we can just exit
        if len(points_bottom) > 1 and len(points_top) > 1:
            break

    # CASE 1 -> Cone has two sides, no tip-------------------------------------------------------------------------
    if len(points_bottom) > 1 and len(points_top) > 1:

        # change selection to vertices select all quads, this gives us the edge verts on each side of the cone
        bpy.context.tool_settings.mesh_select_mode = (True, False, False)
        bpy.ops.mesh.select_face_by_sides(number=4, type='EQUAL')
        selected_verts = [v for v in bm.verts if v.select]

        if selected_verts[0].co[2] < selected_verts[1].co[2]:
            top_radius = calculate_polygon_radius(
                len(selected_verts)/2, selected_verts[1].co, selected_verts[3].co)
            bottom_radius = calculate_polygon_radius(
                len(selected_verts)/2, selected_verts[0].co, selected_verts[2].co)
        else:
            top_radius = calculate_polygon_radius(
                len(selected_verts)/2, selected_verts[0].co, selected_verts[2].co)
            bottom_radius = calculate_polygon_radius(
                len(selected_verts)/2, selected_verts[1].co, selected_verts[3].co)

    # CASE 2 -> Cone has a tip------------------------------------------------------------------------------------
    else:

        # change selection to edges
        bpy.context.tool_settings.mesh_select_mode = (False, True, False)

        # if there is only 1 vertex then it means that side's radius is 0
        if len(points_top) == 1:
            top_radius = 0

        else:

            # selecting the edge verts-----------------------------------------------------------------------------------------------------
            # if the cone is a tetrahedron
            if len(ob.data.vertices) == 4:

                # change selection to verts
                bpy.context.tool_settings.mesh_select_mode = (
                    True, False, False)

                # because of how blender vert sorting works we know that verts [1],[2] and [3] make the top face, if it was bottom they would be [0],[1] and [2]
                bm.verts.ensure_lookup_table()
                bm.verts[1].select_set(True)
                bm.verts[2].select_set(True)
                bm.verts[3].select_set(True)
                selected_verts = [v for v in bm.verts if v.select]
                total_selected_verts = len(selected_verts)

            # if the cone is a tetraehedron with trifan cap(it can also be a pyramid with a quad cap)
            elif len(ob.data.vertices) == 5:

                # change selection to verts
                bpy.context.tool_settings.mesh_select_mode = (
                    True, False, False)

                # select all quads, if something got selected then it was a pyramid with quad cap
                bpy.ops.mesh.select_face_by_sides(number=4, type='EQUAL')
                selected_verts = [v for v in bm.verts if v.select]
                total_selected_verts = len(selected_verts)

                # if nothing got selected it was a tetrahedron with trifan cap
                if len(selected_verts) == 0:

                    # because of how blender vert sorting works we know that [2],[3] and [4] make the top face, if it was bottom it would be [1],[2] and [3]
                    bm.verts.ensure_lookup_table()
                    bm.verts[2].select_set(True)
                    bm.verts[3].select_set(True)
                    bm.verts[4].select_set(True)
                    selected_verts = [v for v in bm.verts if v.select]
                    total_selected_verts = len(selected_verts)

            # in all the other cases we can simply select the sharp edges instead
            else:

                # select all the sharp edges
                bpy.ops.mesh.edges_select_sharp(sharpness=1.5708)
                selected_verts = [v for v in bm.verts if v.select]
                total_selected_verts = len(selected_verts)

                # if nothing got selected from sharp edges it means the cone has no caps
                # in that case just select everything
                if total_selected_verts == 0:

                    # in that case just select everything
                    bpy.ops.mesh.select_all(action='SELECT')
                    selected_verts = [v for v in bm.verts if v.select]
                    # -1 because we selected the tip aswell
                    total_selected_verts = len(selected_verts)-1

            top_radius = calculate_polygon_radius(
                total_selected_verts, selected_verts[0].co, selected_verts[1].co)

        # checking other side now,same process as the above code
        # if there is only 1 vertex then it means that side's radius is 0
        if len(points_bottom) == 1:
            bottom_radius = 0

        else:

            # selecting the edge verts-----------------------------------------------------------------------------------------------------
            # if the cone is a tetrahedron
            if len(ob.data.vertices) == 4:

                # change selection to verts
                bpy.context.tool_settings.mesh_select_mode = (
                    True, False, False)

                # because of how blender vert sorting works we know that [0],[1] and [2] create the bottom face
                bm.verts.ensure_lookup_table()
                bm.verts[0].select_set(True)
                bm.verts[1].select_set(True)
                bm.verts[2].select_set(True)
                selected_verts = [v for v in bm.verts if v.select]
                total_selected_verts = len(selected_verts)

            # if the cone is a tetraehedron with trifan cap(it can also be a pyramid with a quad cap)
            elif len(ob.data.vertices) == 5:

                # change selection to verts
                bpy.context.tool_settings.mesh_select_mode = (
                    True, False, False)

                # select all quads, if something got selected then it was a pyramid with quad cap
                bpy.ops.mesh.select_face_by_sides(number=4, type='EQUAL')
                selected_verts = [v for v in bm.verts if v.select]
                total_selected_verts = len(selected_verts)

                # if nothing got selected it was a tetrahedron with trifan cap
                if len(selected_verts) == 0:

                    # because of how blender vert sorting works we know that [1],[2] and [3] create the bottom face
                    bm.verts.ensure_lookup_table()
                    bm.verts[1].select_set(True)
                    bm.verts[2].select_set(True)
                    bm.verts[3].select_set(True)
                    selected_verts = [v for v in bm.verts if v.select]
                    total_selected_verts = len(selected_verts)

            # in all the other cases we can simply select the sharp edges instead
            else:
                bpy.ops.mesh.edges_select_sharp(sharpness=1.5708)
                selected_verts = [v for v in bm.verts if v.select]
                total_selected_verts = len(selected_verts)

                # if nothing got selected from sharp edges it means the cone has no caps
                if total_selected_verts == 0:

                    # in that case just select everything
                    bpy.ops.mesh.select_all(action='SELECT')
                    selected_verts = [v for v in bm.verts if v.select]

                    # -1 because we selected the tip aswell
                    total_selected_verts = len(selected_verts)-1

            bottom_radius = calculate_polygon_radius(
                total_selected_verts, selected_verts[0].co, selected_verts[1].co)

    # deselect everything
    bpy.ops.mesh.select_all(action='DESELECT')

    # delete the cap if it didn't have one
    if was_filled:

        bm.faces.ensure_lookup_table()
        bm.faces[total_faces-1].select_set(True)
        # if we added 2 faces delete it aswell
        if difference == 2:
            bm.faces[total_faces-2].select_set(True)

        bpy.ops.mesh.delete(type='FACE')

    # restore location and rotation
    ob.location = saved_loc
    ob.rotation_euler = saved_rot
    bpy.ops.object.editmode_toggle()
    bm.free()

    return bottom_radius, top_radius


def calculate_cylinder_radius(ob):

    # save both and reset to 0, return it to original after
    saved_loc, saved_rot = save_reset_and_apply_transforms(ob)

    bm = bmesh.new()
    bm.from_mesh(ob.data)

    # get third vert in case cap was trifan, [0] and [1] are middle ones
    bm.verts.ensure_lookup_table()
    edge_vert = bm.verts[2].co

    # middle point would have the same Z as an edge vert and both X and Y as 0
    middlepoint_top = Vector((0, 0, edge_vert[2]))

    radius = distance_vec(edge_vert, middlepoint_top)

    bm.free()

    # restore original object location/rotation
    ob.location = saved_loc
    ob.rotation_euler = saved_rot

    return radius


def check_if_wrong_circle_rotation(ob):
    """
    checks if the circle has true (0,0,0) rotation by checking how many verts have different Z values
    """

    bm = bmesh.new()
    bm.from_mesh(ob.data)

    # initialize array
    points_with_different_Z = []

    # loop through all the vertices and add each one with new Z
    for v in bm.verts:

        obMat = ob.matrix_world
        current_vert = obMat @ v.co

        if round(current_vert[2], 5) not in points_with_different_Z:
            points_with_different_Z.append(round(current_vert[2], 5))
            # if there's more than 2 vertices with different Z then the object is not correctly rotated
            if len(points_with_different_Z) > 1:
                return True

    bm.free()

    return False


def check_if_wrong_cone_or_cylinder_rotation(ob):
    """
    checks if cone/cylinder have true (0,0,0) rotation by counting if verts have more than 2 different Z values
    """

    bm = bmesh.new()
    bm.from_mesh(ob.data)

    # initialize array
    points_with_different_Z = []

    # loop through all the vertices and add each one with new Z
    for v in bm.verts:

        obMat = ob.matrix_world
        current_vert = obMat @ v.co

        if round(current_vert[2], 5) not in points_with_different_Z:
            points_with_different_Z.append(round(current_vert[2], 5))
            # if there's more than 2 vertices with different Z then the object is not correctly rotated
            if len(points_with_different_Z) > 2:
                return True

    bm.free()
    return False


def check_if_wrong_torus_rotation(ob):
    """
    this function calculates how many verts have different Z values
    if torus is slightly rotated it's gonna have more verts with different [Z] than minor segments
    """

    bm = bmesh.new()
    bm.from_mesh(ob.data)

    # initialize array
    points_with_different_Z = []

    # loop through all the vertices and add each one with new Z
    for v in bm.verts:

        obMat = ob.matrix_world
        current_vert = obMat @ v.co

        if round(current_vert[2], 5) not in points_with_different_Z:
            points_with_different_Z.append(round(current_vert[2], 5))

    bm.free()

    # total polygons=major segments*minor segments
    # minimal number of both segments is 3
    # when this function is called we only know the number of total polygons, not major or minor segments
    # by assuming the worst case scenario which is torus having 3 major segments we can say it has minor segments=polygons/3,
    # this way we're getting maximum possible minor segments and by covering the worst case scenario we cover all of them
    return len(points_with_different_Z) > len(ob.data.polygons)/3


def check_if_wrong_sphere_rotation(ob):
    """
    this function calculates how many verts have different Z values
    if sphere is slightly rotated it's gonna have more verts with different [Z] than rings
    """

    bm = bmesh.new()
    bm.from_mesh(ob.data)

    # initialize array
    points_with_different_Z = []

    # loop through all the vertices and add each one with new Z
    for v in bm.verts:

        obMat = ob.matrix_world
        current_vert = obMat @ v.co
        if round(current_vert[2], 3) not in points_with_different_Z:
            points_with_different_Z.append(round(current_vert[2], 3))

    bm.free()

    # total polygons=segments*rings
    # minimal number of both segments and rings is 3
    # when this function is called we only know the number of total polygons, not segments or rings
    # by assuming the worst case scenario which is sphere having 3 segments we can say it has rings=polygons/3,
    # this way we're getting maximum possible rings and by covering the worst case scenario we cover all of them
    return len(points_with_different_Z)-1 > len(ob.data.polygons)/3, len(points_with_different_Z)-1


def select_smallest_from_selected_faces(faces):

    i = 0
    # loop through all the faces and find the smallest one
    for f in faces:

        if i == 0:
            smallest_face_value = f.calc_area()
            smallest_face = f
            i += 1
            continue
        if f.calc_area() < smallest_face_value:
            smallest_face_value = f.calc_area()
            smallest_face = f

    # deselect everything and select the smallest face
    bpy.ops.mesh.select_all(action='DESELECT')
    smallest_face.select_set(True)


def show_or_hide_modifiers_in_viewport(ob, visibility):
    '''
    modifiers change some object data so we disable them before calculating said data
    '''

    was_changed = False
    for mod in getattr(ob, "modifiers", []):
        # if modifier viewport visibility is different from given visibility
        if mod.show_viewport != visibility:
            mod.show_viewport = visibility
            was_changed = True

    return was_changed


def calculate_z_offset(N):
    '''
    calculates the offset necessary to match the rotation after using fix rotation operator
    it is equal to the interior angle between two sides divided by -2
    look at https://drive.google.com/file/d/1FCij1TjPVtvxHkxPpxW_ekRujkDkQivQ/view?usp=sharing
    '''

    interior_angles = pi-(2*pi/N)
    z_offset = -interior_angles/2

    return z_offset


def copy_modifiers_and_delete_original(original_ob, new_ob, name):

    # make the original object active
    bpy.context.view_layer.objects.active = original_ob

    # copy modifiers from active object(original) to the newly created object
    # new object has to be added prior to this(currently selected)
    bpy.ops.object.make_links_data(type='MODIFIERS')

    # deselect everything and select original object, then delete it
    bpy.ops.object.select_all(action='DESELECT')
    original_ob.select_set(True)
    bpy.ops.object.delete()

    # select the newly created object
    new_ob.select_set(True)
    bpy.context.view_layer.objects.active = new_ob

    # rename the new object to match the original
    new_ob.name = name

    return


def select_unique_faces(ob):
    '''
    selects faces that appear only once or twice, otherwise just select the first one
    '''

    bm = bmesh.from_edit_mesh(ob.data)
    faces = bm.faces
    different_faces = dict()

    for f in faces:
        area = round(f.calc_area(), 4)
        if area in different_faces:
            different_faces[area][0] += 1
            different_faces[area][1].append(f)
        else:
            different_faces[area] = [1, [f]]

    unique_faces = []
    for area in different_faces.keys():
        if different_faces[area][0] <= 2:
            unique_faces.extend(different_faces[area][1])

    total_unique_faces = len(unique_faces)

    # deselect everything and select unique faces
    # if we didn't find any unique faces just select the first face
    bpy.ops.mesh.select_all(action='DESELECT')
    faces.ensure_lookup_table()
    if total_unique_faces == 0:
        faces[0].select_set(True)
        return
    if total_unique_faces > 1:
        unique_faces[0].select_set(True)
        unique_faces[1].select_set(True)
    else:
        unique_faces[0].select_set(True)


def select_rotational_cylinder(ob):
    """
    select or create faces that are needed to properly rotate the cone
    """

    # change selection to faces
    bpy.context.tool_settings.mesh_select_mode = (False, False, True)

    was_filled, total_faces, difference = fill_face_if_non_manifold(ob)
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
        bpy.ops.mesh.select_similar(type='COPLANAR', threshold=0.01)

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


def select_rotational_cone(ob):
    """
    select or create faces that are needed to properly rotate the cone
    """
    # change selection to faces
    bpy.context.tool_settings.mesh_select_mode = (False, False, True)

    was_filled, total_faces, difference = fill_face_if_non_manifold(ob)
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
            shared_distance = round(distance_vec(
                current_vert, Vector((0, 0, 0))), 4)
            v.select = True
            i += 1
            continue

        if round(distance_vec(current_vert, Vector((0, 0, 0))), 4) == shared_distance:
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

# individual functions that replace the current mesh with a new one that looks the same-----------------------------------------------------------------


def replace_circle(vertices, radius, cap_fill, location, rotation, align, b_UV):

    # original object reference
    original_ob = bpy.context.active_object

    if align != "WORLD":
        bpy.ops.mesh.primitive_circle_add(vertices=vertices, radius=radius, fill_type=cap_fill, location=location, calc_uvs=b_UV,
                                          align=align)
    else:
        bpy.ops.mesh.primitive_circle_add(vertices=vertices, radius=radius, fill_type=cap_fill, location=location, rotation=rotation,
                                          calc_uvs=b_UV)

    # new object reference
    new_ob = bpy.context.active_object

    copy_modifiers_and_delete_original(
        original_ob, new_ob, original_ob.name)


def replace_cone(vertices, radius1, radius2, depth, cap_fill, location, rotation, align, b_UV):

    # original object reference
    original_ob = bpy.context.active_object

    # add a new object that matches the original object
    if align != "WORLD":

        bpy.ops.mesh.primitive_cone_add(end_fill_type=cap_fill, depth=depth, radius1=radius1, radius2=radius2, vertices=vertices,
                                        location=location, calc_uvs=b_UV, align=align)
    else:
        bpy.ops.mesh.primitive_cone_add(end_fill_type=cap_fill, depth=depth, radius1=radius1, radius2=radius2, vertices=vertices,
                                        location=location, calc_uvs=b_UV, rotation=rotation)

    # new object reference
    new_ob = bpy.context.active_object

    copy_modifiers_and_delete_original(
        original_ob, new_ob, original_ob.name)


def replace_cylinder(vertices, radius, depth, cap_fill, location, rotation, align, b_UV):

    # original object reference
    original_ob = bpy.context.active_object

    if align != "WORLD":
        bpy.ops.mesh.primitive_cylinder_add(end_fill_type=cap_fill, depth=depth, radius=radius, vertices=vertices, location=location,
                                            calc_uvs=b_UV, align=align)
    else:
        bpy.ops.mesh.primitive_cylinder_add(
            end_fill_type=cap_fill, depth=depth, radius=radius, vertices=vertices, location=location, rotation=rotation, calc_uvs=b_UV)

    # new object reference
    new_ob = bpy.context.active_object

    copy_modifiers_and_delete_original(
        original_ob, new_ob, original_ob.name)


def replace_icosphere(subdivisions, radius, location, rotation, align, b_UV):

    # original object reference
    original_ob = bpy.context.active_object

    if align != "WORLD":
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=subdivisions, radius=radius, location=location, calc_uvs=b_UV, align=align)
    else:
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=radius, location=location, rotation=rotation,
                                              calc_uvs=b_UV)

    # new object reference
    new_ob = bpy.context.active_object

    copy_modifiers_and_delete_original(
        original_ob, new_ob, original_ob.name)


def replace_torus(major_segments, minor_segments, major_radius, minor_radius, location, rotation, align, b_UV):

    # original object reference
    original_ob = bpy.context.active_object

    if align != "WORLD":
        bpy.ops.mesh.primitive_torus_add(major_segments=major_segments, minor_segments=minor_segments, location=location,
                                         major_radius=major_radius, minor_radius=minor_radius, generate_uvs=b_UV, align=align)
    else:
        bpy.ops.mesh.primitive_torus_add(major_segments=major_segments, minor_segments=minor_segments, location=location,
                                         major_radius=major_radius, minor_radius=minor_radius, generate_uvs=b_UV, rotation=rotation)

    # new object reference
    new_ob = bpy.context.active_object

    copy_modifiers_and_delete_original(
        original_ob, new_ob, original_ob.name)


def replace_uv_sphere(segments, rings, radius, location, rotation, align, b_UV):

    # original object reference
    original_ob = bpy.context.active_object

    if align != "WORLD":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=radius, location=location, calc_uvs=b_UV,
                                             align=align)
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=radius, location=location, rotation=rotation,
                                             calc_uvs=b_UV)

    # new object reference
    new_ob = bpy.context.active_object

    copy_modifiers_and_delete_original(
        original_ob, new_ob, original_ob.name)


def calculate_sides(ob):

    total_faces = len(ob.data.polygons)
    total_vertices = len(ob.data.vertices)
    sides = 0
    group = 0

    if ob.data.name.startswith('Cylinder'):
        group = 1
        if total_faces == (total_vertices/2)+2 or total_faces == total_vertices/2:
            sides = total_vertices/2
        else:
            sides = total_vertices-2/2

    elif ob.data.name.startswith('Circle'):
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

    elif ob.data.name.startswith('Cone'):
        group = 1

        # first rotate it by 180 on Y axis because it will be flipped
        ob.rotation_euler = Euler((0, pi, 0))
        bpy.ops.object.transform_apply(
            location=False, rotation=True, scale=False)

        # find out if cone is cylinderlike
        radius1, radius2 = calculate_cone_radiuses(ob)
        cylindrical = False
        if radius1 > 0 and radius2 > 0:
            cylindrical = True

        # if both top and bottom radius are not zero we have to divide vertices with 2
        if cylindrical:

            if total_faces == total_vertices/2+2 or total_faces == total_vertices/2:
                sides = total_vertices/2
            else:
                sides = total_vertices/2-1

        # one side has radius 0
        else:

            if total_faces == total_vertices or total_faces == total_vertices-1:
                sides = total_vertices-1
            else:
                sides = total_vertices-2

    elif ob.data.name.startswith('Sphere'):
        group = 1
        sides = calculate_sphere_segments(ob)

    elif ob.data.name.startswith('Torus'):
        group = 2
        sides = calculate_torus_major_segments(ob)

    elif ob.data.name.startswith('Icosphere'):
        group = 3

    return sides, group


def Z_offset_ob(ob):
    '''
    rotate object on Z so it matches blender default rotation
    '''

    # we have to know how many sides object has and which group it belongs to
    sides, group = calculate_sides(ob)

    # circle, cone, UVSphere and cylinder
    if group == 1:

        # we don't have to fix the rotation if edges go through Y axis by default
        if (sides-2) % 4 != 0:

            # if uneven we can just rotate on Z by 90 degrees
            if sides % 2 != 0:
                ob.rotation_euler = Euler((0, 0, -pi/2))

            # otherwise we have to calculate the angle between sides and divide it with -2
            else:
                z_offset = calculate_z_offset(sides)
                ob.rotation_euler = Euler((0, 0, -z_offset))

    # torus
    elif group == 2:

        # if you were to cut torus on both X and Y and the quarter piece you get was symmetrical to itself
        if sides % 4 == 0:
            z_offset = calculate_z_offset(sides)
            ob.rotation_euler = Euler((0, 0, -z_offset))

        # if torus is symmetrical on both X and Y but the quarter piece isn't symmetrical
        elif sides % 2 == 0:
            ob.rotation_euler = Euler((0, 0, -pi/2))

        # if torus is only symmetrical on 1 axis
        else:
            ob.rotation_euler = Euler((0, 0, -pi))

    # icosphere
    elif group == 3:

        # unlike other objects icosphere only needs to be rotated on Z for 180
        ob.rotation_euler = Euler((0, 0, -pi))

    # do nothing if object doesn't belong to a group
    else:
        return


def smart_selection(ob):
    """
    function that selects the necessary face in order to rotate the object properly
    """

    if ob.data.name.startswith('Sphere'):

        # select all quads invert the selection,we get the top and bottom vert
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

    elif ob.data.name.startswith('Cylinder'):

        select_rotational_cylinder(ob)

    elif ob.data.name.startswith('Torus'):

        insert_middle_face_torus(ob)

    elif ob.data.name.startswith('Circle'):

        # count number of current faces
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

    elif ob.data.name.startswith('Cone'):

        select_rotational_cone(ob)

    elif ob.data.name.startswith('Icosphere'):

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
