import bpy
from .core import *
from bpy.types import Operator
from bpy.props import BoolProperty, IntProperty, EnumProperty, FloatProperty, FloatVectorProperty


class RePrimitive(Operator):
    """ Main reprimitive operator, it decides which other operator gets called based on their type """
    bl_idname = "object.reprimitive"
    bl_label = "Tweak Primitives"
    bl_description = "Tweak Primitives"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and get_object_property(context.object, 'ob_type') is not None

    def execute(self, context):
        match get_object_property(context.object, 'ob_type'):
            case 'cylinder':
                bpy.ops.object.reprimitive_cylinder('INVOKE_DEFAULT')
            case 'circle':
                bpy.ops.object.reprimitive_circle('INVOKE_DEFAULT')
            case 'cone':
                bpy.ops.object.reprimitive_cone('INVOKE_DEFAULT')
            case 'torus':
                bpy.ops.object.reprimitive_torus('INVOKE_DEFAULT')
            case 'sphere':
                bpy.ops.object.reprimitive_sphere('INVOKE_DEFAULT')
            case 'icosphere':
                bpy.ops.object.reprimitive_icosphere('INVOKE_DEFAULT')

        return {'FINISHED'}


class RePrimitiveCircle(Operator):
    bl_idname = "object.reprimitive_circle"
    bl_label = "Tweak Circle"
    bl_options = {'REGISTER', 'UNDO', 'PRESET', 'INTERNAL'}

    vertices: IntProperty(
        name="Vertices",
        default=-1,
        soft_min=3,
        soft_max=500,
        min=3,
        max=500,
    )

    fill_type: EnumProperty(
        name="Base Fill Type",
        description="Select an option",
        items=[('NOTHING', "Nothing", "Don't fill at all"),
               ('NGON', "N-Gon", "Use n-gons"),
               ('TRIFAN', "Triangle Fan", "Use triangle fans")],
        default='NOTHING',
    )

    radius: FloatProperty(
        name="Radius",
        default=1,
        soft_min=0.001,
        min=0,
        subtype='DISTANCE',
        unit='LENGTH',
    )

    calc_uvs: BoolProperty(
        name="Generate UVs",
        description="Generate a default UV map",
        default=True,
    )

    align: EnumProperty(
        name="Align",
        description="Select an option",
        items=[('WORLD', "World", "Align the new object to the world"),
               ('VIEW', "View", "Align the new object to the view"),
               ('CURSOR', "3D Cursor", "Use the 3d cursor orientation for the new object")],
        default='WORLD',
    )

    location: FloatVectorProperty(
        name="Location",
        subtype='TRANSLATION',
    )

    rotation: FloatVectorProperty(
        name="Rotation",
        subtype='EULER',
    )

    def draw(self, context):
        layout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.separator()

        layout.prop(self, "vertices")
        layout.prop(self, "radius")
        layout.prop(self, "fill_type")
        layout.prop(self, "calc_uvs")
        layout.prop(self, "align")

        layout.separator()

        layout.prop(self, "location")
        layout.prop(self, "rotation")

    def invoke(self, context, event):
        ob = context.active_object

        children = save_and_unparent_children(ob.children)

        self.calc_uvs = get_object_property(ob, 'uv')
        self.align = get_object_property(ob, 'align')
        self.fill_type = get_object_property(ob, 'fill')
        self.radius = get_object_property(ob, 'radius')
        self.rotation = get_object_rotation(ob)

        user_input = self.vertices != -1
        if not user_input:  # No input, read verts from the object properties
            self.vertices = get_object_property(ob, 'vertices')

        self.location, self.difference = get_ob_original_location_and_difference(
            ob, vertices=self.vertices, fill_type=self.fill_type, radius=self.radius, rotation=self.rotation)

        for child in children:
            reparent(child, ob)

        # If user called the operator with custom input execute immediately to see it applied
        if user_input:
            self.execute(context)

        return context.window_manager.invoke_props_popup(self, event)

    def execute(self, context):
        replace_object(vertices=self.vertices, radius=self.radius, fill_type=self.fill_type, align=self.align, calc_uvs=self.calc_uvs,
                       location=self.location, rotation=self.rotation, difference=self.difference)
        return {'FINISHED'}


