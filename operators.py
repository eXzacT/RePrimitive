import bpy
from .localization import *
from .core import *
from math import log, pi
from bpy.types import Operator
from bpy.props import BoolProperty, IntProperty, EnumProperty, FloatProperty
from mathutils import Vector, Euler

CUBE_NAME = "cube_to_delete_123#"


class RePrimitive(Operator):
    """
    Main reprimitive operator, it decides which other operator gets called
    """
    bl_idname = "object.reprimitive"
    bl_label = "Tweak Primitives"
    bl_description = "Tweak Primitives"
    bl_options = {'REGISTER', 'UNDO'}

    # Can only be called in object mode and specifically named objects
    @classmethod
    def poll(cls, context):
        ob = context.active_object
        if not ob or bpy.context.mode != 'OBJECT':
            return False

        names = tuple(name.lower() for name in localization_all)
        return ob.name.lower().startswith(names)

    def execute(self, context):
        name = context.active_object.data.name.lower()

        if name.startswith(localization_cylinder.lower()):
            bpy.ops.object.reprimitive_cylinder('INVOKE_DEFAULT')
        elif name.startswith(localization_cone.lower()):
            bpy.ops.object.reprimitive_cone('INVOKE_DEFAULT')
        elif name.startswith(localization_circle.lower()):
            bpy.ops.object.reprimitive_circle('INVOKE_DEFAULT')
        elif name.startswith(localization_torus.lower()):
            bpy.ops.object.reprimitive_torus('INVOKE_DEFAULT')
        elif name.startswith(localization_sphere.lower()):
            bpy.ops.object.reprimitive_sphere('INVOKE_DEFAULT')
        elif name.startswith(localization_icosphere.lower()):
            bpy.ops.object.reprimitive_icosphere('INVOKE_DEFAULT')
        return {'FINISHED'}


class RePrimitiveCircle(Operator):
    """
    Tweak circle operator
    """
    bl_idname = "object.reprimitive_circle"
    bl_label = "Tweak Circle"
    bl_options = {'REGISTER', 'UNDO', 'PRESET', 'INTERNAL'}

    # two bool checks to stop executing code twice from "check" function once OK is pressed or the user clicked outside of the window popup
    from_check = False
    execute_on_check = True

    # create default values
    saved_loc = Vector((0, 0, 0))
    saved_rot = Euler((0, 0, 0))
    Y = 0
    radius = 1
    vertices = 32
    cap_type = 'NGON'
    align_type = 'WORLD'
    b_UV = True
    origin = 0

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

    # bool to know whether operator was called from cancel(clicking away from the popup)
    operator_called_from_cancel: BoolProperty(
        name='',
        default=False)

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

    # this function lets us show changes from window popup live
    def check(self, context):
        # this will only run ---BEFORE--- "OK" button was pressed / user clicked outside of the window popup
        # this is how we prevent the execute from running twice, because once the operator isn't in a window popup but rather locked in the bottom left corner check is still getting called and we don't need it
        if self.execute_on_check:
            self.from_check = True
            self.execute(context)
        return True

    def cancel(self, context):
        # calling the operator again after user clicked outside of the popup but this time we're also letting it know we called it from cancel
        bpy.ops.object.reprimitive_circle(
            'INVOKE_DEFAULT', operator_called_from_cancel=True)

    def invoke(self, context, event):

        ob = context.active_object
        applied_rotation = False

        # before any calculations are done we first hide modifiers in the viewport
        modifiers_changed = show_or_hide_modifiers_in_viewport(ob, False)

        # save location and rotation
        self.saved_loc, self.saved_rot, self.origin = save_location_rotation(
            ob)
        self.align = "WORLD"

        if applied_rotation_circle(ob):

            # if the rotation was applied we fix it so it's truly (0,0,0)
            applied_rotation = True
            bpy.ops.object.fix_applied_rotation_auto()

            # The cube we spawned using the custom operator holds the true object rotation
            self.saved_rot = Euler(
                context.scene.objects[CUBE_NAME].rotation_euler)
            ob.rotation_euler = self.saved_rot
            bpy.data.meshes.remove(bpy.data.meshes[CUBE_NAME])

        # calculate variables
        if (len(ob.data.polygons)) == 0:
            self.cap_type = 'NOTHING'
        elif (len(ob.data.polygons)) == 1:
            self.cap_type = 'NGON'
        else:
            self.cap_type = 'TRIFAN'

        if self.cap_type == 'TRIFAN':
            self.vertices = int(len(ob.data.vertices)-1)
        else:
            self.vertices = int(len(ob.data.vertices))

        self.radius = calculate_circle_radius(ob)
        if not ob.data.uv_layers:
            self.b_UV = False

        # apply cap fill settings if they're different from the enum option drop
        if self.cap_type != self.cap_fill:
            self.cap_fill = self.cap_type

        # after we're done we unhide modifiers in the viewport if they weren't hidden
        if modifiers_changed:
            show_or_hide_modifiers_in_viewport(ob, True)

        restore_origin(self.origin)

        # we don't have to fix the rotation if verts go through Y axis by default
        if applied_rotation and (self.vertices-2) % 4 != 0:

            # if uneven we can just rotate on Z by 90 degrees
            if self.vertices % 2 != 0:
                self.saved_rot = rotate_around_axis_followed_by_euler_rotation(
                    'Z', pi/2, self.saved_rot)

            # otherwise we have to calculate the angle between sides and divide it with -2
            else:
                z_offset = calculate_z_offset(self.vertices)
                self.saved_rot = rotate_around_axis_followed_by_euler_rotation(
                    'Z', z_offset, self.saved_rot)

            # if the user invokes the operator but doesn't do anything and clicks away instead of pressing ok-> execute doesn't go off
            # we're force calling execute to fix the rotation
            self.from_check = True
            self.execute(context)

        # Show operator in bottom left corner if user clicked away
        if self.operator_called_from_cancel:
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        # Popup window
        else:
            return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):

        replace_circle(self.vertices, self.radius, self.cap_fill,
                       self.saved_loc, self.saved_rot, self.align, self.b_UV, self.origin)

        # if execute was ran from check function set to false so execute can run from there again
        if self.from_check:
            self.from_check = False
        # if execute was ran from clicking "OK" or clicking away then disable check from running it again
        else:
            self.execute_on_check = False

        return {'FINISHED'}


