import json
from pathlib import Path

from . import utilities

global __logger__
global __asset_descriptor_manager__
global __asset_parser__

ASSET_DESCRIPTOR_TEMPLATE = '''
    "MATERIAL_INSTANCE": {
        "asset_path_infos": [
            {"asset_path_name": "Materials", "asset_catalog_name": "ProjectName"}
        ],
        "suffixes": [".mat"]
    },
    "MESH": {
        "asset_path_infos": [
            {"asset_path_name": "Models", "asset_catalog_name": "ProjectName"}
        ],
        "suffixes": [".fbx"]
    },
    "MODEL": {
        "asset_path_infos": [
            {"asset_path_name": "Prefabs", "asset_catalog_name": "ProjectName"}
        ],
        "suffixes": [".prefab"]
    },
    "SCENE": {
        "asset_path_infos": [
            {"asset_path_name": "Scenes", "asset_catalog_name": "ProjectName"}
        ],
        "suffixes": [".unity"]
    },
    "TEXTURE": {
        "asset_path_infos": [
            {"asset_path_name": "Textures", "asset_catalog_name": "ProjectName"}
        ],
        "suffixes": [".png", ".tga", ".jpeg", ".jpg"]
    }
}'''


class AssetTypeCatalogNames:
    asset_type_catalog_names = {
        'ANIMATION_LAYER': 'animation_layers',
        'GAME_CHARACTER': 'game_data/characters',
        'GAME_DATA': 'game_data/data',
        'GAME_SCENE': 'game_data/game_scenes',
        'GAME_ITEM': 'game_data/items',
        'GAME_PROP': 'game_data/props',
        'GAME_WEAPON': 'game_data/weapons',
        'MATERIAL_INSTANCE': 'material_instances',
        'MATERIAL': 'materials',
        'MESH': 'meshes',
        'MODEL': 'models',
        'SCENE': 'scenes',
        'TEXTURE': 'textures'
    }

    @classmethod
    def get_asset_type_names(cls):
        return list(cls.asset_type_catalog_names.keys())

    @classmethod
    def get_asset_type_catalog_name(cls, asset_type):
        return cls.asset_type_catalog_names.get(asset_type)


class AssetMetadata:
    def __init__(self, asset_type, asset_path, filepath, guid='', mtime=None):
        self._asset_type = asset_type
        self._asset_path = Path(asset_path)
        self._filepath = Path(filepath)
        self._guid = guid
        self._mtime = mtime or utilities.get_mtime(self._filepath)

    def dump(self):
        return {
            'asset_type': self.get_asset_type(),
            'asset_path': self.get_asset_path(),
            'filepath': self._filepath.as_posix(),
            'guid': self.get_guid(),
            'mtime': self.get_mtime()
        }

    def get_guid(self):
        return self._guid

    def get_asset_name(self):
        return self._asset_path.name

    def get_asset_path(self):
        return self._asset_path.as_posix()

    def get_asset_type(self):
        return self._asset_type

    def get_filepath(self):
        return self._filepath

    def exists(self):
        return self._filepath.exists()

    def get_mtime(self):
        return self._mtime

    def update_mtime(self):
        self._mtime = utilities.get_mtime(self._filepath)
        return self._mtime

    def get_mesh(self):
        return None



