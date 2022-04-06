import bpy

from .core import *
from math import log, pi
from bpy.types import Operator
from bpy.props import BoolProperty, IntProperty, EnumProperty, FloatProperty
from mathutils import Vector, Euler


class RePrimitive(Operator):
    """
    Main reprimitive operator, it decides which other operator gets called
    """
    bl_idname = "object.reprimitive"
    bl_label = "Tweak Primitives"
    bl_description = "Tweak Primitives"
    bl_options = {'REGISTER', 'UNDO'}

    # can only be called on specific named objects and in object mode
    @classmethod
    def poll(cls, context):
        allowed_objects = ['Cone', 'Circle', 'Torus',
                           'Cylinder', 'Sphere', 'Icosphere', '锥体', '圆环', '环体', '柱体', '球体', '棱角球']
        return any(map(context.active_object.data.name.startswith, allowed_objects)) and bpy.context.mode == 'OBJECT'

    def execute(self, context):

        if context.active_object.data.name.startswith(('Cylinder', '柱体')):
            bpy.ops.object.reprimitive_cylinder('INVOKE_DEFAULT')
        elif context.active_object.data.name.startswith(('Cone', '锥体')):
            bpy.ops.object.reprimitive_cone('INVOKE_DEFAULT')
        elif context.active_object.data.name.startswith(('Circle', '圆环')):
            bpy.ops.object.reprimitive_circle('INVOKE_DEFAULT')
        elif context.active_object.data.name.startswith(('Torus', '环体')):
            bpy.ops.object.reprimitive_torus('INVOKE_DEFAULT')
        elif context.active_object.data.name.startswith(('Sphere', '球体')):
            bpy.ops.object.reprimitive_sphere('INVOKE_DEFAULT')
        elif context.active_object.data.name.startswith(('Icosphere', '棱角球')):
            bpy.ops.object.reprimitive_icosphere('INVOKE_DEFAULT')
        return {'FINISHED'}


class RePrimitiveCircle(Operator):
    """
    Tweak circle operator
    """
    bl_idname = "object.reprimitive_circle"
    bl_label = "Tweak Circle"
    bl_options = {'REGISTER', 'UNDO', 'PRESET', 'INTERNAL'}

    # create default values
    saved_object_location = Vector((0, 0, 0))
    saved_object_rotation = Euler((0, 0, 0))

    Y = 0
    radius = 1
    vertices = 32
    cap_type = 'NGON'
    align_type = 'WORLD'
    b_UV = True

    # properties
    vertices: IntProperty(
        name="",
        default=vertices,
        soft_min=3,
        soft_max=500,
        min=3,
        max=500)
    cap_fill: EnumProperty(
        name="",
        description="Select an option",
        items=[('NOTHING', "Nothing", "Don't fill at all"),
               ('NGON', "N-Gon", "Use n-gons"),
               ('TRIFAN', "Triangle Fan", "Use triangle fans")],
        default=cap_type)
    radius: FloatProperty(
        name="",
        default=radius,
        soft_min=0.001,
        min=0)
    b_UV: BoolProperty(
        name="Generate UVs",
        default=b_UV)
    align: EnumProperty(
        name="",
        description="Select an option",
        items=[('WORLD', "World", "Align the new object to the world"),
               ('VIEW', "View", "Align the new object to the view"),
               ('CURSOR', "3D Cursor", "Use the 3d cursor orientation for the new object")],
        default=align_type)

    def draw(self, context):

        layout = self.layout
        split = layout.split(factor=0.3)

        col_1 = split.column()
        col_2 = split.column()

        col_1.label(text="Vertices")
        col_2.prop(self, "vertices")

        col_1.label(text="Radius")
        col_2.prop(self, "radius")

        col_1.label(text="Base Fill Type")
        col_2.prop(self, "cap_fill")

        col_1.label(text="")
        col_2.prop(self, "b_UV")

        col_1.label(text="Align")
        col_2.prop(self, "align")

    def modal(self, context, event):
        return {'FINISHED'}

    def invoke(self, context, event):

        applied_rotation = False

        # before any calculations are done we first hide modifiers in the viewport
        modifiers_changed = show_or_hide_modifiers_in_viewport(
            context.active_object, False)

        # save location and rotation
        self.saved_object_location, self.saved_object_rotation = save_location_rotation(
            context.active_object)
        self.align = "WORLD"

        # first we'll check if the rotation is (0,0,0) to skip the next check
        if context.active_object.rotation_euler == Euler((0, 0, 0)):
            # check if rotation is applied, because functions won't work
            if check_if_wrong_circle_rotation(context.active_object):

                # if the rotation was applied we fix it so it's truly (0,0,0)
                applied_rotation = True
                bpy.ops.object.fix_applied_rotation_auto()

                # set object rotation to cube rotation
                self.saved_object_rotation = Euler(
                    context.scene.objects["if_you==girl_AND_you==READING_THIS_AND_you==SINGLE_THEN_DM_ME"].rotation_euler)
                context.active_object.rotation_euler = self.saved_object_rotation

                # delete the super secret cube
                cube_to_delete = bpy.data.objects["if_you==girl_AND_you==READING_THIS_AND_you==SINGLE_THEN_DM_ME"]
                bpy.data.objects.remove(cube_to_delete, do_unlink=True)

        # calculate variables
        if(len(context.active_object.data.polygons)) == 0:
            self.cap_type = 'NOTHING'
        elif(len(context.active_object.data.polygons)) == 1:
            self.cap_type = 'NGON'
        else:
            self.cap_type = 'TRIFAN'

        if self.cap_type == 'TRIFAN':
            self.vertices = int(len(context.active_object.data.vertices)-1)
        else:
            self.vertices = int(len(context.active_object.data.vertices))

        self.radius = calculate_circle_radius(context.active_object)
        if not context.object.data.uv_layers:
            self.b_UV = False

        # apply cap fill settings if they're different from the enum option drop
        if self.cap_type != self.cap_fill:
            self.cap_fill = self.cap_type

        # after we're done we unhide modifiers in the viewport if they weren't hidden
        if modifiers_changed:
            show_or_hide_modifiers_in_viewport(context.active_object, True)

        # we don't have to fix the rotation if verts go through Y axis by default
        if applied_rotation and (self.vertices-2) % 4 != 0:

            # if uneven we can just rotate on Z by 90 degrees
            if self.vertices % 2 != 0:
                self.saved_object_rotation = rotate_around_axis_followed_by_euler_rotation(
                    'Z', pi/2, self.saved_object_rotation)

            # otherwise we have to calculate the angle between sides and divide it with -2
            else:
                z_offset = calculate_z_offset(self.vertices)
                self.saved_object_rotation = rotate_around_axis_followed_by_euler_rotation(
                    'Z', z_offset, self.saved_object_rotation)

            # if the user invokes the operator but doesn't do anything and clicks away instead of pressing ok-> execute doesn't go off
            # we're force calling execute to fix the rotation
            self.execute(context)

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):

        replace_circle(self.vertices, self.radius, self.cap_fill,
                       self.saved_object_location, self.saved_object_rotation, self.align, self.b_UV)

        return {'FINISHED'}