class RePrimitiveCone(Operator):
    bl_idname = "object.reprimitive_cone"
    bl_label = "Tweak Cone"
    bl_options = {'REGISTER', 'UNDO', 'PRESET', 'INTERNAL'}

    vertices: IntProperty(
        name="Vertices",
        default=-1,
        soft_min=3,
        soft_max=500,
        min=3,
        max=500,
    )

    depth: FloatProperty(
        name="Depth",
        default=1,
        soft_min=0.001,
        subtype='DISTANCE',
        unit='LENGTH',
    )

    end_fill_type: EnumProperty(
        name="Base Fill Type",
        description="Select an option",
        items=[('NOTHING', "Nothing", "Don't fill at all"),
               ('NGON', "N-Gon", "Use n-gons"),
               ('TRIFAN', "Triangle Fan", "Use triangle fans")],
        default='NGON',
    )

    radius1: FloatProperty(
        name="Radius1",
        default=1,
        soft_min=0,
        min=0,
        subtype='DISTANCE',
        unit='LENGTH',
    )

    radius2: FloatProperty(
        name="Radius2",
        default=0,
        soft_min=0,
        min=0,
        subtype='DISTANCE',
        unit='LENGTH',
    )

    calc_uvs: BoolProperty(
        name="Generate UVs",
        description="Generate a default UV map",
        default=True,
    )

    align: EnumProperty(
        name="Align",
        description="Select an option",
        items=[('WORLD', "World", "Align the new object to the world"),
               ('VIEW', "View", "Align the new object to the view"),
               ('CURSOR', "3D Cursor", "Use the 3d cursor orientation for the new object")],
        default='WORLD',
    )

    location: FloatVectorProperty(
        name="Location",
        subtype='TRANSLATION',
    )

    rotation: FloatVectorProperty(
        name="Rotation",
        subtype='EULER',
    )

    def draw(self, context):
        layout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.separator()

        layout.prop(self, "vertices")
        layout.prop(self, "radius1")
        layout.prop(self, "radius2")
        layout.prop(self, "depth")
        layout.prop(self, "end_fill_type")
        layout.prop(self, "calc_uvs")
        layout.prop(self, "align")

        layout.separator()

        layout.prop(self, "location")
        layout.prop(self, "rotation")

    def invoke(self, context, event):
        ob = bpy.context.object

        children = save_and_unparent_children(ob.children)

        self.radius1 = get_object_property(ob, 'radius1')
        self.radius2 = get_object_property(ob, 'radius2')
        self.depth = get_object_property(ob, 'depth')
        self.end_fill_type = get_object_property(ob, 'fill')
        self.align = get_object_property(ob, 'align')
        self.calc_uvs = get_object_property(ob, 'uv')
        self.rotation = get_object_rotation(ob)

        user_input = self.vertices != -1
        if not user_input:  # No input, read verts from the object properties
            self.vertices = get_object_property(ob, 'vertices')

        self.location, self.difference = get_ob_original_location_and_difference(
            ob, vertices=self.vertices, radius1=self.radius1, radius2=self.radius2, depth=self.depth, end_fill_type=self.end_fill_type, rotation=self.rotation)

        for child in children:
            reparent(child, ob)

        if user_input:  # If user called the operator with custom input execute immediately to see it applied
            self.execute(context)

        return context.window_manager.invoke_props_popup(self, event)

    def execute(self, context):
        replace_object(vertices=self.vertices, radius1=self.radius1, radius2=self.radius2, depth=self.depth, end_fill_type=self.end_fill_type, align=self.align, calc_uvs=self.calc_uvs,
                       location=self.location, rotation=self.rotation, difference=self.difference)
        return {'FINISHED'}


