#
#   BlendexDMX > GDTF
#   Handles GDTF profiles
#
#   http://www.github.com/hugoaboud/BlenderDMX
#

import os
import bpy
import copy

from mathutils import Euler

from dmx import pygdtf

from dmx.io_scene_3ds.import_3ds import load_3ds

class DMX_GDTF():

    @staticmethod
    def getProfilesPath():
        ADDON_PATH = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(ADDON_PATH,'assets','profiles')

    @staticmethod
    def getPrimitivesPath():
        ADDON_PATH = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(ADDON_PATH,'assets','primitives')

    @staticmethod
    def getManufacturerList():
        # List profiles in folder
        manufacturers = set([])
        for file in os.listdir(DMX_GDTF.getProfilesPath()):
            # Parse info from file name: Company@Model.gdtf
            info = file.split('@')
            # Remove ".gdtf" from the end of the string
            info[-1] = info[-1][:-5]
            # Add to list (identifier, short name, full name)
            manufacturers.add((info[0], info[0], ''))

        return tuple(sorted(manufacturers))

    @staticmethod
    def getProfileList(manufacturer):
        # List profiles in folder
        profiles = []
        for file in os.listdir(DMX_GDTF.getProfilesPath()):
            # Parse info from file name: Company@Model.gdtf
            info = file.split('@')
            if (info[0] == manufacturer):
                # Remove ".gdtf" from the end of the string
                info[-1] = info[-1][:-5]
                # Add to list (identifier, short name, full name)
                profiles.append((file, info[1], (info[2] if len(info) > 2 else '')))

        return tuple(profiles)

    @staticmethod
    def getModes(profile):
        gdtf_profile = DMX_GDTF.loadProfile(profile)
        return tuple([mode.name for mode in gdtf_profile.dmx_modes])

    @staticmethod
    def getValue(dmx_value, fine=False):
        if (dmx_value.byte_count == 1): return dmx_value.value
        f = dmx_value.value/255.0
        msb = int(f)
        if (not fine): return msb
        lsb = int((f-msb)*255)
        return lsb

    @staticmethod
    def getFootprint(channels):
        #FIXME: for devices with GeometryReferences and DMX Brakes
        dmx_offsets = []
        for ch in channels:
            if ch.offset is None:
                continue
            dmx_offsets.append(max(o for o in ch.offset))
        return max(dmx_offsets)

    @staticmethod
    def getChannels(gdtf_profile, mode):
        dmx_mode = None
        for m in gdtf_profile.dmx_modes:
            if (m.name == mode):
                dmx_mode = m
                break
        if (not dmx_mode): return []
        
        channels = dmx_mode.dmx_channels
        footprint = DMX_GDTF.getFootprint(channels)

        dmx_channels = [{'id':'', 'default':0}]*footprint
        for ch in channels:
            if ch.offset is None:
                continue
            dmx_channels[ch.offset[0]-1] = {
                'id':str(ch.logical_channels[0].channel_functions[0].attribute),
                'default':DMX_GDTF.getValue(ch.logical_channels[0].channel_functions[0].default)
            }
            if (len(ch.offset) > 1):
                dmx_channels[ch.offset[1]-1] = {
                    'id':'+'+str(ch.logical_channels[0].channel_functions[0].attribute),
                    'default':DMX_GDTF.getValue(ch.logical_channels[0].channel_functions[0].default, True)
                }

        return dmx_channels
        
    @staticmethod
    def loadProfile(filename):
        path = os.path.join(DMX_GDTF.getProfilesPath(), filename)
        profile = pygdtf.FixtureType(path)
        return profile

    @staticmethod
    def loadBlenderPrimitive(model):
        primitive = str(model.primitive_type)

        if (primitive == 'Cube'):
            bpy.ops.mesh.primitive_cube_add(size=1.0)
        elif (primitive == 'Pigtail'):
            bpy.ops.mesh.primitive_cube_add(size=1.0)
        elif (primitive == 'Cylinder'):
            bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.5, depth=1.0)
        elif (primitive == 'Sphere'):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=16, radius=0.5)

        obj = bpy.context.view_layer.objects.selected[0]
        obj.users_collection[0].objects.unlink(obj)
        obj.scale = (model.length, model.width, model.height)
        return obj

    @staticmethod
    def loadPrimitive(model):
        primitive = str(model.primitive_type)
        path = os.path.join(DMX_GDTF.getPrimitivesPath(), primitive+'.obj')
        bpy.ops.import_scene.obj(filepath=path)
        obj = bpy.context.view_layer.objects.selected[0]
        obj.users_collection[0].objects.unlink(obj)
        obj.rotation_euler = Euler((0, 0, 0), 'XYZ')
        obj.scale = (model.length/obj.dimensions.x,model.width/obj.dimensions.y,model.height/obj.dimensions.z)
        return obj

    @staticmethod
    def loadModel(profile, model):
        current_path = os.path.dirname(os.path.realpath(__file__))
        extract_to_folder_path = os.path.join(current_path, 'assets', 'models', profile.fixture_type_id)
        
        if model.file.extension.lower() == "3ds":
            inside_zip_path = os.path.join("models/3ds",f"{model.file.name}.{model.file.extension}")
            file_name = profile._package.open(inside_zip_path)
            load_3ds(file_name, bpy.context)
        else:
            inside_zip_path = os.path.join("models/gltf",f"{model.file.name}.{model.file.extension}")
            profile._package.extract(inside_zip_path, extract_to_folder_path)
            file_name=os.path.join(extract_to_folder_path, inside_zip_path)
            bpy.ops.import_scene.gltf(filepath=file_name)

        obj = bpy.context.view_layer.objects.selected[0]
        obj.users_collection[0].objects.unlink(obj)
        obj.rotation_euler = Euler((0, 0, 0), 'XYZ')
        z=obj.dimensions.z or 1
        obj.scale = (
            obj.scale.x*model.length/obj.dimensions.x,
            obj.scale.y*model.width/obj.dimensions.y,
            obj.scale.z*model.height/z)
        return obj

    @staticmethod
    def buildCollection(profile, mode, mvr_position = None):
        print("build coolection", mvr_position)


        # Create model collection
        collection = bpy.data.collections.new(DMX_GDTF.getName(profile, mode))
        objs = {}
        # Get root geometry reference from the selected DMX Mode
        dmx_mode = profile.get_dmx_mode_by_name(mode)
        root_geometry = profile.get_geometry_by_name(dmx_mode.geometry)

        def load_geometries(geometry):
            """Load 3d models, primitives and shapes"""
            
            if isinstance(geometry, pygdtf.GeometryReference):
                reference = profile.get_geometry_by_name(geometry.geometry)
                geometry.model = reference.model

            if geometry.model is None:
                # Empty geometries are allowed as of GDTF 1.2
                # If the size is 0, Blender will discard it, set it to something tiny
                model=pygdtf.Model(name=geometry.name,
                                   length=0.0001, width=0.0001, height=0.0001, primitive_type="Cube")
                geometry.model = ""
            else:
                # Deepcopy the model because GeometryReference will modify the name
                # Perhaps this could be done conditionally
                # Also, we could maybe make a copy of the beam instance, if Blender supports it...
                model = copy.deepcopy(profile.get_model_by_name(geometry.model))

            if isinstance(geometry, pygdtf.GeometryReference):
                model.name=geometry.name

            obj = None
            primitive = str(model.primitive_type)
            # Normalize 1.1 PrimitiveTypes
            # (From GDTF v1.1 on, the 1_1 was added to the end of primitive names, we just ignore them and use the same primitives)
            if (primitive[-3:] == '1_1'):
                primitive = primitive[:-3]
                model.primitive_type = pygdtf.PrimitiveType(primitive)
            # BlenderDMX primitives
            if (str(model.primitive_type) in ['Base','Conventional','Head','Yoke']):
                obj = DMX_GDTF.loadPrimitive(model)
            # 'Undefined': load from 3d
            elif (str(model.primitive_type) == 'Undefined'):
                try:
                    obj = DMX_GDTF.loadModel(profile, model)
                except Exception as e:
                    print("Error importing 3D model:", e)
            # Blender primitives
            else:
                obj = DMX_GDTF.loadBlenderPrimitive(model)
            # If object was created
            if (obj != None):
                obj.name = model.name
                objs[model.name] = obj
                obj.hide_select = True

            if hasattr(geometry, "geometries"):
                for sub_geometry in geometry.geometries:
                    load_geometries(sub_geometry)


        def add_child_position(geometry):
            """Add a child, create a light source and emitter material for beams"""
            obj_child = objs[geometry.name]
            position = [geometry.position.matrix[c][3] for c in range(3)]
            if (geometry.name == root_geometry.name) and (mvr_position is not None):
                #root_position = [mvr_position.matrix[3][c]*0.001 for c in range(3)]
                #obj_child.location[0] += root_position[0]
                #obj_child.location[1] += root_position[1]
                #obj_child.location[2] += root_position[2]
                obj_child.matrix_world=mvr_position.matrix

            obj_child.location[0] += position[0]
            obj_child.location[1] += position[1]
            obj_child.location[2] += position[2]
            scale = [geometry.position.matrix[c][c] for c in range(3)]
            obj_child.scale[0] *= scale[0]
            obj_child.scale[1] *= scale[1]
            obj_child.scale[2] *= scale[2]
            if 'Pigtail' in geometry.model:
                if not bpy.context.scene.dmx.display_pigtails:
                    obj_child.scale[0] *= 0
                    obj_child.scale[1] *= 0
                    obj_child.scale[2] *= 0

            if isinstance(geometry, pygdtf.GeometryBeam) or isinstance(geometry, pygdtf.GeometryReference):
                if isinstance(geometry, pygdtf.GeometryReference):
                    geometry = profile.get_geometry_by_name(geometry.geometry)

                obj_child.visible_shadow = False
                light_data = bpy.data.lights.new(name="Spot", type='SPOT')
                light_data['flux'] = geometry.luminous_flux
                light_data.energy = 0
                light_data.spot_size = geometry.beam_angle*3.1415/180.0
                light_data.shadow_soft_size = geometry.beam_radius
                light_object = bpy.data.objects.new(name="Spot", object_data=light_data)
                light_object.location = obj_child.location
                light_object.hide_select = True
                constraint = light_object.constraints.new('CHILD_OF')
                constraint.target = obj_child
                collection.objects.link(light_object)

        def constraint_child_to_parent(parent_geometry, child_geometry):
            obj_parent = objs[parent_geometry.name]
            if (not child_geometry.name in objs): return
            obj_child = objs[child_geometry.name]
            constraint = obj_child.constraints.new('CHILD_OF')
            constraint.target = obj_parent
            constraint.use_scale_x = False
            constraint.use_scale_y = False
            constraint.use_scale_z = False
            # Add parent position
            position = [parent_geometry.position.matrix[c][3] for c in range(3)]
            obj_child.location[0] += obj_parent.location[0]
            obj_child.location[1] += obj_parent.location[1]
            obj_child.location[2] += obj_parent.location[2]

        def update_geometry(geometry):
            """Recursively update objects position, rotation and scale
               and define parent/child constraints"""
            add_child_position(geometry)

            if hasattr(geometry, "geometries"):
                if len(geometry.geometries) > 0:
                    for child_geometry in geometry.geometries:
                        constraint_child_to_parent(geometry, child_geometry)
                        update_geometry(child_geometry)

        # Load 3d objects from the GDTF profile
        load_geometries(root_geometry)
        update_geometry(root_geometry)

        # Add target for manipulating fixture
        target = bpy.data.objects.new(name="Target", object_data=None)
        collection.objects.link(target)
        target.empty_display_size = 0.5
        target.empty_display_type = 'PLAIN_AXES'
        if mvr_position:
            #root_position = [mvr_position.matrix[3][c]*0.001 for c in range(3)]
            #target.location = (root_position[0],root_position[1],root_position[2]-2)
            mvr_position.matrix[3][2] += -2
            target.matrix_world=mvr_position.matrix

        else:
            target.location = (0, 0, -2)

        # If there's no Head, this is a static fixture
        if ('Head' not in objs):
            # If body has a Yoke child, set Z rotation constraint
            for name, obj in objs.items():
                if (name == 'Yoke' and len(obj.constraints)):
                    constraint = obj.constraints[0]
                    if (constraint.target == objs['Body']):
                        constraint.use_rotation_x = False
                        constraint.use_rotation_y = False
                    break

            # Track body to the target
            constraint = objs['Body'].constraints.new('TRACK_TO')
            constraint.target = target

            # Make body selectable
            objs['Body'].hide_select = False

        # There's a Head! This is a moving fixture
        else:
            # If base has a Yoke child, create Z rotation constraint
            for name, obj in objs.items():
                if (name == 'Yoke' and len(obj.constraints)):
                    constraint = obj.constraints[0]
                    if (constraint.target == objs['Base']):
                        constraint = obj.constraints.new('LOCKED_TRACK')
                        constraint.target = target
                        constraint.lock_axis = "LOCK_Z"
                    break

            # Track body to the target
            constraint = objs['Head'].constraints.new('TRACK_TO')
            constraint.target = target

            # Make body selectable
            objs['Base'].hide_select = False

        # Link objects to collection
        for name, obj in objs.items():
            collection.objects.link(obj)

        return collection

    @staticmethod
    def getName(profile, dmx_mode):
        revision = profile.revisions[-1].text if len(profile.revisions) else ''
        return f"{profile.manufacturer}, {profile.name}, {dmx_mode}, {revision}"