class RePrimitiveCone(Operator):
    """
    Tweak cone operator
    """
    bl_idname = "object.reprimitive_cone"
    bl_label = "Tweak Cone"
    bl_options = {'REGISTER', 'UNDO', 'PRESET', 'INTERNAL'}

    # create default values
    applied_rotation_and_location = False
    saved_object_location = Vector((0, 0, 0))
    saved_object_rotation = Euler((0, 0, 0))
    Y = 0
    depth = 2
    radius1 = 1
    radius2 = 0
    vertices = 32
    cap_type = 'NGON'
    align_type = 'WORLD'
    b_UV = True

    # properties
    vertices: IntProperty(
        name="",
        default=vertices,
        soft_min=3,
        soft_max=500,
        min=3,
        max=500)
    depth: FloatProperty(
        name="",
        default=depth,
        soft_min=0.001)
    cap_fill: EnumProperty(
        name="",
        description="Select an option",
        items=[('NOTHING', "Nothing", "Don't fill at all"),
               ('NGON', "N-Gon", "Use n-gons"),
               ('TRIFAN', "Triangle Fan", "Use triangle fans")],
        default=cap_type)
    radius1: FloatProperty(
        name="",
        default=radius1,
        soft_min=0,
        min=0)
    radius2: FloatProperty(
        name="",
        default=radius2,
        soft_min=0,
        min=0)
    b_UV: BoolProperty(
        name="Generate UVs",
        default=b_UV)
    align: EnumProperty(
        name="",
        description="Select an option",
        items=[('WORLD', "World", "Align the new object to the world"),
               ('VIEW', "View", "Align the new object to the view"),
               ('CURSOR', "3D Cursor", "Use the 3d cursor orientation for the new object")],
        default=align_type)

    def draw(self, context):

        layout = self.layout
        split = layout.split(factor=0.3)

        col_1 = split.column()
        col_2 = split.column()

        col_1.label(text="Vertices")
        col_2.prop(self, "vertices")

        col_1.label(text="Radius 1")
        col_2.prop(self, "radius1")

        col_1.label(text="Radius 2")
        col_2.prop(self, "radius2")

        col_1.label(text="Depth")
        col_2.prop(self, "depth")

        col_1.label(text="Base Fill Type")
        col_2.prop(self, "cap_fill")

        col_1.label(text="")
        col_2.prop(self, "b_UV")

        col_1.label(text="Align")
        col_2.prop(self, "align")

    def modal(self, context, event):
        return {'FINISHED'}

    def invoke(self, context, event):

        applied_rotation = False
        was_filled = False

        # before any calculations are done we first hide modifiers in the viewport
        modifiers_changed = show_or_hide_modifiers_in_viewport(
            context.active_object, False)

        # first we'll check if the rotation is (0,0,0) to skip the next check
        if context.active_object.rotation_euler == Euler((0, 0, 0)):
            # check if rotation is applied, because functions won't work
            if check_if_wrong_cone_or_cylinder_rotation(context.active_object):

                applied_rotation = True
                # if the location was possibly applied aswell then we have to fix it first
                # usually we don't have to do this because we're doing the location first, but with cone we need to know the rotation first
                # or we can't fix the location
                if context.active_object.location == Vector((0, 0, 0)):

                    # if cone is not manifold, origin to center of volume won't work, so we're filling in the face
                    bpy.ops.object.editmode_toggle()
                    was_filled, total_faces, difference = fill_face_if_non_manifold(
                        context.active_object)
                    bpy.ops.object.editmode_toggle()

                    bpy.ops.object.origin_set(
                        type='ORIGIN_CENTER_OF_VOLUME', center='MEDIAN')
                    self.applied_rotation_and_location = True

                # if the rotation was applied we fix it so it's truly (0,0,0)
                bpy.ops.object.fix_applied_rotation_auto()

                # the above function also spawns a cube that we use to reapply the rotation as it was before fixing but this time it won't be (0,0,0)
                self.saved_object_rotation = Euler(
                    context.scene.objects["if_you==girl_AND_you==READING_THIS_AND_you==SINGLE_THEN_DM_ME"].rotation_euler)
                context.active_object.rotation_euler = self.saved_object_rotation

                # delete the super secret cube
                cube_to_delete = bpy.data.objects["if_you==girl_AND_you==READING_THIS_AND_you==SINGLE_THEN_DM_ME"]
                bpy.data.objects.remove(cube_to_delete, do_unlink=True)

        # if we added a cap, delete the last 2 or 1 depending on cone shape
        if was_filled:

            bpy.ops.object.editmode_toggle()
            bm = bmesh.from_edit_mesh(context.active_object.data)
            bm.faces.ensure_lookup_table()
            bm.faces[total_faces-1].select_set(True)
            if difference == 2:
                bm.faces[total_faces-2].select_set(True)
            bpy.ops.mesh.delete(type='FACE')
            bpy.ops.object.editmode_toggle()
            was_filled = False

        self.radius1, self.radius2 = calculate_cone_radiuses(
            context.active_object)

        cylindrical = False
        if self.radius1 > 0 and self.radius2 > 0:
            cylindrical = True

        # if the cone is cylindrical then we can use the usual function that uses origin to geometry
        if cylindrical:

            if self.applied_rotation_and_location:
                # in this case we already fixed the origin but it's wrong for cylindrical cones
                bpy.ops.object.origin_set(
                    type='ORIGIN_GEOMETRY', center='MEDIAN')

            self.applied_rotation_and_location = False
            self.saved_object_location, self.saved_object_rotation = save_location_rotation(
                context.active_object)

        # if cone has a sharp tip, origin to geometry won't work so we do this instead
        else:

            # if cone is not manifold origin to center of volume won't work, so we're filling in the face
            if context.active_object.location == Vector((0, 0, 0)):
                bpy.ops.object.editmode_toggle()
                was_filled, total_faces, difference = fill_face_if_non_manifold(
                    context.active_object)
                bpy.ops.object.editmode_toggle()

            # look at https://drive.google.com/file/d/1dJnHe81WgO4eUJY4xyjoTFJi5n8h79we/view?usp=sharing
            # bottom radius is zero, so origin to center of volume is above where it should be which means when location is reset to (0,0,0) the object will be lower
            # so we're moving the object up
            if self.radius1 == 0:
                self.saved_object_location, self.saved_object_rotation = fix_cone_origin_and_save_location_rotation_positive(
                    context.active_object)

            # top radius is zero, so origin to center of volume is below where it should be which means when location is reset to (0,0,0) the object will be higher
            # so we're moving the object down
            else:
                self.saved_object_location, self.saved_object_rotation = fix_cone_origin_and_save_location_rotation_negative(
                    context.active_object)

        # if we added a cap, delete the last 2 or 1 depending on cone shape
        if was_filled:
            bpy.ops.object.editmode_toggle()
            bm = bmesh.from_edit_mesh(context.active_object.data)
            bm.faces.ensure_lookup_table()
            bm.faces[total_faces-1].select_set(True)
            if difference == 2:
                bm.faces[total_faces-2].select_set(True)
            bpy.ops.mesh.delete(type='FACE')
            bpy.ops.object.editmode_toggle()

        # calculate variables
        self.align = "WORLD"
        self.Y = context.object.dimensions[1]
        self.depth = context.object.dimensions[2]
        if not context.object.data.uv_layers:
            self.b_UV = False

        # if both top and bottom radius are not zero we have to divide vertices with 2
        if cylindrical:

            if len(context.object.data.polygons) == len(context.object.data.vertices)/2+2:
                self.vertices = int(len(context.object.data.vertices)/2)
                self.cap_type = 'NGON'

            elif len(context.object.data.polygons) == len(context.object.data.vertices)/2:
                self.vertices = int(len(context.object.data.vertices)/2)
                self.cap_type = 'NOTHING'
            else:
                self.vertices = int(len(context.object.data.vertices)/2-1)
                self.cap_type = 'TRIFAN'
        elif self.radius1 == 0 and self.radius2 == 0:

            # special case for when both radiuses are 0, base fill type would change to triangle fan otherwise because there's only 3 verts
            # not much i can do here except just set it so it's an NGON cause that's the most used one anyway
            self.cap_type = 'NGON'

        # one side has radius 0
        else:

            if len(context.object.data.polygons) == len(context.object.data.vertices):
                self.vertices = int(len(context.object.data.vertices)-1)
                self.cap_type = 'NGON'
            elif len(context.object.data.polygons) == len(context.object.data.vertices)-1:
                self.vertices = int(len(context.object.data.vertices)-1)
                self.cap_type = 'NOTHING'
            else:
                self.vertices = int(len(context.object.data.vertices)-2)
                self.cap_type = 'TRIFAN'

        # apply cap fill settings if they're different from the enum option drop
        if self.cap_type != self.cap_fill:
            self.cap_fill = self.cap_type

        # after we're done we unhide modifiers in the viewport if they weren't hidden
        if modifiers_changed:
            show_or_hide_modifiers_in_viewport(context.active_object, True)

        # we don't have to fix the rotation if edges go through Y axis by default
        if applied_rotation and (self.vertices-2) % 4 != 0:

            # if uneven we can just rotate on Z by 90 degrees
            if self.vertices % 2 != 0:
                self.saved_object_rotation = rotate_around_axis_followed_by_euler_rotation(
                    'Z', pi/2, self.saved_object_rotation)

            # otherwise we have to calculate the angle between sides and divide it with -2
            else:
                z_offset = calculate_z_offset(self.vertices)
                self.saved_object_rotation = rotate_around_axis_followed_by_euler_rotation(
                    'Z', z_offset, self.saved_object_rotation)

        # if the user invokes the operator but doesn't do anything and clicks away instead of pressing ok-> execute doesn't go off
        # we're force calling execute to fix the location and rotation
        if applied_rotation or self.applied_rotation_and_location:

            self.execute(context)

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):

        replace_cone(self.vertices, self.radius1, self.radius2, self.depth, self.cap_fill,
                     self.saved_object_location, self.saved_object_rotation, self.align, self.b_UV)

        # fix the location if both rotation and location were applied
        if self.applied_rotation_and_location:
            bpy.ops.transform.translate(
                value=(0, 0, -self.depth/4), orient_axis_ortho='X', orient_type='LOCAL')

        return {'FINISHED'}