class RePrimitiveCylinder(Operator):
    bl_idname = "object.reprimitive_cylinder"
    bl_label = "Tweak Cylinder"
    bl_options = {'REGISTER', 'UNDO', 'PRESET', 'INTERNAL'}

    vertices: IntProperty(
        name="Vertices",
        default=-1,
        soft_min=3,
        soft_max=500,
        min=3,
        max=500,
    )

    depth: FloatProperty(
        name="Depth",
        default=2,
        soft_min=0.001,
        min=0,
        subtype='DISTANCE',
        unit='LENGTH'
    )

    end_fill_type: EnumProperty(
        name="Cap Fill Type", description="Select an option",
        items=[('NOTHING', "Nothing", "Don't fill at all"),
               ('NGON', "N-Gon", "Use n-gons"),
               ('TRIFAN', "Triangle Fan", "Use triangle fans")],
        default='NGON',
    )

    radius: FloatProperty(
        name="Radius",
        default=1,
        soft_min=0.001,
        min=0,
        subtype='DISTANCE',
        unit='LENGTH',
    )

    calc_uvs: BoolProperty(
        name="Generate UVs",
        description="Generate a default UV map",
        default=True,
    )

    align: EnumProperty(
        name="Align",
        description="Select an option",
        items=[('WORLD', "World", "Align the new object to the world"),
               ('VIEW', "View", "Align the new object to the view"),
               ('CURSOR', "3D Cursor", "Use the 3d cursor orientation for the new object")],
        default='WORLD',
    )

    location: FloatVectorProperty(
        name="Location",
        subtype='TRANSLATION',
    )

    rotation: FloatVectorProperty(
        name="Rotation",
        subtype='EULER',
    )

    def draw(self, context):
        layout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.separator()

        layout.prop(self, "vertices")
        layout.prop(self, "radius")
        layout.prop(self, "depth")
        layout.prop(self, "end_fill_type")
        layout.prop(self, "calc_uvs")
        layout.prop(self, "align")

        layout.separator()

        layout.prop(self, "location")
        layout.prop(self, "rotation")

    def invoke(self, context, event):
        ob = context.active_object

        children = save_and_unparent_children(ob.children)

        self.calc_uvs = get_object_property(ob, 'uv')
        self.align = get_object_property(ob, 'align')
        self.end_fill_type = get_object_property(ob, 'fill')
        self.radius = get_object_property(ob, 'radius')
        self.depth = get_object_property(ob, 'depth')
        self.rotation = get_object_rotation(ob)

        user_input = self.vertices != -1
        if not user_input:  # No input, read verts from the object properties
            self.vertices = get_object_property(ob, 'vertices')

        self.location, self.difference = get_ob_original_location_and_difference(
            ob, vertices=self.vertices, radius=self.radius, depth=self.depth, end_fill_type=self.end_fill_type, rotation=self.rotation)

        for child in children:
            reparent(child, ob)

        # If user called the operator with custom input execute immediately to see it applied
        if user_input:
            self.execute(context)

        return context.window_manager.invoke_props_popup(self, event)

    def execute(self, context):
        replace_object(vertices=self.vertices, radius=self.radius, depth=self.depth, end_fill_type=self.end_fill_type, align=self.align, calc_uvs=self.calc_uvs,
                       location=self.location, rotation=self.rotation, difference=self.difference)

        return {'FINISHED'}


