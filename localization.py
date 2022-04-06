# the rest of this code runs once you open blender
import bpy

# set default language to be english, we'll check if it isn't and change all the localization variables
user_language = 'en_US'
localization_all = ('Cylinder', 'Cone', 'Circle',
                    'Torus', 'Sphere', 'Icosphere')
localization_cylinder = ('Cylinder')
localization_cone = ('Cone')
localization_circle = ('Circle')
localization_torus = ('Torus')
localization_sphere = ('Sphere')
localization_icosphere = ('Icosphere')

# if the user enabled translation of objects and the language isn't English then change the user_language variable
if bpy.context.preferences.view.use_translate_new_dataname:
    if bpy.context.preferences.view.language != user_language:
        user_language = bpy.context.preferences.view.language

# if we changed user_language variable in the previous line then change localization for objects
if user_language != 'en_US':
    # spanish
    if user_language == 'es':
        localization_all = ('Cilindro', 'Cono', 'Círculo',
                            'Rosca', 'Sfera', 'Esfera geodésica')
        localization_cylinder = 'Cilindro'
        localization_cone = 'Cono'
        localization_circle = 'Círculo'
        localization_torus = 'Rosca'
        localization_sphere = 'Sfera'
        localization_icosphere = 'Esfera geodésica'
    # japanese
    elif user_language == 'ja_JP':
        localization_all = ('円柱', '円錐', '円',
                            'トーラス', '球', 'ICO球')
        localization_cylinder = '円柱'
        localization_cone = '円錐'
        localization_circle = '円'
        localization_torus = 'トーラス'
        localization_sphere = '球'
        localization_icosphere = 'ICO球'
    # simplified chinese
    elif user_language == 'zh_CN':
        localization_all = ('柱体', '锥体', '圆环', '环体', '球体', '棱角球')
        localization_cylinder = ('柱体')
        localization_cone = ('锥体')
        localization_circle = ('圆环')
        localization_torus = ('环体')
        localization_sphere = ('球体')
        localization_icosphere = ('棱角球')
    # slovak
    elif user_language == 'sk_SK':
        localization_all = ('Valec', 'Kužeľ', 'Kruh',
                            'Prstenec', 'Guľa', 'Mnohosten')
        localization_cylinder = ('Valec')
        localization_cone = ('Kužeľ')
        localization_circle = ('Kruh')
        localization_torus = ('Prstenec')
        localization_sphere = ('Guľa')
        localization_icosphere = ('Mnohosten')
    # vietnamese
    elif user_language == 'vi_VN':
        localization_all = ('Hình Trụ', 'Hình Nón', 'Vòng Tròn',
                            'Hình Xuyến', 'Hình Cầu', 'Hình Cầu Diện')
        localization_cylinder = ('Hình Trụ')
        localization_cone = ('Hình Nón')
        localization_circle = ('Vòng Tròn')
        localization_torus = ('Hình Xuyến')
        localization_sphere = ('Hình Cầu')
        localization_icosphere = ('Hình Cầu Diện')
    # arabic
    elif user_language == 'ar_EG':
        localization_all = ('ﺔﻧﺍﻮﻄﺳﺃ', 'ﻁﻭﺮﺨﻣ', 'ﺓﺮﺋﺍﺩ',
                            'Torus', 'ﺓﺮﻛ', '(ﺕﺎﺜﻠﺜﻣ)ﺓﺮﻛ')
        localization_cylinder = ('柱体')
        localization_cone = ('锥体')
        localization_circle = ('圆环')
        # blender bug, torus stays named torus
        localization_torus = ('Torus')
        localization_sphere = ('球体')
        localization_icosphere = ('棱角球')
    # czech
    elif user_language == 'cs_CZ':
        localization_all = ('Válec', 'Kužel', 'Kruh',
                            'Torus', 'Koule', 'IcoKoule')
        localization_cylinder = ('Válec')
        localization_cone = ('Kužel')
        localization_circle = ('Kruh')
        localization_torus = ('Torus')
        localization_sphere = ('Koule')
        localization_icosphere = ('IcoKoule')
    # german
    elif user_language == 'sk_SK':
        localization_all = ('Zylinder', 'Kegel', 'Kreis',
                            'Torus', 'Kugel', 'Icokugel')
        localization_cylinder = ('Zylinder')
        localization_cone = ('Kegel')
        localization_circle = ('Kreis')
        localization_torus = ('Torus')
        localization_sphere = ('Kugel')
        localization_icosphere = ('Icokugel')
    # french
    elif user_language == 'fr_FR':
        localization_all = ('Cylindre', 'Cône', 'Cercle',
                            'Tore', 'Sphère', 'Icosphère')
        localization_cylinder = ('Cylindre')
        localization_cone = ('Cône')
        localization_circle = ('Cercle')
        localization_torus = ('Tore')
        localization_sphere = ('Sphère')
        localization_icosphere = ('Icosphère')
    # italian
    elif user_language == 'it_IT':
        localization_all = ('Cilindro', 'Cono', 'Cerchio',
                            'Torus', 'Sfera', 'Icosfera')
        localization_cylinder = ('Cylindre')
        localization_cone = ('Cône')
        localization_circle = ('Cercle')
        localization_torus = ('Tore')
        localization_sphere = ('Sphère')
        localization_icosphere = ('Icosphère')
    # korean
    elif user_language == 'ko_KR':
        localization_all = ('실린더', '원뿔', '원형',
                            'Torus', '구체', '아이코스피어')
        localization_cylinder = ('실린더')
        localization_cone = ('원뿔')
        localization_circle = ('원형')
        # blender bug again, torus name stays the same
        localization_torus = ('Torus')
        localization_sphere = ('구체')
        localization_icosphere = ('아이코스피어')
    # brazilian portuguese
    elif user_language == 'pt_BR':
        localization_all = ('Cilindro', 'Cone', 'Círculo',
                            'Toróide', 'Esfera UV', 'Esfera icosaédrica')
        localization_cylinder = ('Cilindro')
        localization_cone = ('Cone')
        localization_circle = ('Círculo')
        localization_torus = ('Toróide')
        localization_sphere = ('Esfera UV')
        localization_icosphere = ('Esfera icosaédrica')
    # portuguese
    elif user_language == 'pt_PT':
        localization_all = ('Cilindro', 'Cone', 'Círculo',
                            'Torus', 'Esfera UV', 'Esfera icosaédrica')
        localization_cylinder = ('Cilindro')
        localization_cone = ('Cone')
        localization_circle = ('Círculo')
        # blender bug again, torus name stays the same
        localization_torus = ('Torus')
        localization_sphere = ('Esfera UV')
        localization_icosphere = ('Esfera icosaédrica')
    # russian
    elif user_language == 'ru_RU':
        localization_all = ('Цилиндр', 'Конус', 'Окружность',
                            'Torus', 'Сфера', 'Икосфера')
        localization_cylinder = ('Цилиндр')
        localization_cone = ('Конус')
        localization_circle = ('Окружность')
        # blender bug again, torus name stays the same
        localization_torus = ('Torus')
        localization_sphere = ('Сфера')
        localization_icosphere = ('Икосфера')
    # ukrainian
    elif user_language == 'uk_UA':
        localization_all = ('Циліндр', 'Конус', 'Коло',
                            'Тор', 'Сфера', 'Iкосфера')
        localization_cylinder = ('Циліндр')
        localization_cone = ('Конус')
        localization_circle = ('Коло')
        localization_torus = ('Тор')
        localization_sphere = ('Сфера')
        localization_icosphere = ('Iкосфера')
    # traditional chinese
    elif user_language == 'zh_TW':
        localization_all = ('圓柱體', '圓錐體', '圓形',
                            'Torus', 'Сфера', 'Iкосфера')
        localization_cylinder = ('圓柱體')
        localization_cone = ('圓錐體')
        localization_circle = ('圓形')
        # blender bug again, torus name stays the same
        localization_torus = ('Torus')
        localization_sphere = ('球體')
        localization_icosphere = ('Ico 球體')