class RePrimitiveCone(Operator):
    """
    Tweak cone operator
    """
    bl_idname = "object.reprimitive_cone"
    bl_label = "Tweak Cone"
    bl_options = {'REGISTER', 'UNDO', 'PRESET', 'INTERNAL'}

    # two bool checks to stop executing code twice from "check" function once OK is pressed or the user clicked outside of the window popup
    from_check = False
    execute_on_check = True

    # create default values
    saved_loc = Vector((0, 0, 0))
    saved_rot = Euler((0, 0, 0))
    Y = 0
    depth = 2
    radius1 = 1
    radius2 = 0
    vertices = 32
    cap_type = 'NGON'
    align_type = 'WORLD'
    b_UV = True
    origin = 0

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

    # bool to know whether operator was called from cancel(clicking away from the popup)
    operator_called_from_cancel: BoolProperty(
        name='',
        default=False)

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

    # this function lets us show changes from window popup live
    def check(self, context):
        # this will only run ---BEFORE--- "OK" button was pressed / user clicked outside of the window popup
        # this is how we prevent the execute from running twice, because once the operator isn't in a window popup but rather locked in the bottom left corner check is still getting called and we don't need it
        if self.execute_on_check:
            self.from_check = True
            self.execute(context)
        return True

    def cancel(self, context):
        # calling the operator again after user clicked outside of the popup but this time we're also letting it know we called it from cancel
        bpy.ops.object.reprimitive_cone(
            'INVOKE_DEFAULT', operator_called_from_cancel=True)

    def invoke(self, context, event):

        applied_rotation = False
        ob = context.object

        # before any calculations are done we first hide modifiers in the viewport
        modifiers_changed = show_or_hide_modifiers_in_viewport(ob, False)

        if applied_rotation_cone_or_cylinder(ob):
            applied_rotation = True

            # The cube we spawned using the custom operator holds the true object rotation
            bpy.ops.object.fix_applied_rotation_auto()
            self.saved_rot = Euler(
                context.scene.objects[CUBE_NAME].rotation_euler)
            ob.rotation_euler = self.saved_rot
            bpy.data.meshes.remove(bpy.data.meshes[CUBE_NAME])

        # Save origin first since is_cone_cylindrical changes it
        self.origin = Vector(ob.location)
        self.radius1, self.radius2, self.vertices, self.cap_type, sharp_tipped = calculate_cone_properties(
            ob)

        # Sadly origin to geometry doesn't work for cones so we have to fix it manually,
        # origin to geometry 'BOUNDS' almost works but it's not perfect because it doesn't work for uneven side cones
        if sharp_tipped:
            self.saved_loc, self.saved_rot, _ = fix_cone_origin_and_save_location_rotation(
                ob,  applied_rotation or self.radius1 < self.radius2)  # Meaning upsidedown
        else:  # Cylindrical
            self.saved_loc, self.saved_rot, _ = save_location_rotation(ob)

        # calculate variables
        self.align = "WORLD"
        self.Y = ob.dimensions.y
        self.depth = ob.dimensions.z
        if not ob.data.uv_layers:
            self.b_UV = False

        # apply cap fill settings if they're different from the enum option drop
        if self.cap_type != self.cap_fill:
            self.cap_fill = self.cap_type

        # after we're done we unhide modifiers in the viewport if they weren't hidden
        if modifiers_changed:
            show_or_hide_modifiers_in_viewport(ob, True)

        # We don't have to fix the rotation if edges go through Y axis by default
        if applied_rotation and (self.vertices-2) % 4:

            # if uneven we can just rotate on Z by 90 degrees
            if self.vertices % 2:
                self.saved_rot = rotate_around_axis_followed_by_euler_rotation(
                    'Z', pi/2, self.saved_rot)

            # otherwise we have to calculate the angle between sides and divide it with -2
            else:
                z_offset = calculate_z_offset(self.vertices)
                self.saved_rot = rotate_around_axis_followed_by_euler_rotation(
                    'Z', z_offset, self.saved_rot)

        restore_origin(self.origin)

        # Show operator in bottom left corner if user clicked away
        if self.operator_called_from_cancel:
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        # Popup window
        else:
            return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):

        replace_cone(self.vertices, self.radius1, self.radius2, self.depth, self.cap_fill,
                     self.saved_loc, self.saved_rot, self.align, self.b_UV, self.origin)

        # if execute was ran from check function set to false so execute can run from there again
        if self.from_check:
            self.from_check = False
        # if execute was ran from clicking "OK" or clicking away then disable check from running it again
        else:
            self.execute_on_check = False

        return {'FINISHED'}