class RePrimitiveTorus(Operator):
    bl_idname = "object.reprimitive_torus"
    bl_label = "Tweak Torus"
    bl_options = {'REGISTER', 'UNDO', 'PRESET', 'INTERNAL'}

    def mode_update_callback(self, _context):
        if self.mode == 'EXT_INT':
            self.abso_major_rad = self.major_radius + self.minor_radius
            self.abso_minor_rad = self.major_radius - self.minor_radius
        else:
            self.major_radius = (self.abso_major_rad + self.abso_minor_rad) / 2
            self.minor_radius = (self.abso_major_rad - self.abso_minor_rad) / 2

    major_segments: IntProperty(
        name="Major Segments",
        description="Number of segments for the main ring of the torus",
        min=3, max=256,
        default=48,
    )
    minor_segments: IntProperty(
        name="Minor Segments",
        description="Number of segments for the minor ring of the torus",
        min=3, max=256,
        default=12,
    )
    mode: EnumProperty(
        name="Dimensions Mode",
        items=(
            ('MAJOR_MINOR', "Major/Minor",
             "Use the major/minor radii for torus dimensions"),
            ('EXT_INT', "Exterior/Interior",
             "Use the exterior/interior radii for torus dimensions"),
        ),
        update=mode_update_callback,
    )
    major_radius: FloatProperty(
        name="Major Radius",
        description="Radius from the origin to the center of the cross sections",
        soft_min=0.0, soft_max=100.0,
        min=0.0, max=10_000.0,
        default=1.0,
        subtype='DISTANCE',
        unit='LENGTH',
    )
    minor_radius: FloatProperty(
        name="Minor Radius",
        description="Radius of the torus' cross section",
        soft_min=0.0, soft_max=100.0,
        min=0.0, max=10_000.0,
        default=0.25,
        subtype='DISTANCE',
        unit='LENGTH',
    )
    abso_major_rad: FloatProperty(
        name="Exterior Radius",
        description="Total Exterior Radius of the torus",
        soft_min=0.0, soft_max=100.0,
        min=0.0, max=10_000.0,
        default=1.25,
        subtype='DISTANCE',
        unit='LENGTH',
    )
    abso_minor_rad: FloatProperty(
        name="Interior Radius",
        description="Total Interior Radius of the torus",
        soft_min=0.0, soft_max=100.0,
        min=0.0, max=10_000.0,
        default=0.75,
        subtype='DISTANCE',
        unit='LENGTH',
    )
    generate_uvs: BoolProperty(
        name="Generate UVs",
        description="Generate a default UV map",
        default=True,
    )
    align: EnumProperty(
        name="Align",
        description="Select an option",
        items=[
            ('WORLD', "World", "Align the new object to the world"),
            ('VIEW', "View", "Align the new object to the view"),
            ('CURSOR', "3D Cursor", "Use the 3d cursor orientation for the new object"),
        ],
        default='WORLD',
    )

    location: FloatVectorProperty(
        name="Location",
        subtype='TRANSLATION',
    )

    rotation: FloatVectorProperty(
        name="Rotation",
        subtype='EULER',
    )

    def draw(self, _context):
        layout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.separator()

        layout.prop(self, "major_segments")
        layout.prop(self, "minor_segments")

        layout.separator()

        layout.prop(self, "mode")
        if self.mode == 'MAJOR_MINOR':
            layout.prop(self, "major_radius")
            layout.prop(self, "minor_radius")
        else:
            layout.prop(self, "abso_major_rad")
            layout.prop(self, "abso_minor_rad")

        layout.separator()

        layout.prop(self, "generate_uvs")
        layout.prop(self, "align")
        layout.prop(self, "location")
        layout.prop(self, "rotation")

    def invoke(self, context, event):
        ob = context.active_object

        children = save_and_unparent_children(ob.children)

        self.major_segments = get_object_property(ob, 'major_segments')
        self.minor_segments = get_object_property(ob, 'minor_segments')
        self.mode = get_object_property(ob, 'dimensions_mode')
        self.major_radius = get_object_property(ob, 'major_radius')
        self.minor_radius = get_object_property(ob, 'minor_radius')
        self.abso_major_rad = get_object_property(ob, 'abso_major_rad')
        self.abso_minor_rad = get_object_property(ob, 'abso_minor_rad')
        self.align = get_object_property(ob, 'align')
        self.generate_uvs = get_object_property(ob, 'uv')
        self.rotation = get_object_rotation(ob)
        self.location, self.difference = get_ob_original_location_and_difference(
            ob, major_segments=self.major_segments, minor_segments=self.minor_segments, major_radius=self.major_radius, minor_radius=self.minor_radius, rotation=self.rotation)

        for child in children:
            reparent(child, ob)

        return context.window_manager.invoke_props_popup(self, event)

    def execute(self, context):
        replace_object(major_segments=self.major_segments, minor_segments=self.minor_segments, mode=self.mode, major_radius=self.major_radius, minor_radius=self.minor_radius, abso_major_rad=self.abso_major_rad, abso_minor_rad=self.abso_minor_rad, align=self.align, generate_uvs=self.generate_uvs,
                       location=self.location, rotation=self.rotation, difference=self.difference)
        return {'FINISHED'}