class RePrimitiveCylinder(Operator):
    """
    Tweak cylinder operator
    """
    bl_idname = "object.reprimitive_cylinder"
    bl_label = "Tweak Cylinder"
    bl_options = {'REGISTER', 'UNDO', 'PRESET', 'INTERNAL'}

    # create default values
    saved_object_location = Vector((0, 0, 0))
    saved_object_rotation = Euler((0, 0, 0))
    Y = 0
    depth = 2
    radius = 1
    vertices = 32
    cap_type = 'NGON'
    align_type = 'WORLD'
    b_UV = True

    # properties
    vertices: IntProperty(
        name="",
        default=vertices,
        soft_min=3,
        soft_max=500,
        min=3,
        max=500)
    depth: FloatProperty(
        name="",
        default=depth,
        soft_min=0.001,
        min=0)
    cap_fill: EnumProperty(
        name="", description="Select an option",
        items=[('NOTHING', "Nothing", "Don't fill at all"),
               ('NGON', "N-Gon", "Use n-gons"),
               ('TRIFAN', "Triangle Fan", "Use triangle fans")],
        default=cap_type)
    radius: FloatProperty(
        name="", default=radius, soft_min=0.001, min=0)
    b_UV: BoolProperty(
        name="Generate UVs",
        default=b_UV)
    align: EnumProperty(
        name="",
        description="Select an option",
        items=[('WORLD', "World", "Align the new object to the world"),
               ('VIEW', "View", "Align the new object to the view"),
               ('CURSOR', "3D Cursor", "Use the 3d cursor orientation for the new object")],
        default=align_type)

    def draw(self, context):

        layout = self.layout
        split = layout.split(factor=0.3)

        col_1 = split.column()
        col_2 = split.column()

        col_1.label(text="Vertices")
        col_2.prop(self, "vertices")

        col_1.label(text="Radius")
        col_2.prop(self, "radius")

        col_1.label(text="Depth")
        col_2.prop(self, "depth")

        col_1.label(text="Cap Fill Type")
        col_2.prop(self, "cap_fill")

        col_1.label(text="")
        col_2.prop(self, "b_UV")

        col_1.label(text="Align")
        col_2.prop(self, "align")

    def modal(self, context, event):
        return {'FINISHED'}

    def invoke(self, context, event):

        applied_rotation = False

        # before any calculations are done we first hide modifiers in the viewport
        modifiers_changed = show_or_hide_modifiers_in_viewport(
            context.active_object, False)

        # save location and rotation
        self.saved_object_location, self.saved_object_rotation = save_location_rotation(
            context.active_object)
        self.align = "WORLD"

        # first we'll check if the rotation is (0,0,0) to skip the next check
        if context.active_object.rotation_euler == Euler((0, 0, 0)):
            # check if rotation is applied, because functions won't work
            if check_if_wrong_cone_or_cylinder_rotation(context.active_object):

                applied_rotation = True

                # if the rotation was applied we fix it so it's truly (0,0,0)
                bpy.ops.object.fix_applied_rotation_auto()

                self.saved_object_rotation = Euler(
                    context.scene.objects["if_you==girl_AND_you==READING_THIS_AND_you==SINGLE_THEN_DM_ME"].rotation_euler)
                context.active_object.rotation_euler = self.saved_object_rotation

                # delete the super secret cube
                cube_to_delete = bpy.data.objects["if_you==girl_AND_you==READING_THIS_AND_you==SINGLE_THEN_DM_ME"]
                bpy.data.objects.remove(cube_to_delete, do_unlink=True)

        # calculate variables
        self.Y = context.active_object.dimensions[1]
        self.depth = context.active_object.dimensions[2]
        self.radius = calculate_cylinder_radius(context.active_object)
        if not context.object.data.uv_layers:
            self.b_UV = False

        # check the number of vertices of the object and its cap fill
        if len(context.object.data.polygons) == (len(context.object.data.vertices)/2)+2:
            self.vertices = int(len(context.object.data.vertices)/2)
            self.cap_type = 'NGON'
        elif len(context.object.data.polygons) == (len(context.object.data.vertices)/2):
            self.vertices = int(len(context.object.data.vertices)/2)
            self.cap_type = 'NOTHING'
        else:
            self.vertices = int((len(context.object.data.vertices)-2)/2)
            self.cap_type = 'TRIFAN'

        # apply cap fill settings if they're different from the enum option drop
        if self.cap_type != self.cap_fill:
            self.cap_fill = self.cap_type

        # after we're done we unhide modifiers in the viewport if they weren't hidden
        if modifiers_changed:
            show_or_hide_modifiers_in_viewport(context.active_object, True)

        # we don't have to fix rotation if Y axis goes through 2 cylinder edges, that happens when (vertices-2)%4==0
        # look at https://drive.google.com/file/d/1_p8GNj4fXDeyflXOhAiwfcR8xGuOf8Lj/view?usp=sharing
        if applied_rotation and (self.vertices-2) % 4 != 0:

            # if uneven we can just rotate on Z by 90 degrees
            if self.vertices % 2 != 0:
                self.saved_object_rotation = rotate_around_axis_followed_by_euler_rotation(
                    'Z', pi/2, self.saved_object_rotation)

            # otherwise we have to calculate the angle between sides and divide it with -2
            else:
                z_offset = calculate_z_offset(self.vertices)
                self.saved_object_rotation = rotate_around_axis_followed_by_euler_rotation(
                    'Z', z_offset, self.saved_object_rotation)

            # if the user invokes the operator but doesn't do anything and clicks away instead of pressing ok-> execute doesn't go off
            # we're force calling execute to fix the rotation
            self.execute(context)

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):

        replace_cylinder(self.vertices, self.radius, self.depth, self.cap_fill, self.saved_object_location, self.saved_object_rotation,
                         self.align, self.b_UV)

        return {'FINISHED'}