class RePrimitiveCylinder(Operator):
    """ Tweak cylinder operator """
    bl_idname = "object.reprimitive_cylinder"
    bl_label = "Tweak Cylinder"
    bl_options = {'REGISTER', 'UNDO', 'PRESET', 'INTERNAL'}

    # two bool checks to stop executing code twice from "check" function once OK is pressed or the user clicked outside of the window popup
    from_check = False
    execute_on_check = True

    # create default values
    saved_loc = Vector((0, 0, 0))
    saved_rot = Euler((0, 0, 0))
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

    # bool to know whether operator was called from cancel(clicking away from the popup)
    operator_called_from_cancel: BoolProperty(
        name='',
        default=False)

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

    # this function lets us show changes from window popup live
    def check(self, context):
        # this will only run ---BEFORE--- "OK" button was pressed / user clicked outside of the window popup
        # this is how we prevent the execute from running twice, because once the operator isn't in a window popup but rather locked in the bottom left corner check is still getting called and we don't need it
        if self.execute_on_check:
            self.from_check = True
            self.execute(context)
        return True

    def cancel(self, context):
        # calling the operator again after user clicked outside of the popup but this time we're also letting it know we called it from cancel
        bpy.ops.object.reprimitive_cylinder(
            'INVOKE_DEFAULT', operator_called_from_cancel=True)

    def invoke(self, context, event):

        ob = context.active_object
        applied_rotation = False

        # before any calculations are done we first hide modifiers in the viewport
        modifiers_changed = show_or_hide_modifiers_in_viewport(ob, False)

        # save location and rotation
        self.saved_loc, self.saved_rot, self.origin = save_location_rotation(
            ob)
        self.align = "WORLD"

        # Was the rotation really applied?
        if applied_rotation_cone_or_cylinder(ob):

            applied_rotation = True

            # if the rotation was applied we fix it so it's truly (0,0,0)
            bpy.ops.object.fix_applied_rotation_auto()
            self.saved_rot = Euler(
                context.scene.objects[CUBE_NAME].rotation_euler)
            ob.rotation_euler = self.saved_rot
            bpy.data.meshes.remove(bpy.data.meshes[CUBE_NAME])

        # Calculate variables
        self.Y = ob.dimensions[1]
        self.depth = ob.dimensions[2]
        self.radius, self.vertices, self.cap_type = calculate_cylinder_properties(
            ob)

        if not ob.data.uv_layers:
            self.b_UV = False

        # Apply cap fill settings if they're different from the enum option drop
        if self.cap_type != self.cap_fill:
            self.cap_fill = self.cap_type

        # After we're done we unhide modifiers in the viewport if they weren't hidden
        if modifiers_changed:
            show_or_hide_modifiers_in_viewport(ob, True)

        # We don't have to fix rotation if Y axis goes through 2 cylinder edges, that happens when (vertices-2)%4==0
        # look at https://drive.google.com/file/d/1_p8GNj4fXDeyflXOhAiwfcR8xGuOf8Lj/view?usp=sharing
        if applied_rotation and (self.vertices-2) % 4 != 0:

            # if uneven we can just rotate on Z by 90 degrees
            if self.vertices % 2 != 0:
                self.saved_rot = rotate_around_axis_followed_by_euler_rotation(
                    'Z', pi/2, self.saved_rot)

            # otherwise we have to calculate the angle between sides and divide it with -2
            else:
                z_offset = calculate_z_offset(self.vertices)
                self.saved_rot = rotate_around_axis_followed_by_euler_rotation(
                    'Z', z_offset, self.saved_rot)

            # if the user invokes the operator but doesn't do anything and clicks away instead of pressing ok-> execute doesn't go off
            # we're force calling execute to fix the rotation
            self.from_check = True
            self.execute(context)

        restore_origin(self.origin)

        # Show operator in bottom left corner if user clicked away
        if self.operator_called_from_cancel:
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        # Popup window
        else:
            return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):

        replace_cylinder(self.vertices, self.radius, self.depth, self.cap_fill, self.saved_loc, self.saved_rot,
                         self.align, self.b_UV, self.origin)

        # if execute was ran from check function set to false so execute can run from there again
        if self.from_check:
            self.from_check = False
        # if execute was ran from clicking "OK" or clicking away then disable check from running it again
        else:
            self.execute_on_check = False

        return {'FINISHED'}


