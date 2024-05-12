from bpy.types import AddonPreferences
from bpy.props import BoolProperty, IntProperty
from . import addon_updater_ops
import rna_keymap_ui


@addon_updater_ops.make_annotations
class RePrimitivePrefs(AddonPreferences):
    bl_idname = __package__

    # Addon updater preferences.

    auto_check_update = BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False)

    updater_interval_months = IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0)

    updater_interval_days = IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7,
        min=0,
        max=31)

    updater_interval_hours = IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23)

    updater_interval_minutes = IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59)

    # panel properties
    show_reprimitive_panel: BoolProperty(
        name='Show Panel',
        default=True,
    )

    def draw(self, context):
        layout = self.layout

        # Updater draw function, could also pass in col as third arg.
        addon_updater_ops.update_settings_ui(self, context)

        # panel-----------------------------------------------------------------------------
        split = layout.split(factor=0.2)
        col_1 = split.column()
        col_2 = split.column()
        col_1.label(text='Show Panel')
        col_2.prop(self, 'show_reprimitive_panel', text='')

        # hotkeys---------------------------------------------------------------------------
        box = layout.box()
        box.label(text='Hotkey')
        wm = context.window_manager
        kc = wm.keyconfigs.user
        km = kc.keymaps['3D View']

        # Reprimitive
        kmi = km.keymap_items.get('object.reprimitive')
        box.context_pointer_set("keymap", km)
        rna_keymap_ui.draw_kmi([], kc, km, kmi, box, 0)

        # Socials and marketplace-----------------------------------------------------------
        row = layout.row(align=True)
        split = row.split(factor=0.5)
        col_1 = split.column(align=True)
        col_2 = split.column(align=True)
        col_1.alignment = 'CENTER'
        col_2.alignment = 'CENTER'

        box = col_1.box()
        box.scale_y = 0.6
        box.label(text='Support me on:')
        col_1.operator(
            "wm.url_open",
            text='Gumroad').url = 'https://app.gumroad.com/exzact7'
        col_1.operator(
            "wm.url_open",
            text='Blender Market').url = 'https://blendermarket.com/creators/exzact7'
        col_1.operator(
            "wm.url_open",
            text='Ko-fi').url = 'https://ko-fi.com/exzact7'

        box = col_2.box()
        box.scale_y = 0.6
        box.label(text='Follow Me:')
        col_2.operator(
            "wm.url_open",
            text='YouTube').url = 'https://www.youtube.com/channel/UCm5Nt3WIh1i1z-QB7H3zzkQ'
        col_2.operator(
            "wm.url_open",
            text='Instagram').url = 'https://www.instagram.com/exzact7'
        col_2.operator(
            "wm.url_open",
            text='Twitch').url = 'https://www.twitch.tv/exzact7'
