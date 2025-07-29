import os
from pathlib import Path
import uuid
import json

import bpy

from . import utilities
from .asset_descriptor import AssetMetadata, AssetTypeCatalogNames, AssetTypes

global __logger__
    
class AssetImportManager:
    def __init__(self, logger, asset_library_name, asset_descriptor_manager):
        global __logger__
        __logger__ = logger

        asset_library = bpy.context.preferences.filepaths.asset_libraries[asset_library_name]
        self._asset_library = asset_library
        self._asset_catalogs_filepath = Path(asset_library.path, 'blender_assets.cats.txt')
        self._asset_catalog_name_id_map = {}
        self._asset_catalog_name_type_map = {}
        self._asset_catalog_ids = {}
        self._asset_metadata = {}
        self._asset_descriptor_manager = asset_descriptor_manager
        self._asset_metadata_filepath = Path(asset_library.path, 'asset_metadata.json')

    def initialize(self):
        self.load_asset_catalogs()
        self.load_asset_metadata()

    def get_asset_type_and_name_from_asset_path(self, target_asset_path):
        for asset_type_name, asset_catalog_name in self._asset_catalog_name_type_map.items():
            if target_asset_path.is_relative_to(asset_catalog_name):
                return asset_type_name, target_asset_path.relative_to(asset_catalog_name).as_posix()
        raise ValueError(f'Unknown asset type: {target_asset_path}')

    def load_asset_catalogs(self):  
        __logger__.info('>>> load_asset_catalogs')
        # asset_catalog_name_id_map
        contents = self._asset_catalogs_filepath.read_text().split('\n')
        for content in contents:
            if content.startswith('#') or ':' not in content:
                continue
            uuid, catalog_name, catalog_simple_name = content.strip().split(':')
            self._asset_catalog_ids[catalog_name] = uuid
            self._asset_catalog_name_id_map[uuid] = catalog_name
            __logger__.debug(f'{uuid}: {catalog_name}')

        # asset_catalog_name_type_map
        for asset_type_name in AssetTypeCatalogNames.get_asset_type_names():
            self._asset_catalog_name_type_map[asset_type_name] = Path(self._asset_library.name, AssetTypeCatalogNames.get_asset_type_catalog_name(asset_type_name))

    def get_asset_catalog_id(self, catalog_simple_name):
        catalog_id = self._asset_catalog_ids.get(catalog_simple_name, '')
        if not catalog_id:
            catalog_id = self.register_asset_catalog_name(catalog_simple_name)
        return catalog_id

    def get_asset_catalog_name_by_id(self, catalog_id):
        return self._asset_catalog_name_id_map.get(catalog_id)

    def get_asset_catalog_name_by_type(self, asset_type_name):
        return self._asset_catalog_name_type_map.get(asset_type_name)

    def register_asset_catalog_name(self, catalog_name):
        if catalog_name not in self._asset_catalog_name_id_map:
            catalog_id = str(uuid.uuid4())
            catalog_simple_name = catalog_name.replace('/', '-')
            self._asset_catalog_name_id_map[catalog_id] = catalog_name
            self._asset_catalog_ids[catalog_name] = catalog_id

            contents = self._asset_catalogs_filepath.read_text().strip()
            contents += f'\n{catalog_id}:{catalog_name}:{catalog_simple_name}'
            self._asset_catalogs_filepath.write_text(contents)
            return catalog_id
        return ''

    def make_asset_library(self, asset, asset_type, asset_path, filepath):
        asset.asset_mark()
        catalog_name = Path(self.get_asset_catalog_name_by_type(asset_type), asset_path).parent.as_posix()
        asset.asset_data.catalog_id = self.get_asset_catalog_id(catalog_name)
        return self.register_asset_metadata(asset_type, asset_path, filepath)

    def register_asset_metadata(self, asset_type, asset_path, filepath):
        if asset_type not in self._asset_metadata:
            self._asset_metadata[asset_type] = {}
        asset_metadata = AssetMetadata(asset_type=asset_type, asset_path=asset_path, filepath=filepath)
        self._asset_metadata[asset_type][asset_path] = asset_metadata
        return asset_metadata

    def load_asset_metadata(self):
        __logger__.info(f'>>> load_asset_metadata: {self._asset_metadata_filepath}')
        asset_metadata_in_files = {}
        if self._asset_metadata_filepath.exists():
            with open(self._asset_metadata_filepath, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                for (filepath, asset_metadata_list) in loaded_data.items():
                    for asset_path, asset_metadata_dict in asset_metadata_list.items():
                        asset_metadata = AssetMetadata(**asset_metadata_dict)
                        filepath = asset_metadata.get_filepath()
                        if filepath.exists() and filepath.stat().st_mtime <= asset_metadata.get_mtime():
                            if filepath not in asset_metadata_in_files:
                                asset_metadata_in_files[filepath] = {}
                            asset_metadata_in_files[filepath][asset_metadata.get_asset_path()] = asset_metadata

        # update asset metadata
        for filepath in self._asset_metadata_filepath.parent.glob('**/*.blend'):
            if filepath in asset_metadata_in_files:
                continue

            utilities.clear_scene()
            with bpy.data.libraries.load(filepath.as_posix(), link=True, assets_only=True) as (data_from, data_to):
                data_to.actions = data_from.actions
                data_to.armatures = data_from.armatures
                data_to.collections = data_from.collections
                data_to.materials = data_from.materials
                data_to.meshes = data_from.meshes
                data_to.objects = data_from.objects
            data_blocks = [bpy.data.actions, bpy.data.armatures, bpy.data.collections, bpy.data.materials, bpy.data.meshes, bpy.data.objects]
            for data_block in data_blocks:
                for asset in data_block:
                    if asset.asset_data:
                        library_path = os.path.abspath(bpy.path.abspath(asset.library.filepath))                        
                        if library_path == filepath.as_posix():
                            abs_asset_path = Path(self.get_asset_catalog_name_by_id(asset.asset_data.catalog_id), asset.name)
                            asset_type, asset_path = self.get_asset_type_and_name_from_asset_path(abs_asset_path)
                            asset_metadata = AssetMetadata(
                                asset_type=asset_type,
                                asset_path=asset_path,
                                filepath=filepath,
                                mtime=utilities.get_mtime(filepath)
                            )
                            if filepath not in asset_metadata_in_files:
                                asset_metadata_in_files[filepath] = {}
                            asset_metadata_in_files[filepath][asset_metadata.get_asset_path()] = asset_metadata

        # convert asset metadata
        self._asset_metadata.clear()
        for (filepath, asset_metadata_list) in asset_metadata_in_files.items():
            for asset_path, asset_metadata in asset_metadata_list.items():
                self.register_asset_metadata(asset_metadata.get_asset_type(), asset_metadata.get_asset_path(), filepath)

        # save to file
        self.save_asset_metadata()

    def save_asset_metadata(self):
        __logger__.info(f'>>> save_asset_metadata: {self._asset_metadata_filepath}')
        with open(self._asset_metadata_filepath, 'w', encoding='utf-8') as f:
            save_data = {}
            for (asset_type, asset_metadata_list) in self._asset_metadata.items():
                for asset_path, asset_metadata in asset_metadata_list.items():
                    filepath = asset_metadata.get_filepath().as_posix()
                    if filepath not in save_data:
                        save_data[filepath] = {}
                    save_data[filepath][asset_path] = asset_metadata.dump()
            json.dump(save_data, f, indent=4)

    def get_asset_metadata(self, asset_type, asset_path):
        type_asset_metadata = self._asset_metadata.get(asset_type)
        return type_asset_metadata.get(asset_path) if type_asset_metadata else None

    def load_asset(self, asset_type, asset_path):
        asset_metadata = self.get_asset_metadata(asset_type, asset_path)
        if asset_metadata:
            asset_name = asset_metadata.get_asset_name()
            asset_filepath = asset_metadata.get_filepath().as_posix()
            # link asset
            with bpy.data.libraries.load(asset_filepath, link=True, assets_only=True) as (data_from, data_to):
                data_to.actions = data_from.actions
                data_to.armatures = data_from.armatures
                data_to.collections = data_from.collections
                data_to.materials = data_from.materials
                data_to.meshes = data_from.meshes
                data_to.objects = data_from.objects

            match asset_metadata.get_asset_type():
                case AssetTypes.MATERIAL | AssetTypes.MATERIAL_INSTANCE:
                    return bpy.data.materials[asset_name]
                case _:
                    for collection in data_to.collections:
                        if collection.name == asset_name:
                            return collection
            return None

        type_asset_metadata = self._asset_metadata.get(asset_type)
        __logger__.info(f'{list(type_asset_metadata.keys()), asset_path in type_asset_metadata}')

        raise ValueError(f'Unknown asset: {asset_path}')

    def load_default_material(self):
        return self.load_asset('MATERIAL', 'common/render_static_object')

    def override_material(self, material, material_name, blend_filepath):
        descriptor_name = self._asset_descriptor_manager.get_descriptor_name()
        material.name = material_name

        asset_path = Path(descriptor_name, material.name).as_posix()
        self.make_asset_library(asset=material, asset_type='MATERIAL_INSTANCE', asset_path=asset_path, filepath=blend_filepath)
        
        for node in material.node_tree.nodes:
            if node.label == 'textureBase':
                texture_filepath = Path(self._asset_library.path, 'textures/PolygonNatureBiomes/Terrain/Rock_Texture_01.png').as_posix()
                image_data = bpy.data.images.load(filepath=texture_filepath, check_existing=True)
                image_data.filepath = bpy.path.relpath(texture_filepath)
                node.image = image_data
                __logger__.debug(node.image.filepath)
            elif node.label == 'textureMaterial':
                pass
            elif node.label == 'textureNormal':
                pass
    
    # process import
    def import_textures(self):
        textures_path = Path(self._asset_library.path, 'textures')
        textures = self._asset_descriptor_manager.get_asset_metadata_list(AssetTypes.TEXTURE).values()
        __logger__.info(f'>>> import_textures: {len(textures)}')
        for texture in textures:
            ext = texture.get_filepath().suffix
            dst_texture_filepath = Path(textures_path, texture.get_asset_path()).with_suffix(ext)
            if utilities.get_mtime(dst_texture_filepath) < texture.get_mtime():
                __logger__.info(f'copy {dst_texture_filepath} -> {texture.get_filepath()}')
                utilities.copy(texture.get_filepath(), dst_texture_filepath)

    def import_meshes(self):
        mesh_path = Path(self._asset_library.path, 'meshes')
        meshes = self._asset_descriptor_manager.get_asset_metadata_list(AssetTypes.MESH).values()

        __logger__.info(f'>>> import_meshes: {len(meshes)}')
        for mesh in meshes:
            utilities.clear_scene()

            asset_path = mesh.get_asset_path()
            blend_filepath = Path(mesh_path, asset_path).with_suffix('.blend')
            if mesh.get_mtime() <= utilities.get_mtime(blend_filepath):
                continue
            
            # save
            __logger__.info(f'save mesh: {blend_filepath}')
            utilities.save_as(blend_filepath)
            
            # import fbx
            bpy.ops.import_scene.fbx(filepath=mesh.get_filepath().as_posix())
            
            # create a collection
            asset_name = Path(asset_path).name
            collection = utilities.create_collection(asset_name)
            msh_asset_metadata = self.make_asset_library(asset=collection, asset_type=AssetTypes.MESH, asset_path=asset_path, filepath=blend_filepath)
            
            # default material
            default_material = self.load_default_material()
            
            # make mesh
            for obj in bpy.context.scene.objects:
                # select object
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                
                # move to a collection
                utilities.move_to_collection(collection, obj)
                
                # set material
                for material_slot in obj.material_slots:
                    material_slot.link = 'DATA'
                    material_slot.material = default_material
                    material_slot.link = 'OBJECT'
                    material_slot.material = default_material
            
            # save final
            collection.asset_generate_preview()
            utilities.save_as(blend_filepath)
    
    def import_models(self):
        model_path = Path(self._asset_library.path, 'models')
        models = self._asset_descriptor_manager.get_asset_metadata_list(AssetTypes.MODEL).values()
        __logger__.info(f'>>> import_models: {len(models)}')

        shader_guid_list = set()
        
        for model in models:
            utilities.clear_scene()

            asset_path = model.get_asset_path()
            blend_filepath = Path(model_path, asset_path).with_suffix('.blend')
            if model.get_mtime() <= utilities.get_mtime(blend_filepath):
                continue
            
            # save
            __logger__.info(f'save model: {blend_filepath}')
            utilities.save_as(blend_filepath)
            
            # create a collection
            asset_name = Path(asset_path).name
            collection = utilities.create_collection(asset_name)
            self.make_asset_library(asset=collection, asset_type=AssetTypes.MODEL, asset_path=asset_path, filepath=blend_filepath)

            # link mesh and override
            mesh_asset_path = model.get_data(AssetTypes.MESH)
            mesh_asset_collection = self.load_asset(asset_type=AssetTypes.MESH, asset_path=mesh_asset_path)
            override_collection = mesh_asset_collection.override_hierarchy_create(
                bpy.context.scene,
                bpy.context.view_layer,
                do_fully_editable=True
            )
            bpy.context.scene.collection.children.unlink(override_collection)
            collection.children.link(override_collection)

            materials = model.get_data(AssetTypes.MATERIAL)
            material_instances = model.get_data(AssetTypes.MATERIAL_INSTANCE)
            for (i, material_instance_asset_path) in enumerate(material_instances):
                shader_guid = materials[i]
                shader_guid_list.add(shader_guid)

            # set material
            # for material_slot in obj.material_slots:
            #     material_slot.link = 'OBJECT'
            #     material_slot.material = default_material.copy()
            #     self.override_material(material_slot.material, obj.name, blend_filepath)
            
            # save final
            collection.asset_generate_preview()
            utilities.save_as(blend_filepath)

        __logger__.info(f'>>> shader_guid_list: {shader_guid_list}')
        
    def import_assets(self):
        __logger__.info(f'>>> Begin: import_assets')

        # initialize
        self.initialize()

        # load asset descriptor
        self._asset_descriptor_manager.process()
        
        # process import        
        self.import_textures()
        self.import_meshes()
        self.import_models()

        # close
        utilities.clear_scene()
        self._asset_descriptor_manager.close()
        self.save_asset_metadata()
        __logger__.info(f'>>> End: import_assets')