class RePrimitiveIcoSphere(Operator):
    """
    Tweak icosphere operator
    """
    bl_idname = "object.reprimitive_icosphere"
    bl_label = "Tweak IcoSphere"
    bl_options = {'REGISTER', 'UNDO', 'PRESET', 'INTERNAL'}

    # two bool checks to stop executing code twice from "check" function once OK is pressed or the user clicked outside of the window popup
    from_check = False
    execute_on_check = True

    # create default values
    saved_loc = Vector((0, 0, 0))
    saved_rot = Euler((0, 0, 0))
    subdivisions = 2
    radius = 1
    Y = 0
    align_type = 'WORLD'
    b_UV = True
    origin = 0

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

    # bool to know whether operator was called from cancel(clicking away from the popup)
    operator_called_from_cancel: BoolProperty(
        name='',
        default=False)

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

    # this function lets us show changes from window popup live
    def check(self, context):
        # this will only run ---BEFORE--- "OK" button was pressed / user clicked outside of the window popup
        # this is how we prevent the execute from running twice, because once the operator isn't in a window popup but rather locked in the bottom left corner check is still getting called and we don't need it
        if self.execute_on_check:
            self.from_check = True
            self.execute(context)
        return True

    def cancel(self, context):
        # calling the operator again after user clicked outside of the popup but this time we're also letting it know we called it from cancel
        bpy.ops.object.reprimitive_icosphere(
            'INVOKE_DEFAULT', operator_called_from_cancel=True)

    def invoke(self, context, event):

        ob = context.active_object
        applied_rotation = False

        # before any calculations are done we first hide modifiers in the viewport
        modifiers_changed = show_or_hide_modifiers_in_viewport(ob, False)

        self.saved_loc, self.saved_rot, self.origin = save_location_rotation(
            ob)
        self.align = "WORLD"

        if applied_rotation_sphere(ob):

            # if the rotation was applied we fix it so it's truly (0,0,0)
            applied_rotation = True
            bpy.ops.object.fix_applied_rotation_auto()

            # The cube we spawned using the custom operator holds the true object rotation
            self.saved_rot = Euler(
                context.scene.objects[CUBE_NAME].rotation_euler)
            bpy.data.meshes.remove(bpy.data.meshes[CUBE_NAME])

        # calculate variables
        self.Y = ob.dimensions[1]
        self.radius = calculate_icosphere_radius(ob)
        self.subdivisions = int(log(len(ob.data.polygons)/20, 4)+1)
        if not ob.data.uv_layers:
            self.b_UV = False

        # after we're done we unhide modifiers in the viewport if they weren't hidden
        if modifiers_changed:
            show_or_hide_modifiers_in_viewport(ob, True)

        if applied_rotation:

            # unlike other objects icosphere only needs to be rotated on Z for 180
            self.saved_rot = rotate_around_axis_followed_by_euler_rotation(
                "Z", pi, self.saved_rot)

            # if the user invokes the operator but doesn't do anything and clicks away instead of pressing ok-> execute doesn't go off
            # we're force calling execute to fix the rotation
            self.from_check = True
            self.execute(context)

        restore_origin(self.origin)

        # Show operator in bottom left corner if user clicked away
        if self.operator_called_from_cancel:
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        # Popup window
        else:
            return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):

        replace_icosphere(self.subdivisions, self.radius, self.saved_loc,
                          self.saved_rot, self.align, self.b_UV, self.origin)

        # if execute was ran from check function set to false so execute can run from there again
        if self.from_check:
            self.from_check = False
        # if execute was ran from clicking "OK" or clicking away then disable check from running it again
        else:
            self.execute_on_check = False

        return {'FINISHED'}