class RePrimitiveIcoSphere(Operator):
    """
    Tweak icosphere operator
    """
    bl_idname = "object.reprimitive_icosphere"
    bl_label = "Tweak IcoSphere"
    bl_options = {'REGISTER', 'UNDO', 'PRESET', 'INTERNAL'}

    # create default values
    saved_object_location = Vector((0, 0, 0))
    saved_object_rotation = Euler((0, 0, 0))

    subdivisions = 2
    radius = 1
    Y = 0
    align_type = 'WORLD'
    b_UV = True

    # properties
    subdivisions: IntProperty(
        name="",
        default=subdivisions,
        soft_min=1,
        soft_max=8,
        min=1,
        max=8)
    radius: FloatProperty(
        name="",
        default=radius,
        soft_min=0.001,
        min=0)
    b_UV: BoolProperty(
        name="Generate UVs",
        default=b_UV)
    align: EnumProperty(
        name="",
        description="Select an option",
        items=[('WORLD', "World", "Align the new object to the world"),
               ('VIEW', "View", "Align the new object to the view"),
               ('CURSOR', "3D Cursor", "Use the 3d cursor orientation for the new object")],
        default=align_type)

    def draw(self, context):

        layout = self.layout
        split = layout.split(factor=0.3)

        col_1 = split.column()
        col_2 = split.column()

        col_1.label(text="Subdivisions")
        col_2.prop(self, "subdivisions")

        col_1.label(text="Radius")
        col_2.prop(self, "radius")

        col_1.label(text="")
        col_2.prop(self, "b_UV")

        col_1.label(text="Align")
        col_2.prop(self, "align")

    def modal(self, context, event):
        return {'FINISHED'}

    def invoke(self, context, event):

        applied_rotation = False

        # before any calculations are done we first hide modifiers in the viewport
        modifiers_changed = show_or_hide_modifiers_in_viewport(
            context.active_object, False)

        # save location and rotation
        self.saved_object_location, self.saved_object_rotation = save_location_rotation(
            context.active_object)
        self.align = "WORLD"

        # first we'll check if the rotation is (0,0,0) to skip the next check
        if context.active_object.rotation_euler == Euler((0, 0, 0)):
            # check if rotation is applied , because functions won't work
            if check_if_wrong_sphere_rotation(context.active_object):

                # if the rotation was applied we fix it so it's truly (0,0,0)
                applied_rotation = True
                bpy.ops.object.fix_applied_rotation_auto()

                # the above function also spawns a cube that we use to reapply the rotation as it was before fixing but this time it won't be (0,0,0)
                self.saved_object_rotation = Euler(
                    context.scene.objects["if_you==girl_AND_you==READING_THIS_AND_you==SINGLE_THEN_DM_ME"].rotation_euler)
                #context.active_object.rotation_euler = self.saved_object_rotation

                # delete the super secret cube
                cube_to_delete = bpy.data.objects["if_you==girl_AND_you==READING_THIS_AND_you==SINGLE_THEN_DM_ME"]
                bpy.data.objects.remove(cube_to_delete, do_unlink=True)

        # calculate variables
        self.Y = context.object.dimensions[1]
        self.radius = calculate_icosphere_radius(context.active_object)
        self.subdivisions = int(log(
            len(context.active_object.data.polygons)/20, 4)+1)
        if not context.object.data.uv_layers:
            self.b_UV = False

        # after we're done we unhide modifiers in the viewport if they weren't hidden
        if modifiers_changed:
            show_or_hide_modifiers_in_viewport(context.active_object, True)

        if applied_rotation:

            # unlike other objects icosphere only needs to be rotated on Z for 180
            self.saved_object_rotation = rotate_around_axis_followed_by_euler_rotation(
                "Z", pi, self.saved_object_rotation)

            # if the user invokes the operator but doesn't do anything and clicks away instead of pressing ok-> execute doesn't go off
            # we're force calling execute to fix the rotation
            self.execute(context)

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):

        replace_icosphere(self.subdivisions, self.radius, self.saved_object_location,
                          self.saved_object_rotation, self.align, self.b_UV)

        return {'FINISHED'}


