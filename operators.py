import bpy
from .core import *
from math import log
from bpy.types import Operator, Menu
from bpy.props import BoolProperty, IntProperty, EnumProperty, FloatProperty, FloatVectorProperty


class RePrimitive(Operator):
    bl_idname = "object.reprimitive_pie"
    bl_label = "RePrimitive Pie Menu"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ob = context.active_object
        if ob and ob.type == 'MESH':  # Draw the pie menu only if the active object is a mesh
            ob_type = find_ob_type(ob)
            if ob_type != 'unknown':
                set_hidden_property("str", "ob_type", ob_type)
                bpy.ops.wm.call_menu_pie(name="OBJECT_MT_reprimitive_pie")
        return {'FINISHED'}


class RePrimitiveAuto(Operator):
    bl_idname = "object.reprimitive_auto"
    bl_label = "Tweak Primitives"
    bl_description = "Tweak Primitives"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        match find_ob_type(context.active_object):
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


class RePrimitivePieMenu(Menu):
    bl_idname = "OBJECT_MT_reprimitive_pie"
    bl_label = ""

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        ob_type = get_object_property(context.active_object, 'ob_type')

        pie.separator()  # WEST
        pie.separator()  # EAST

        # SOUTH
        box = pie.box()
        row = box.row()
        row.operator("object.reprimitive_cylinder",
                     depress=ob_type == 'cylinder', text="Cylinder", icon="MESH_CYLINDER")
        draw_buttons(box, "object.reprimitive_cylinder")

        # NORTH
        pie.operator("object.reprimitive_sphere",
                     depress=ob_type == 'sphere', text="UV Sphere", icon='MESH_UVSPHERE')

        # NORTHWEST
        box = pie.box()
        row = box.row()
        row.operator("object.reprimitive_cone",
                     depress=ob_type == 'cone', text="Cone", icon="MESH_CONE")
        draw_buttons(box, "object.reprimitive_cone")

        # NORTHEAST
        box = pie.box()
        row = box.row()
        row.operator("object.reprimitive_circle",
                     depress=ob_type == 'circle', text="Circle", icon="MESH_CIRCLE")
        draw_buttons(box, "object.reprimitive_circle")

        # SOUTHWEST
        pie.operator("object.reprimitive_torus",
                     depress=ob_type == 'torus', text="Torus", icon='MESH_TORUS')

        # SOUTHEAST
        pie.operator("object.reprimitive_icosphere",
                     depress=ob_type == 'icosphere', text="Ico Sphere", icon='MESH_ICOSPHERE')


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
        options={'SKIP_SAVE'},
    )

    rotation: FloatVectorProperty(
        name="Rotation",
        subtype='EULER',
        options={'SKIP_SAVE'},
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
        user_input = self.properties.is_property_set("vertices")

        self.location, self.difference = calculate_object_location_and_difference(
            ob)
        self.calc_uvs = True if ob.data.uv_layers else False

        if (len(ob.data.polygons)) == 0:
            self.fill_type = 'NOTHING'
        elif (len(ob.data.polygons)) == 1:
            self.fill_type = 'NGON'
        else:
            self.fill_type = 'TRIFAN'

        # Have to calculate verts regarldess of input because the rotation depends on proper vert count
        verts = len(ob.data.vertices) - \
            1 if self.fill_type == 'TRIFAN' else len(ob.data.vertices)
        self.radius = calculate_radius(ob)
        self.rotation = calculate_object_rotation(
            ob, ob_type='circle', vertices=verts, fill_type=self.fill_type, radius=self.radius)

        for child in children:
            reparent(child, ob)

        # If user called the operator with custom input overwrite and execute immediately to see it applied
        self.vertices = self.vertices if user_input else verts
        if user_input:
            return self.execute(context)

        return context.window_manager.invoke_props_popup(self, event)

    def execute(self, context):
        replace_object(ob_type='circle', vertices=self.vertices, radius=self.radius, fill_type=self.fill_type, align=self.align, calc_uvs=self.calc_uvs,
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
        soft_min=0.001,
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
        options={'SKIP_SAVE'},
    )

    rotation: FloatVectorProperty(
        name="Rotation",
        subtype='EULER',
        options={'SKIP_SAVE'},
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
        user_input = self.properties.is_property_set("vertices")

        sharp_tipped, verts, self.cut_heights, self.radius1, self.radius2, self.depth, self.end_fill_type = calculate_cone_properties(
            ob)
        self.rotation = calculate_object_rotation(
            ob, ob_type='cone', vertices=verts, radius1=self.radius1, radius2=self.radius2, depth=self.depth, end_fill_type=self.end_fill_type, cut_heights=self.cut_heights, sharp_tipped=sharp_tipped)
        self.calc_uvs = True if ob.data.uv_layers else False
        if sharp_tipped or self.cut_heights:
            self.location, self.difference = calculate_object_location_and_difference_no_origin_to_geometry(
                ob, ob_type='cone', vertices=self.vertices, radius1=self.radius1, radius2=self.radius2, depth=self.depth, end_fill_type=self.end_fill_type, rotation=self.rotation, cut_heights=self.cut_heights)
        else:
            self.location, self.difference = calculate_object_location_and_difference(
                ob)

        for child in children:
            reparent(child, ob)

        # If user called the operator with custom input overwrite and execute immediately to see it applied
        self.vertices = self.vertices if user_input else verts
        if user_input:
            return self.execute(context)

        return context.window_manager.invoke_props_popup(self, event)

    def execute(self, context):
        replace_object(ob_type='cone', vertices=self.vertices, radius1=self.radius1, radius2=self.radius2, depth=self.depth, end_fill_type=self.end_fill_type, align=self.align, calc_uvs=self.calc_uvs,
                       location=self.location, rotation=self.rotation, difference=self.difference, cut_heights=self.cut_heights)

        return {'FINISHED'}


class RePrimitiveCylinder(Operator):
    bl_idname = "object.reprimitive_cylinder"
    bl_label = "Tweak Cylinder"
    bl_options = {'REGISTER', 'UNDO', 'PRESET', 'INTERNAL'}

    vertices: IntProperty(
        name="Vertices",
        default=32,
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
        options={'SKIP_SAVE'},
    )

    rotation: FloatVectorProperty(
        name="Rotation",
        subtype='EULER',
        options={'SKIP_SAVE'},
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
        user_input = self.properties.is_property_set("vertices")

        self.calc_uvs = True if ob.data.uv_layers else False
        verts, self.cut_heights, self.radius, self.depth, self.end_fill_type = calculate_cylinder_properties(
            ob)
        self.rotation = calculate_object_rotation(
            ob, ob_type='cylinder', vertices=verts, radius=self.radius, depth=self.depth, end_fill_type=self.end_fill_type, cut_heights=self.cut_heights)
        self.linked_locations = [a+b for a, b in
                                 [calculate_object_location_and_difference(ob) for ob in get_linked_objects(ob)]]
        self.location, self.difference = calculate_object_location_and_difference_no_origin_to_geometry(
            ob, ob_type='cylinder', vertices=self.vertices, radius=self.radius, depth=self.depth, end_fill_type=self.end_fill_type, rotation=self.rotation, cut_heights=self.cut_heights)

        for child in children:
            reparent(child, ob)

        # If user called the operator with custom input overwrite and execute immediately to see it applied
        self.vertices = self.vertices if user_input else verts
        if user_input:
            return self.execute(context)

        return context.window_manager.invoke_props_popup(self, event)

    def execute(self, context):
        replace_object(ob_type='cylinder', vertices=self.vertices, radius=self.radius, depth=self.depth, end_fill_type=self.end_fill_type, align=self.align, calc_uvs=self.calc_uvs,
                       location=self.location, rotation=self.rotation, difference=self.difference, cut_heights=self.cut_heights)

        new_ob = bpy.context.object
        for loc in self.linked_locations:
            create_linked_ob_at_location(new_ob, loc)

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
        options={'SKIP_SAVE'},
    )

    rotation: FloatVectorProperty(
        name="Rotation",
        subtype='EULER',
        options={'SKIP_SAVE'},
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

        self.location, self.difference = calculate_object_location_and_difference(
            ob)
        self.generate_uvs = True if ob.data.uv_layers else False

        # Select the minor circle, Blender always has verts 0 and 1 forming an edge that goes through it
        select_ring_from_verts(ob, [0, 1])
        selected_verts = get_selected_verts(ob)
        self.minor_segments = len(selected_verts)
        self.major_segments = len(ob.data.polygons) // self.minor_segments
        # Last used mode,, default to major minor
        self.mode = get_object_property(ob, 'dimensions_mode', 'MAJOR_MINOR')
        self.minor_radius = calculate_radius(selected_verts)
        # Blender ordering, indices from 0 <-> minor_segments form a minor ring, then the first next index is a vert on the major circle, and the following are forming another minor circle
        select_ring_from_verts(ob, [0, self.minor_segments])
        self.major_radius = calculate_radius(
            get_selected_verts(ob)) - self.minor_radius
        self.rotation = calculate_object_rotation(
            ob, ob_type='torus', major_segments=self.major_segments, minor_segments=self.minor_segments, major_radius=self.major_radius, minor_radius=self.minor_radius)

        for child in children:
            reparent(child, ob)

        return context.window_manager.invoke_props_popup(self, event)

    def execute(self, context):
        replace_object(ob_type='torus', major_segments=self.major_segments, minor_segments=self.minor_segments, mode=self.mode, major_radius=self.major_radius, minor_radius=self.minor_radius, abso_major_rad=self.abso_major_rad, abso_minor_rad=self.abso_minor_rad, align=self.align, generate_uvs=self.generate_uvs,
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
        options={'SKIP_SAVE'},
    )

    rotation: FloatVectorProperty(
        name="Rotation",
        subtype='EULER',
        options={'SKIP_SAVE'},
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

        self.calc_uvs = True if ob.data.uv_layers else False
        self.location, self.difference = calculate_object_location_and_difference(
            ob)

        self.segments = calculate_sphere_segments(ob)
        self.ring_count = len(ob.data.polygons)//self.segments
        self.radius = calculate_radius(ob)
        self.rotation = calculate_object_rotation(
            ob, ob_type='sphere', segments=self.segments, ring_count=self.ring_count, radius=self.radius)

        for child in children:
            reparent(child, ob)

        return context.window_manager.invoke_props_popup(self, event)

    def execute(self, context):
        replace_object(ob_type='sphere', segments=self.segments, ring_count=self.ring_count, radius=self.radius, align=self.align, calc_uvs=self.calc_uvs,
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
        options={'SKIP_SAVE'},
    )

    rotation: FloatVectorProperty(
        name="Rotation",
        subtype='EULER',
        options={'SKIP_SAVE'},
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

        self.calc_uvs = True if ob.data.uv_layers else False
        self.location, self.difference = calculate_object_location_and_difference(
            ob)

        self.subdivisions = int(log(len(ob.data.polygons)/20, 4)+1)
        self.radius = calculate_radius(ob)
        self.rotation = calculate_object_rotation(
            ob, ob_type='icosphere', subdivisions=self.subdivisions, radius=self.radius)

        for child in children:
            reparent(child, ob)

        return context.window_manager.invoke_props_popup(self, event)

    def execute(self, context):
        replace_object(ob_type='icosphere', subdivisions=self.subdivisions, radius=self.radius, align=self.align, calc_uvs=self.calc_uvs,
                       location=self.location, rotation=self.rotation, difference=self.difference)
        return {'FINISHED'}