class RePrimitiveTorus(Operator):
    """
    Tweak torus operator
    """
    bl_idname = "object.reprimitive_torus"
    bl_label = "Tweak Torus"
    bl_options = {'REGISTER', 'UNDO', 'PRESET', 'INTERNAL'}

    # two bool checks to stop executing code twice from "check" function once OK is pressed or the user clicked outside of the window popup
    from_check = False
    execute_on_check = True

    # create default values
    saved_loc = Vector((0, 0, 0))
    saved_rot = Euler((0, 0, 0))
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

    # bool to know whether operator was called from cancel(clicking away from the popup)
    operator_called_from_cancel: BoolProperty(
        name='',
        default=False)

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

    # this function lets us show changes from window popup live
    def check(self, context):
        # this will only run ---BEFORE--- "OK" button was pressed / user clicked outside of the window popup
        # this is how we prevent the execute from running twice, because once the operator isn't in a window popup but rather locked in the bottom left corner check is still getting called and we don't need it
        if self.execute_on_check:
            self.from_check = True
            self.execute(context)
        return True

    def cancel(self, context):
        # calling the operator again after user clicked outside of the popup but this time we're also letting it know we called it from cancel
        bpy.ops.object.reprimitive_torus(
            'INVOKE_DEFAULT', operator_called_from_cancel=True)

    def modal(self, context, event):
        return {'FINISHED'}

    def invoke(self, context, event):

        applied_rotation = False
        ob = context.active_object

        # before any calculations are done we first hide modifiers in the viewport
        modifiers_changed = show_or_hide_modifiers_in_viewport(ob, False)

        # save location and rotation
        self.saved_loc, self.saved_rot, self.origin = save_location_rotation(
            ob)
        self.align = "WORLD"

        if applied_rotation_torus(ob):

            # if the rotation was applied we fix it so it's truly (0,0,0)
            applied_rotation = True
            bpy.ops.object.fix_applied_rotation_auto()

            # The cube we spawned using the custom operator holds the true object rotation
            self.saved_rot = Euler(
                context.scene.objects[CUBE_NAME].rotation_euler)
            ob.rotation_euler = self.saved_rot
            bpy.data.meshes.remove(bpy.data.meshes[CUBE_NAME])

        # calculate variables
        self.major_segments = calculate_torus_major_segments(ob)
        self.minor_segments = len(ob.data.vertices)//self.major_segments
        tip_vert, neighbour_vert = find_tip_and_neighbour_vert(ob)
        self.minor_radius = calculate_polygon_radius(
            self.minor_segments, tip_vert, neighbour_vert)

        if not context.object.data.uv_layers:
            self.b_UV = False

        # save location, reset it and apply it, we need this for the next part because we're comparing distance to (0,0,0)
        saved_loc = Vector(ob.location)
        ob.location = (0, 0, 0)
        bpy.ops.object.transform_apply(
            location=True, rotation=False, scale=False)

        # subtract minor radius from the distance between first selected vert and the middle
        self.major_radius = vector_distance(
            tip_vert, Vector((0, 0, 0))) - self.minor_radius

        # restore location
        ob.location = saved_loc

        # after we're done we unhide modifiers in the viewport if they weren't hidden
        if modifiers_changed:
            show_or_hide_modifiers_in_viewport(ob, True)

        # if the rotation was applied first rotate it by offset on Z, then rotate based on saved rotation
        # look at https://drive.google.com/file/d/1xI0NubgaogZtGhrnmRr2wZmjqGRCSeW4/view?usp=sharing
        if applied_rotation:

            # if you were to cut torus on both X and Y and the quarter piece you get was symmetrical to itself
            if self.major_segments % 4 == 0:
                z_offset = calculate_z_offset(self.major_segments)
                self.saved_rot = rotate_around_axis_followed_by_euler_rotation(
                    'Z', z_offset, self.saved_rot)

            # if torus is symmetrical on both X and Y but the quarter piece isn't symmetrical
            elif self.major_segments % 2 == 0:
                self.saved_rot = rotate_around_axis_followed_by_euler_rotation(
                    'Z', pi/2, self.saved_rot)

            # if torus is only symmetrical on 1 axis
            else:
                self.saved_rot = rotate_around_axis_followed_by_euler_rotation(
                    'Z', pi, self.saved_rot)

            # if the user invokes the operator but doesn't do anything and clicks away instead of pressing ok-> execute doesn't go off
            # we're force calling execute to fix the rotation
            self.from_check = True
            self.execute(context)

        restore_origin(self.origin)

        # Show operator in bottom left corner if user clicked away
        if self.operator_called_from_cancel:
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        # Popup window
        else:
            return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):

        replace_torus(self.major_segments, self.minor_segments, self.major_radius, self.minor_radius,
                      self.saved_loc, self.saved_rot, self.align, self.b_UV, self.origin)

        # if execute was ran from check function set to false so execute can run from there again
        if self.from_check:
            self.from_check = False
        # if execute was ran from clicking "OK" or clicking away then disable check from running it again
        else:
            self.execute_on_check = False

        return {'FINISHED'}