class RePrimitiveTorus(Operator):
    """
    Tweak torus operator
    """
    bl_idname = "object.reprimitive_torus"
    bl_label = "Tweak Torus"
    bl_options = {'REGISTER', 'UNDO', 'PRESET', 'INTERNAL'}

    # create default values
    saved_object_location = Vector((0, 0, 0))
    saved_object_rotation = Euler((0, 0, 0))

    major_segments = 48
    minor_segments = 12
    major_radius = 1
    minor_radius = 0.25
    align_type = 'WORLD'
    b_UV = True

    # properties
    major_segments: IntProperty(
        name="",
        default=major_segments,
        soft_min=3,
        soft_max=256,
        min=3,
        max=256)
    minor_segments: IntProperty(
        name="",
        default=minor_segments,
        soft_min=3,
        soft_max=256,
        min=3,
        max=256)
    major_radius: FloatProperty(
        name="",
        default=major_radius,
        soft_min=0,
        min=0)
    minor_radius: FloatProperty(
        name="",
        default=minor_radius,
        soft_min=0,
        min=0)
    b_UV: BoolProperty(
        name="Generate UVs",
        default=b_UV)
    align: EnumProperty(
        name="",
        description="Select an option",
        items=[('WORLD', "World", "Align the new object to the world"),
               ('VIEW', "View", "Align the new object to the view"),
               ('CURSOR', "3D Cursor", "Use the 3d cursor orientation for the new object")],
        default=align_type)

    def draw(self, context):

        layout = self.layout
        split = layout.split(factor=0.35)

        col_1 = split.column()
        col_2 = split.column()

        col_1.label(text="Major Segments")
        col_2.prop(self, "major_segments")

        col_1.label(text="Minor Segments")
        col_2.prop(self, "minor_segments")

        col_1.label(text="Major Radius")
        col_2.prop(self, "major_radius")

        col_1.label(text="Minor Radius")
        col_2.prop(self, "minor_radius")

        col_1.label(text="")
        col_2.prop(self, "b_UV")

        col_1.label(text="Align")
        col_2.prop(self, "align")

    def modal(self, context, event):
        return {'FINISHED'}

    def invoke(self, context, event):

        applied_rotation = False

        # before any calculations are done we first hide modifiers in the viewport
        modifiers_changed = show_or_hide_modifiers_in_viewport(
            context.active_object, False)

        # save location and rotation
        self.saved_object_location, self.saved_object_rotation = save_location_rotation(
            context.active_object)
        self.align = "WORLD"

        # first we'll check if the rotation is (0,0,0) to skip the next check
        if context.active_object.rotation_euler == Euler((0, 0, 0)):
            # check if rotation is applied, because functions won't work
            if check_if_wrong_torus_rotation(context.active_object):

                # if the rotation was applied we fix it so it's truly (0,0,0)
                applied_rotation = True
                bpy.ops.object.fix_applied_rotation_auto()

                # the above function also spawns a cube that we use to reapply the rotation as it was before fixing but this time it won't be (0,0,0)
                self.saved_object_rotation = Euler(
                    context.scene.objects["if_you==girl_AND_you==READING_THIS_AND_you==SINGLE_THEN_DM_ME"].rotation_euler)
                context.active_object.rotation_euler = self.saved_object_rotation

                # delete the super secret cube
                cube_to_delete = bpy.data.objects["if_you==girl_AND_you==READING_THIS_AND_you==SINGLE_THEN_DM_ME"]
                bpy.data.objects.remove(cube_to_delete, do_unlink=True)

        # calculate variables
        self.major_segments = int(calculate_torus_major_segments(
            context.active_object))
        self.minor_segments = int(len(
            context.active_object.data.vertices)/self.major_segments)
        tip_vert, neighbour_vert = find_tip_and_neighbour_vert(
            context.active_object)
        self.minor_radius = calculate_polygon_radius(
            self.minor_segments, tip_vert, neighbour_vert)
        if not context.object.data.uv_layers:
            self.b_UV = False

        # save location, reset it and apply it, we need this for the next part because we're comparing distance to (0,0,0)
        saved_loc = Vector(context.active_object.location)
        context.active_object.location = (0, 0, 0)
        bpy.ops.object.transform_apply(
            location=True, rotation=False, scale=False)

        # subtract minor radius from the distance between first selected vert and the middle
        self.major_radius = distance_vec(
            tip_vert, Vector((0, 0, 0)))-self.minor_radius

        # restore location
        context.active_object.location = saved_loc

        # after we're done we unhide modifiers in the viewport if they weren't hidden
        if modifiers_changed:
            show_or_hide_modifiers_in_viewport(context.active_object, True)

        # if the rotation was applied first rotate it by offset on Z, then rotate based on saved rotation
        # look at https://drive.google.com/file/d/1xI0NubgaogZtGhrnmRr2wZmjqGRCSeW4/view?usp=sharing
        if applied_rotation:

            # if you were to cut torus on both X and Y and the quarter piece you get was symmetrical to itself
            if self.major_segments % 4 == 0:
                z_offset = calculate_z_offset(self.major_segments)
                self.saved_object_rotation = rotate_around_axis_followed_by_euler_rotation(
                    'Z', z_offset, self.saved_object_rotation)

            # if torus is symmetrical on both X and Y but the quarter piece isn't symmetrical
            elif self.major_segments % 2 == 0:
                self.saved_object_rotation = rotate_around_axis_followed_by_euler_rotation(
                    'Z', pi/2, self.saved_object_rotation)

            # if torus is only symmetrical on 1 axis
            else:
                self.saved_object_rotation = rotate_around_axis_followed_by_euler_rotation(
                    'Z', pi, self.saved_object_rotation)

            # if the user invokes the operator but doesn't do anything and clicks away instead of pressing ok-> execute doesn't go off
            # we're force calling execute to fix the rotation
            self.execute(context)

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):

        replace_torus(self.major_segments, self.minor_segments, self.major_radius, self.minor_radius,
                      self.saved_object_location, self.saved_object_rotation, self.align, self.b_UV)

        return {'FINISHED'}


