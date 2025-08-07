import json
from pathlib import Path

from . import utilities

global __logger__
global __asset_descriptor_manager__
global __asset_parser__

class AssetTypes:
    ANIMATION_LAYER = 'ANIMATION_LAYER'
    COLOR = 'COLOR'
    VALUE = 'VALUE'
    GAME_CHARACTER = 'GAME_CHARACTER'
    GAME_DATA = 'GAME_DATA'
    GAME_SCENE = 'GAME_SCENE'
    GAME_ITEM = 'GAME_ITEM'
    GAME_PROP = 'GAME_PROP'
    GAME_WEAPON = 'GAME_WEAPON'
    MATERIAL = 'MATERIAL'
    MATERIAL_INSTANCE = 'MATERIAL_INSTANCE'
    MESH = 'MESH'
    MODEL = 'MODEL'
    SCENE = 'SCENE'
    TEXTURE = 'TEXTURE'

    @classmethod
    def get_types(cls):
        return [key for key in cls.__dict__.keys() if key.isupper()]


ASSET_DESCRIPTOR_TEMPLATE = '''
{
    "MATERIAL": {
        "material_create_infos": {
            "0000000000000000f000000000000000": {
                "asset_path": "PolygonNatureBiomes/Standard",
                "m_TexEnvs": ["_MainTex", "_BumpMap", "_EmissionMap"],
                "m_Colors": ["_Color"],
                "m_Floats": ["_Glossiness", "_Metallic"]
            },
            "276a39a5a210b124885f0eff3e80f1f3": {
                "asset_path": "PolygonNatureBiomes/WaterShader",
                "m_TexEnvs": ["_DistortionMap", "_FoamMask", "_Refraction", "_WaterNormal", "_WaveMask"],
                "m_Colors": ["_DeepColour", "_FoamColor"],
                "m_Floats": ["_Glossiness", "_Metallic", "_Tiling", "_Opacity", "_waveTime"]
            },
            "6697e1f185bc8b840a2f02567abf15b5": {
                "asset_path": "PolygonNatureBiomes/VegetationShader",
                "m_TexEnvs": ["_EmissiveMask", "_GustNoiseMap", "_LeafNormalMap", "_LeafTex", "_TrunkNormalMap", "_TunkTex"],
                "m_Colors": ["_BaseColour", "_EmissiveColour", "_TrunkBaseColour"],
                "m_Floats": ["_TrunkSmoothness", "_LeafSmoothness", "_GustFreq", "_GustLargeFreq", "_GustScale", "_GustSmallFreq"]
            },
            "66f8401a4c881134f8803eceae302347": {
                "asset_path": "PolygonNatureBiomes/TriplanarBasic",
                "m_TexEnvs": ["_Top", "_TopNormal", "_Sides", "_SidesNormal"],
                "m_Colors": ["_Color"],
                "m_Floats": ["_Glossiness", "_Metallic"]
            },
            "b79e425cce5c90642a8dd66b6852353e": {
                "asset_path": "PolygonNatureBiomes/SkyBoxUnlit",
                "m_TexEnvs": [],
                "m_Colors": ["_ColorBottom", "_ColorTop"],
                "m_Floats": []
            }
        },
        "suffixes": []
    },
    "MATERIAL_INSTANCE": {
        "asset_path_infos": [
            {"import_path": "Materials", "asset_catalog_name": "PolygonNatureBiomes"}
        ],
        "suffixes": [".mat"]
    },
    "MESH": {
        "asset_path_infos": [
            {"import_path": "Models", "asset_catalog_name": "PolygonNatureBiomes"}
        ],
        "suffixes": [".fbx"]
    },
    "MODEL": {
        "asset_path_infos": [
            {"import_path": "Prefabs", "asset_catalog_name": "PolygonNatureBiomes"}
        ],
        "suffixes": [".prefab"]
    },
    "SCENE": {
        "asset_path_infos": [
            {"import_path": "Scenes", "asset_catalog_name": "PolygonNatureBiomes"}
        ],
        "suffixes": [".unity"]
    },
    "TEXTURE": {
        "asset_path_infos": [
            {"import_path": "Terrain", "asset_catalog_name": "PolygonNatureBiomes/Terrain"},
            {"import_path": "Textures", "asset_catalog_name": "PolygonNatureBiomes"}
        ],
        "suffixes": [".png", ".tga", ".jpeg", ".jpg"]
    }
}
'''