class RePrimitiveUVSphere(Operator):
    bl_idname = "object.reprimitive_sphere"
    bl_label = "Tweak UV Sphere"
    bl_options = {'REGISTER', 'UNDO', 'PRESET', 'INTERNAL'}

    segments: IntProperty(
        name="Segments",
        default=32,
        soft_min=3,
        min=3,
        soft_max=500,
        max=500,
    )

    ring_count: IntProperty(
        name="Rings",
        default=16,
        soft_min=3,
        min=3,
        soft_max=500,
        max=500,
    )

    radius: FloatProperty(
        name="Radius",
        default=1,
        soft_min=0.001,
        min=0,
        subtype='DISTANCE',
        unit='LENGTH',
    )

    calc_uvs: BoolProperty(
        name="Generate UVs",
        description="Generate a default UV map",
        default=True,
    )

    align: EnumProperty(
        name="Align",
        description="Select an option",
        items=[('WORLD', "World", "Align the new object to the world"),
               ('VIEW', "View", "Align the new object to the view"),
               ('CURSOR', "3D Cursor", "Use the 3d cursor orientation for the new object")],
        default='WORLD',
    )

    location: FloatVectorProperty(
        name="Location",
        subtype='TRANSLATION',
    )

    rotation: FloatVectorProperty(
        name="Rotation",
        subtype='EULER',
    )

    def draw(self, context):
        layout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.separator()

        layout.prop(self, "segments")
        layout.prop(self, "ring_count")
        layout.prop(self, "radius")
        layout.prop(self, "calc_uvs")
        layout.prop(self, "align")

        layout.separator()

        layout.prop(self, "location")
        layout.prop(self, "rotation")

    def invoke(self, context, event):
        ob = context.active_object

        children = save_and_unparent_children(ob.children)

        self.segments = get_object_property(ob, 'segments')
        self.ring_count = get_object_property(ob, 'rings')
        self.radius = get_object_property(ob, 'radius')
        self.align = get_object_property(ob, 'align')
        self.calc_uvs = get_object_property(ob, 'uv')
        self.rotation = get_object_rotation(ob)
        self.location, self.difference = get_ob_original_location_and_difference(
            ob, segments=self.segments, ring_count=self.ring_count, radius=self.radius, rotation=self.rotation)

        for child in children:
            reparent(child, ob)

        return context.window_manager.invoke_props_popup(self, event)

    def execute(self, context):
        replace_object(segments=self.segments, ring_count=self.ring_count, radius=self.radius, align=self.align, calc_uvs=self.calc_uvs,
                       location=self.location, rotation=self.rotation, difference=self.difference)
        return {'FINISHED'}


class RePrimitiveIcoSphere(Operator):
    bl_idname = "object.reprimitive_icosphere"
    bl_label = "Tweak Ico Sphere"
    bl_options = {'REGISTER', 'UNDO', 'PRESET', 'INTERNAL'}

    subdivisions: IntProperty(
        name="Subdivisions",
        default=2,
        soft_min=1,
        soft_max=8,
        min=1,
        max=8)

    radius: FloatProperty(
        name="Radius",
        default=1,
        soft_min=0.001,
        min=0,
        subtype='DISTANCE',
        unit='LENGTH',
    )

    calc_uvs: BoolProperty(
        name="Generate UVs",
        description="Generate a default UV map",
        default=True,
    )

    align: EnumProperty(
        name="Align",
        description="Select an option",
        items=[('WORLD', "World", "Align the new object to the world"),
               ('VIEW', "View", "Align the new object to the view"),
               ('CURSOR', "3D Cursor", "Use the 3d cursor orientation for the new object")],
        default='WORLD',
    )

    location: FloatVectorProperty(
        name="Location",
        subtype='TRANSLATION',
    )

    rotation: FloatVectorProperty(
        name="Rotation",
        subtype='EULER',
    )

    def draw(self, context):
        layout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.separator()

        layout.prop(self, "subdivisions")
        layout.prop(self, "radius")
        layout.prop(self, "calc_uvs")
        layout.prop(self, "align")

        layout.separator()

        layout.prop(self, "location")
        layout.prop(self, "rotation")

    def invoke(self, context, event):
        ob = context.active_object

        children = save_and_unparent_children(ob.children)

        self.subdivisions = get_object_property(ob, 'subdivisions')
        self.radius = get_object_property(ob, 'radius')
        self.align = get_object_property(ob, 'align')
        self.calc_uvs = get_object_property(ob, 'uv')
        self.rotation = get_object_rotation(ob)
        self.location, self.difference = get_ob_original_location_and_difference(
            ob, subdivisions=self.subdivisions, radius=self.radius, rotation=self.rotation)

        for child in children:
            reparent(child, ob)

        return context.window_manager.invoke_props_popup(self, event)

    def execute(self, context):
        replace_object(subdivisions=self.subdivisions, radius=self.radius, align=self.align, calc_uvs=self.calc_uvs,
                       location=self.location, rotation=self.rotation, difference=self.difference)
        return {'FINISHED'}