class AssetDescriptor:
    def __init__(self, asset_descriptor, asset_type):
        self._asset_descriptor = asset_descriptor
        self._asset_type = asset_type
        self._assets = {}
        self._assets_by_guid = {}

    def register_asset_metadata(self, asset):
        self._assets[asset.get_asset_path()] = asset
        self._assets_by_guid[asset.get_guid()] = asset

    def get_assets(self):
        return self._assets

    def get_asset(self, asset_name='', guid=''):
        if asset_name:
            return self._assets.get(asset_name)
        elif guid:
            return self._assets_by_guid.get(guid)
        return None

    def process(self, asset_descriptor_data):
        __logger__.info(f'AssetDescriptor::process::{self._asset_type}')
        root_path = self._asset_descriptor.get_root_path()
        my_asset_descriptor_data = asset_descriptor_data.get(self._asset_type, {})
        self._assets = {}
        for asset_path_info in my_asset_descriptor_data.get('asset_path_infos', []):
            asset_directory_path = root_path / asset_path_info.get('asset_path_name', '')
            asset_catalog_name = asset_path_info.get('asset_catalog_name', '')
            for ext in my_asset_descriptor_data.get('suffixes', []):
                for filepath in asset_directory_path.rglob(f'*{ext}'):
                    relative_filepath = filepath.relative_to(asset_directory_path)
                    asset_path = asset_catalog_name / relative_filepath.with_suffix('')
                    asset_metadata =  __asset_parser__.create_asset_metadata(self._asset_type, asset_path.as_posix(), filepath)
                    self.register_asset_metadata(asset_metadata)
                    __logger__.debug(asset_metadata)


class AssetDescriptorManager:
    def __init__(self, logger, root_path):
        global __logger__
        __logger__ = logger

        from .unity_asset_parser import UnityAssetParser
        global __asset_parser__
        __asset_parser__ = UnityAssetParser(asset_descriptor_manager=self, logger=logger)

        global __asset_descriptor_manager__
        __asset_descriptor_manager__ = self

        self._root_path = Path(root_path)
        self._descriptor_name = self._root_path.stem
        self._asset_descriptor_filepath = Path(self._root_path, 'asset_descriptor.json')
        self._material_instance_descriptor = AssetDescriptor(self, asset_type='MATERIAL_INSTANCE')
        self._mesh_descriptor = AssetDescriptor(self, asset_type='MESH')
        self._model_descriptor = AssetDescriptor(self, asset_type='MODEL')
        self._scene_descriptor = AssetDescriptor(self, asset_type='SCENE')
        self._texture_descriptor = AssetDescriptor(self, asset_type='TEXTURE')

    def get_asset_descriptor_filepath(self):
        return self._asset_descriptor_filepath.as_posix()

    def is_valid_asset_descriptor(self):
        return self._asset_descriptor_filepath.exists()

    def create_default_asset_descriptor_file(self):
        self._asset_descriptor_filepath.write_text(ASSET_DESCRIPTOR_TEMPLATE)
        return self.get_asset_descriptor_filepath()

    def process(self):
        asset_descriptor_data = json.loads(self._asset_descriptor_filepath.read_text())

        # Process each asset type
        self._texture_descriptor.process(asset_descriptor_data)
        self._material_instance_descriptor.process(asset_descriptor_data)
        self._mesh_descriptor.process(asset_descriptor_data)
        self._model_descriptor.process(asset_descriptor_data)
        self._scene_descriptor.process(asset_descriptor_data)

    def get_descriptor_name(self):
        return self._descriptor_name

    def get_root_path(self):
        return self._root_path

    def get_material_instances(self):
        return self._material_instance_descriptor.get_assets()

    def get_material_instance(self, asset_name='', guid=''):
        return self._material_instance_descriptor.get_asset(asset_name=asset_name, guid=guid)

    def get_meshes(self):
        return self._mesh_descriptor.get_assets()

    def get_mesh(self, asset_name='', guid=''):
        return self._mesh_descriptor.get_asset(asset_name=asset_name, guid=guid)

    def get_models(self):
        return self._model_descriptor.get_assets()

    def get_model(self, asset_name='', guid=''):
        return self._model_descriptor.get_asset(asset_name=asset_name, guid=guid)

    def get_scenes(self):
        return self._scene_descriptor.get_assets()

    def get_scene(self, asset_name='', guid=''):
        return self._scene_descriptor.get_asset(asset_name=asset_name, guid=guid)

    def get_textures(self):
        return self._texture_descriptor.get_assets()

    def get_texture(self, asset_name='', guid=''):
        return self._texture_descriptor.get_asset(asset_name=asset_name, guid=guid)