class RePrimitiveUVSphere(Operator):
    """
    Tweak UVSphere operator
    """
    bl_idname = "object.reprimitive_sphere"
    bl_label = "Tweak UVSphere"
    bl_options = {'REGISTER', 'UNDO', 'PRESET', 'INTERNAL'}

    # create default values
    saved_object_location = Vector((0, 0, 0))
    saved_object_rotation = Euler((0, 0, 0))

    segments = 32
    rings = 16
    radius = 1
    depth = 0
    align_type = 'WORLD'
    b_UV = True

    # properties
    segments: IntProperty(
        name="",
        default=segments,
        soft_min=3,
        min=3,
        soft_max=500,
        max=500)
    rings: IntProperty(
        name="",
        default=rings,
        soft_min=3,
        min=3,
        soft_max=500,
        max=500)
    radius: FloatProperty(
        name="",
        default=radius,
        soft_min=0.001,
        min=0)
    b_UV: BoolProperty(
        name="Generate UVs",
        default=b_UV)
    align: EnumProperty(
        name="",
        description="Select an option",
        items=[('WORLD', "World", "Align the new object to the world"),
               ('VIEW', "View", "Align the new object to the view"),
               ('CURSOR', "3D Cursor", "Use the 3d cursor orientation for the new object")],
        default=align_type)

    def draw(self, context):

        layout = self.layout
        split = layout.split(factor=0.3)

        col_1 = split.column()
        col_2 = split.column()

        col_1.label(text="Segments")
        col_2.prop(self, "segments")

        col_1.label(text="Rings")
        col_2.prop(self, "rings")

        col_1.label(text="Radius")
        col_2.prop(self, "radius")

        col_1.label(text="")
        col_2.prop(self, "b_UV")

        col_1.label(text="Align")
        col_2.prop(self, "align")

    # https://www.youtube.com/watch?v=dQw4w9WgXcQ

    def modal(self, context, event):
        return {'FINISHED'}

    def invoke(self, context, event):

        applied_rotation = False

        # before any calculations are done we first hide modifiers in the viewport
        modifiers_changed = show_or_hide_modifiers_in_viewport(
            context.active_object, False)

        # save location and rotation
        self.saved_object_location, self.saved_object_rotation = save_location_rotation(
            context.active_object)
        self.align = "WORLD"

        # first we'll check if the rotation is (0,0,0) to skip the next check
        if context.active_object.rotation_euler == Euler((0, 0, 0)):
            # check if rotation is applied, because functions won't work
            if check_if_wrong_sphere_rotation(context.active_object):

                # if the rotation was applied we fix it so it's truly (0,0,0)
                applied_rotation = True
                bpy.ops.object.fix_applied_rotation_auto()

                # the above function also spawns a cube that we use to reapply the rotation as it was before fixing but this time it won't be (0,0,0)
                self.saved_object_rotation = Euler(
                    context.scene.objects["if_you==girl_AND_you==READING_THIS_AND_you==SINGLE_THEN_DM_ME"].rotation_euler)
                context.active_object.rotation_euler = self.saved_object_rotation

                # delete the super secret cube
                cube_to_delete = bpy.data.objects["if_you==girl_AND_you==READING_THIS_AND_you==SINGLE_THEN_DM_ME"]
                bpy.data.objects.remove(cube_to_delete, do_unlink=True)

        # calculate variables
        self.depth = bpy.context.object.dimensions[2]
        self.radius = self.depth/2
        self.segments = int(calculate_sphere_segments(context.active_object))
        self.rings = int(
            len(context.active_object.data.polygons)/self.segments)
        if not context.object.data.uv_layers:
            self.b_UV = False

        # after we're done we unhide modifiers in the viewport if they weren't hidden
        if modifiers_changed:
            show_or_hide_modifiers_in_viewport(context.active_object, True)

        # we don't have to fix the rotation if edges go through Y axis by default
        if applied_rotation and (self.segments-2) % 4 != 0:

            # if uneven we can just rotate on Z by 90 degrees
            if self.segments % 2 != 0:
                self.saved_object_rotation = rotate_around_axis_followed_by_euler_rotation(
                    'Z', pi/2, self.saved_object_rotation)

            # otherwise we have to calculate the angle between sides and divide it with -2
            else:
                z_offset = calculate_z_offset(self.segments)
                self.saved_object_rotation = rotate_around_axis_followed_by_euler_rotation(
                    'Z', z_offset, self.saved_object_rotation)

            # if the user invokes the operator but doesn't do anything and clicks away instead of pressing ok-> execute doesn't go off
            # we're force calling execute to fix the rotation
            self.execute(context)

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):

        replace_uv_sphere(self.segments, self.rings, self.radius,
                          self.saved_object_location, self.saved_object_rotation, self.align, self.b_UV)

        return {'FINISHED'}