class RePrimitiveUVSphere(Operator):
    """
    Tweak UVSphere operator
    """
    bl_idname = "object.reprimitive_sphere"
    bl_label = "Tweak UVSphere"
    bl_options = {'REGISTER', 'UNDO', 'PRESET', 'INTERNAL'}

    # two bool checks to stop executing code twice from "check" function once OK is pressed or the user clicked outside of the window popup
    from_check = False
    execute_on_check = True

    # create default values
    saved_loc = Vector((0, 0, 0))
    saved_rot = Euler((0, 0, 0))
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

    # bool to know whether operator was called from cancel(clicking away from the popup)
    operator_called_from_cancel: BoolProperty(
        name='',
        default=False)

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

    # this function lets us show changes from window popup live
    def check(self, context):
        # this will only run ---BEFORE--- "OK" button was pressed / user clicked outside of the window popup
        # this is how we prevent the execute from running twice, because once the operator isn't in a window popup but rather locked in the bottom left corner check is still getting called and we don't need it
        if self.execute_on_check:
            self.from_check = True
            self.execute(context)
        return True

    def cancel(self, context):
        # calling the operator again after user clicked outside of the popup but this time we're also letting it know we called it from cancel
        bpy.ops.object.reprimitive_sphere(
            'INVOKE_DEFAULT', operator_called_from_cancel=True)

    def invoke(self, context, event):

        applied_rotation = False
        ob = context.active_object

        # before any calculations are done we first hide modifiers in the viewport
        modifiers_changed = show_or_hide_modifiers_in_viewport(ob, False)

        # save location and rotation
        self.saved_loc, self.saved_rot, self.origin = save_location_rotation(
            ob)
        self.align = "WORLD"

        if applied_rotation_sphere(ob):

            # if the rotation was applied we fix it so it's truly (0,0,0)
            applied_rotation = True
            bpy.ops.object.fix_applied_rotation_auto()

            # The cube we spawned using the custom operator holds the true object rotation
            self.saved_rot = Euler(
                context.scene.objects[CUBE_NAME].rotation_euler)
            ob.rotation_euler = self.saved_rot
            bpy.data.meshes.remove(bpy.data.meshes[CUBE_NAME])

        # calculate variables
        self.depth = ob.dimensions[2]
        self.radius = self.depth/2
        self.segments = calculate_sphere_segments(ob)
        self.rings = len(ob.data.polygons)//self.segments

        if not context.object.data.uv_layers:
            self.b_UV = False

        # after we're done we unhide modifiers in the viewport if they weren't hidden
        if modifiers_changed:
            show_or_hide_modifiers_in_viewport(ob, True)

        # we don't have to fix the rotation if edges go through Y axis by default
        if applied_rotation and (self.segments-2) % 4 != 0:

            # if uneven we can just rotate on Z by 90 degrees
            if self.segments % 2 != 0:
                self.saved_rot = rotate_around_axis_followed_by_euler_rotation(
                    'Z', pi/2, self.saved_rot)

            # otherwise we have to calculate the angle between sides and divide it with -2
            else:
                z_offset = calculate_z_offset(self.segments)
                self.saved_rot = rotate_around_axis_followed_by_euler_rotation(
                    'Z', z_offset, self.saved_rot)

            # if the user invokes the operator but doesn't do anything and clicks away instead of pressing ok-> execute doesn't go off
            # we're force calling execute to fix the rotation
            self.from_check = True
            self.execute(context)

        restore_origin(self.origin)

        # Show operator in bottom left corner if user clicked away
        if self.operator_called_from_cancel:
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        # Popup window
        else:
            return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):

        replace_uv_sphere(self.segments, self.rings, self.radius,
                          self.saved_loc, self.saved_rot, self.align, self.b_UV, self.origin)

        # if execute was ran from check function set to false so execute can run from there again
        if self.from_check:
            self.from_check = False
        # if execute was ran from clicking "OK" or clicking away then disable check from running it again
        else:
            self.execute_on_check = False

        return {'FINISHED'}