class AssetTypeCatalogNames:
    asset_type_catalog_names = {
        AssetTypes.ANIMATION_LAYER: 'animation_layers',
        AssetTypes.GAME_CHARACTER: 'game_data/characters',
        AssetTypes.GAME_DATA: 'game_data/data',
        AssetTypes.GAME_SCENE: 'game_data/game_scenes',
        AssetTypes.GAME_ITEM: 'game_data/items',
        AssetTypes.GAME_PROP: 'game_data/props',
        AssetTypes.GAME_WEAPON: 'game_data/weapons',
        AssetTypes.MATERIAL_INSTANCE: 'material_instances',
        AssetTypes.MATERIAL: 'materials',
        AssetTypes.MESH: 'meshes',
        AssetTypes.MODEL: 'models',
        AssetTypes.SCENE: 'scenes',
        AssetTypes.TEXTURE: 'textures'
    }

    @classmethod
    def get_asset_type_names(cls):
        return list(cls.asset_type_catalog_names.keys())

    @classmethod
    def get_asset_type_catalog_name(cls, asset_type):
        return cls.asset_type_catalog_names.get(asset_type)


class AssetMetadata:
    def __init__(self, asset_type='', asset_path='', filepath='', guid='', mtime=None, data=None):
        self._asset_type = asset_type
        self._asset_path = Path(asset_path)
        self._filepath = Path(filepath)
        self._guid = guid
        self._mtime = mtime or utilities.get_mtime(self._filepath)
        self._data = data if data else {}

    def process(self):
        pass

    def dump(self):
        return {
            'asset_type': self.get_asset_type(),
            'asset_path': self.get_asset_path(),
            'filepath': self._filepath.as_posix(),
            'guid': self.get_guid(),
            'mtime': self.get_mtime(),
            'data': self._data,
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

    def get_data(self, key):
        return self._data.get(key)

    def set_data(self, key, value):
        self._data[key] = value


class AssetParser:
    pass


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
        self._asset_metadata_filepath = Path(self._root_path, 'asset_metadata.json')
        self._asset_descriptor_filepath = Path(self._root_path, 'asset_descriptor.json')
        self._asset_metadata_by_types = {}

    def close(self):
        self.save_asset_metadata()

    def get_root_path(self):
        return self._root_path

    def get_descriptor_name(self):
        return self._descriptor_name

    def get_asset_descriptor_filepath(self):
        return self._asset_descriptor_filepath.as_posix()

    def is_valid_asset_descriptor(self):
        return self._asset_descriptor_filepath.exists()

    def create_default_asset_descriptor_file(self):
        self._asset_descriptor_filepath.write_text(ASSET_DESCRIPTOR_TEMPLATE)
        return self.get_asset_descriptor_filepath()

    def get_asset_metadata_list(self, asset_type):
        return self._asset_metadata_by_types.get(asset_type, {})

    def get_asset_metadata(self, asset_type, asset_path=None, guid=None):
        if guid:
            for asset_metadata in self.get_asset_metadata_list(asset_type).values():
                if asset_metadata.get_guid() == guid:
                    return asset_metadata

        return self.get_asset_metadata_list(asset_type).get(asset_path)

    def register_asset_metadata(self, asset_metadata):
        asset_type = asset_metadata.get_asset_type()
        if asset_type not in self._asset_metadata_by_types:
            self._asset_metadata_by_types[asset_type] = {}
        self._asset_metadata_by_types[asset_type][asset_metadata.get_asset_path()] = asset_metadata

    def process(self):
        __logger__.info(f'AssetDescriptorManager::process: {self._asset_descriptor_filepath}')
        self.load_asset_metadata()
        asset_descriptor_data = json.loads(self._asset_descriptor_filepath.read_text())
        __asset_parser__.process(asset_descriptor_data)
        self.save_asset_metadata()

    def load_asset_metadata(self):
        __logger__.info(f'>>> load_asset_metadata: {self._asset_metadata_filepath}')
        self._asset_metadata_by_types.clear()
        if self._asset_metadata_filepath.exists():
            with open(self._asset_metadata_filepath, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                for (asset_type, asset_metadata_list) in loaded_data.items():
                    for asset_path, asset_metadata_dict in asset_metadata_list.items():
                        asset_metadata = AssetMetadata(**asset_metadata_dict)
                        filepath = asset_metadata.get_filepath()
                        if filepath.exists() and filepath.stat().st_mtime <= asset_metadata.get_mtime():
                            self.register_asset_metadata(asset_metadata)

    def save_asset_metadata(self):
        __logger__.info(f'>>> save_asset_metadata: {self._asset_metadata_filepath}')
        with open(self._asset_metadata_filepath, 'w', encoding='utf-8') as f:
            save_data = {}
            for (asset_type, asset_metadata_list) in self._asset_metadata_by_types.items():
                for asset_path, asset_metadata in asset_metadata_list.items():
                    if asset_type not in save_data:
                        save_data[asset_type] = {}
                    save_data[asset_type][asset_path] = asset_metadata.dump()
            json.dump(save_data, f, indent=4)