class FixAppliedRotationAuto(Operator):
    """
    Fixes applied rotation and keeps a cube that we use to rotate the main object, user can't call this one
    """
    bl_idname = "object.fix_applied_rotation_auto"
    bl_label = "Fix Applied Rotation"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):

        # save original object ref and its location
        ob = context.active_object
        saved_location = Vector(ob.location)
        saved_name = ob.name

        # set the location to 0 so some of the smart selection that compares to the (0,0,0) Vector would work
        # i could change the functions so they work regardless but they're simpler this way
        ob.location = (0, 0, 0)

        # save view
        rv = context.space_data.region_3d
        matrix = rv.view_matrix

        # if user ran the operator from object mode use smart selection
        # only works for simple objects
        if context.mode == 'OBJECT':

            # enter edit mode and deselect everything
            bpy.ops.object.editmode_toggle()
            bpy.ops.mesh.select_all(action='DESELECT')

            # change selection to vertices
            context.tool_settings.mesh_select_mode = (True, False, False)

            # use smart selection
            smart_selection(context.active_object)

        # if user ran the operator from edit mode we don't calculate selection and rather use what user selected
        # unless he selected nothing then we use smart selection just like in object mode
        elif context.mode == 'EDIT_MESH':

            # confirm selection
            bpy.ops.object.editmode_toggle()
            bpy.ops.object.editmode_toggle()

            # check if nothing is selected
            if len([v for v in context.active_object.data.vertices if v.select]) == 0:

                # use smart selection
                smart_selection(context.active_object)

            # check if more than 2 faces are selected
            elif len([f for f in context.active_object.data.polygons if f.select]) > 2:

                bpy.ops.mesh.duplicate()
                bpy.ops.transform.resize(value=(1, 1, 0), orient_type='NORMAL')
                bpy.ops.transform.translate(value=(0, 0, 2))
                bpy.ops.mesh.dissolve_edges()

                # align view to the selected faces and delete the face after
                bpy.ops.view3d.view_axis(type='TOP', align_active=True)
                bpy.ops.mesh.delete(type='EDGE')

            # otherwise just align to selection(1 vert,edge,face, etc)
            else:
                bpy.ops.view3d.view_axis(type='TOP', align_active=True)

        # deselect all faces and return to object mode
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.editmode_toggle()

        # add two cubes, 1-> that's gonna be used to fix the rotation so it's truly (0,0,0)
        # and 2-> to restore original object rotation to how it was before applied
        # cube number 2, we use this one outside of the operator since there's no way to return values from operator
        bpy.ops.mesh.primitive_cube_add(location=saved_location, align='VIEW')
        context.active_object.name = "if_you==girl_AND_you==READING_THIS_AND_you==SINGLE_THEN_DM_ME"

        # cube number 1, we use this one in this operator
        bpy.ops.mesh.primitive_cube_add(location=saved_location, align='VIEW')
        cube = context.active_object

        # deselect everything and select original object, followed by the cube
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        cube.select_set(True)

        # parent object to cube
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)

        # deselect everything again and select the cube
        bpy.ops.object.select_all(action='DESELECT')
        cube.select_set(True)

        # reset rotation of the cube
        bpy.ops.object.rotation_clear(clear_delta=False)

        # deselect everything again and select the original object
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)

        # clear parent and keep transform, after that apply the rotation
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        bpy.ops.object.transform_apply(
            location=False, rotation=True, scale=False)

        # deselect everything, select the cube and delete it
        bpy.ops.object.select_all(action='DESELECT')
        cube.select_set(True)
        bpy.ops.object.delete()

        # restore saved view and reselect the original object
        rv.view_perspective = 'PERSP'
        rv.view_matrix = matrix
        context.scene.objects[saved_name].select_set(True)
        context.view_layer.objects.active = ob

        # restore original location
        ob.location = saved_location

        return {'FINISHED'}

# same as the above class except this one doesn't spawn an extra cube because we don't care about returning the object to previous rotation