class FixAppliedRotationAuto(Operator):
    """ Fixes applied rotation and keeps a cube that we use to rotate the main object, user can't call manually call this class"""
    bl_idname = "object.fix_applied_rotation_auto"
    bl_label = "Fix Applied Rotation"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):

        # Save original object ref and its parent, then unparent and save location
        ob = context.active_object
        parent = ob.parent
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        saved_location = Vector(ob.location)

        # Set the location to 0 so some of the smart selection that compares to the (0,0,0) Vector would work
        ob.location = (0, 0, 0)

        # Save view
        rv = context.space_data.region_3d
        matrix = rv.view_matrix

        # Use smart selection when in object mode, only works for simple objects
        if context.mode == 'OBJECT':

            # Enter edit mode and deselect everything, then change selection to vertices
            bpy.ops.object.editmode_toggle()
            bpy.ops.mesh.select_all(action='DESELECT')
            context.tool_settings.mesh_select_mode = (True, False, False)
            smart_selection(context.active_object)

        # Use whatever is selected, if nothing is then we use smart selection just like in object mode
        elif context.mode == 'EDIT_MESH':

            # Reenter edit mode to confirm the selection
            bpy.ops.object.editmode_toggle()
            bpy.ops.object.editmode_toggle()

            # Is nothing selected?
            if len([v for v in context.active_object.data.vertices if v.select]) == 0:
                smart_selection(context.active_object)

            # Are more than 2 faces selected? We have to flatten the selected faces into 1
            elif len([f for f in context.active_object.data.polygons if f.select]) > 2:

                bpy.ops.mesh.duplicate()
                bpy.ops.transform.resize(value=(1, 1, 0), orient_type='NORMAL')
                bpy.ops.transform.translate(value=(0, 0, 2))
                bpy.ops.mesh.dissolve_edges()

                # Align view to the selected face, then delete it
                bpy.ops.view3d.view_axis(type='TOP', align_active=True)
                bpy.ops.mesh.delete(type='EDGE')

            # Use whatever is selected
            else:
                bpy.ops.view3d.view_axis(type='TOP', align_active=True)

        # Deselect all faces and return to object mode
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.editmode_toggle()

        # Spawn two cubes:
        # 1. used to fix the rotation so it's truly (0,0,0)
        # 2. store the rotation we find out an applied object had, we will read from this cube since we can't return values from operators
        bpy.ops.mesh.primitive_cube_add(location=saved_location, align='VIEW')
        context.active_object.name = CUBE_NAME
        context.active_object.data.name = CUBE_NAME

        # cube number 1, we use this one in this operator
        bpy.ops.mesh.primitive_cube_add(location=saved_location, align='VIEW')
        cube = context.active_object
        # +1 because two objects can't share the same mesh name
        cube.data.name = CUBE_NAME+"1"

        # Deselect everything and select original object, followed by the cube, then parent it to the cube
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        cube.select_set(True)
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)

        # Deselect everything again and select the cube
        bpy.ops.object.select_all(action='DESELECT')
        cube.select_set(True)

        # Reset rotation of the cube
        bpy.ops.object.rotation_clear(clear_delta=False)

        # Deselect everything again and select the original object
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)

        # Clear parent and keep transform, after that apply the rotation
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        bpy.ops.object.transform_apply(
            location=False, rotation=True, scale=False)

        # Delete the helper cube
        bpy.data.meshes.remove(bpy.data.meshes[CUBE_NAME+"1"])

        # restore saved view and reselect the original object
        rv.view_perspective = 'PERSP'
        rv.view_matrix = matrix
        context.view_layer.objects.active = ob

        # Restore original location and parent if it existed
        ob.location = saved_location
        if parent:
            ob.parent = parent
            ob.matrix_parent_inverse = parent.matrix_world.inverted()

        return {'FINISHED'}


class FixAppliedRotation(Operator):
    """ Fix applied rotation so it is truly (0,0,0). """
    bl_idname = "object.fix_applied_rotation"
    bl_label = "Fix Applied Rotation"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object != None

    def execute(self, context):

        ob = context.active_object

        # For torus we have to fix the location first before fixing the rotation
        if (ob.name.startswith(localization_torus)):
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')

        # The cube we spawned using the custom operator holds the true object rotation
        bpy.ops.object.fix_applied_rotation_auto()
        ob.rotation_euler = Euler(
            context.scene.objects[CUBE_NAME].rotation_euler)
        bpy.data.meshes.remove(bpy.data.meshes[CUBE_NAME])

        # For a cone we have to fix the origin along with saving its location and rotation
        if (ob.name.startswith(localization_cone)):
            ob.location, ob.rotation_euler, origin = fix_cone_origin_and_save_location_rotation(
                ob, True)
        else:
            ob.location, ob.rotation_euler, origin = save_location_rotation(ob)

        # Every object has a different offset after fixing the rotation
        Z_offset_ob(ob)
        bpy.ops.object.transform_apply(
            location=False, rotation=True, scale=False)

        restore_origin(origin)

        return {'FINISHED'}