class FixAppliedRotation(Operator):
    """
    Fix applied rotation so it is truly (0,0,0)
    """
    bl_idname = "object.fix_applied_rotation"
    bl_label = "Fix Applied Rotation"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        # save original object ref and name
        ob = context.active_object
        saved_name = ob.name
        cone_loc_applied = False
        was_filled = False
        changed_mode = False

        # if in edit mode enter object mode
        if context.mode == 'EDIT_MESH':
            changed_mode = True
            bpy.ops.object.editmode_toggle()

        # cone requires a specific function if location was applied because origin to geometry doesn't work in every case
        if ob.data.name.startswith(('Cone', '锥体')) and ob.location == Vector((0, 0, 0)):

            # if cone is not manifold, origin to center of volume won't work, so we're filling in the face
            bpy.ops.object.editmode_toggle()
            was_filled, total_faces, difference = fill_face_if_non_manifold(
                context.active_object)
            bpy.ops.object.editmode_toggle()

            bpy.ops.object.origin_set(
                type='ORIGIN_CENTER_OF_VOLUME', center='MEDIAN')
            cone_loc_applied = True
            saved_location = ob.location

        else:

            # save object location, we don't actually need the rotation, this also fixes the location if it was applied
            saved_location, saved_rotation = save_location_rotation(ob)
            # set the location to 0 so some of the smart selection that compares to the (0,0,0) Vector would work
            # i could change the functions so they work regardless but they're simpler this way
            ob.location = (0, 0, 0)

        # if we changed the mode from edit swap it back
        if changed_mode:
            bpy.ops.object.editmode_toggle()

        # save view
        rv = context.space_data.region_3d
        matrix = rv.view_matrix

        # if user ran the operator from object mode use smart selection
        # only works for simple objects
        if context.mode == 'OBJECT':

            # enter edit mode and deselect everything
            bpy.ops.object.editmode_toggle()
            bpy.ops.mesh.select_all(action='DESELECT')

            # change selection to vertices
            context.tool_settings.mesh_select_mode = (True, False, False)

            # use smart selection
            smart_selection(context.active_object)

        # if user ran the operator from edit mode we don't calculate selection and rather use what user selected
        # unless he selected nothing then we use smart selection just like in object mode
        elif context.mode == 'EDIT_MESH':

            # check if nothing is selected
            if len([v for v in context.active_object.data.vertices if v.select]) == 0:

                # use smart selection
                smart_selection(context.active_object)

            # check if more than 2 faces are selected
            elif len([f for f in context.active_object.data.polygons if f.select]) > 1:

                bpy.ops.mesh.duplicate()
                bpy.ops.transform.resize(value=(1, 1, 0), orient_type='NORMAL')
                bpy.ops.mesh.dissolve_edges()

                # align view to the selected faces and delete the face after
                bpy.ops.view3d.view_axis(type='TOP', align_active=True)
                bpy.ops.mesh.delete(type='EDGE')

            # otherwise just align to selection(1 vert,edge,face, etc)
            else:
                bpy.ops.view3d.view_axis(type='TOP', align_active=True)

        # deselect all faces and return to object mode
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.editmode_toggle()

        # add a cube that's aligned to view, this way we get the objects true rotation
        bpy.ops.mesh.primitive_cube_add(location=saved_location, align='VIEW')
        cube = context.active_object

        # save the cube rotation, we only use this for special cases when both location was applied and the object in question is a cone with a sharp tip
        cube_saved_rot = Euler(cube.rotation_euler)

        # deselect everything and select original object, followed by the cube
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        cube.select_set(True)

        # parent object to cube
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)

        # deselect everything again and select the cube
        bpy.ops.object.select_all(action='DESELECT')
        cube.select_set(True)

        # reset rotation of the cube
        bpy.ops.object.rotation_clear(clear_delta=False)

        # deselect everything again and select the original object
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)

        # clear parent and keep transform, after that apply the rotation
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        bpy.ops.object.transform_apply(
            location=False, rotation=True, scale=False)

        # deselect everything, select the cube and delete it
        bpy.ops.object.select_all(action='DESELECT')
        cube.select_set(True)
        bpy.ops.object.delete()

        # restore saved view and reselect the original object
        rv.view_perspective = 'PERSP'
        rv.view_matrix = matrix
        context.scene.objects[saved_name].select_set(True)
        context.view_layer.objects.active = ob

        # if the object was cone and the location was applied
        if cone_loc_applied:

            # if we added a cap, delete the last 2 or 1 depending on cone shape
            if was_filled:

                bpy.ops.object.editmode_toggle()
                bm = bmesh.from_edit_mesh(ob.data)
                bm.faces.ensure_lookup_table()
                bm.faces[total_faces-1].select_set(True)
                if difference == 2:
                    bm.faces[total_faces-2].select_set(True)
                bpy.ops.mesh.delete(type='FACE')
                bpy.ops.object.editmode_toggle()

            cylindrical = is_cone_cylindrical(ob)

            # if the cone is cylindrical then we can use the usual function that uses origin to geometry
            if cylindrical:

                # we already fixed the origin but it's wrong for cylindrical cones
                bpy.ops.object.origin_set(
                    type='ORIGIN_GEOMETRY', center='MEDIAN')

                cone_loc_applied = False
                saved_location, saved_rotation = save_location_rotation(
                    ob)

            # if cone has a sharp tip origin to geometry won't work so we do this instead
            else:
                # function will simply return object rotation and location without fixing if location isn't (0,0,0) so we're applying location to force call
                bpy.ops.object.transform_apply(
                    location=True, rotation=False, scale=False)
                saved_location, saved_rotation = fix_cone_origin_and_save_location_rotation_special(
                    context.active_object)

        # restore original location
        ob.location = saved_location

        # fix the rotation on Z axis so it matches blender default and apply rotation again
        Z_offset_ob(ob)
        bpy.ops.object.transform_apply(
            location=False, rotation=True, scale=False)

        # offset location on both local and global Z if both rotation and location were applied and the object was a sharp tip cone
        if cone_loc_applied:

            ob.rotation_euler = cube_saved_rot
            bpy.ops.transform.translate(
                value=(0, 0, ob.dimensions[2]/4), orient_type='GLOBAL')
            bpy.ops.transform.translate(
                value=(0, 0, -ob.dimensions[2]/4), orient_type='LOCAL')
            ob.rotation_euler = (0, 0, 0)

        return {'FINISHED'}

# 01000001 01101100 01110011 01101111 00101100 00100000 01101101 01100001 01110011 01110011 00100000 01100101 01100110
# 01100110 01100101 01100011 01110100 00100000 01101001 01110011 00100000 01110100 01101000 01100101 00100000 01100111
# 01110010 01100101 01100001 01110100 01100101 01110011 01110100 00100000 01100111 01100001 01101101 01100101 00100000
# 01101111 01100110 00100000 01100001 01101100 01101100 00100000 01110100 01101001 01101101 01100101
