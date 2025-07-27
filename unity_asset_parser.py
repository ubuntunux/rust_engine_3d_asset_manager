import re

from .asset_descriptor import AssetMetadata
from .yaml_parser import YAML
from pathlib import Path

global __logger__
global __asset_descriptor_manager__
global __asset_parser__

re_guid = re.compile('guid: ([a-fA-F0-9]+)')

class UnityAssetMetadata(AssetMetadata):
    def __init__(self, asset_type, asset_path, filepath, guid='', mtime=0):
        AssetMetadata.__init__(self, asset_type, asset_path, filepath, guid=guid, mtime=mtime)
        self._data = {}

        # load data
        if asset_type in ['MATERIAL_INSTANCE', 'MODEL', 'SCENE']:
            self._data = UnityAssetParser.load_yaml(self._filepath)

    def get_material_instances(self):
        material_guids = []
        if 'MeshRenderer' in self._data:
            for material in self._data['MeshRenderer']['m_Materials']:
                material_guids.append(material.get('guid'))
        elif 'PrefabInstance' in self._data:
            for modification in self._data['PrefabInstance']['m_Modification']['m_Modifications']:
                if modification['propertyPath'].startswith('m_Materials'):
                    material_guids.append(modification['objectReference']['guid'])
        else:
            msg = f'Unknown prefab data: {self._filepath}'
            __logger__.error(msg)
            raise ValueError(msg)
        return [__asset_descriptor_manager__.get_material_instance(guid=guid) for guid in material_guids]

    def get_mesh(self):
        if 'MeshFilter' in self._data:
            mesh_guid = self._data['MeshFilter']['m_Mesh']['guid']
        elif 'PrefabInstance' in self._data:
            mesh_guid = self._data['PrefabInstance']['m_SourcePrefab']['guid']
        else:
            msg = f'Unknown prefab data: {self._filepath}'
            __logger__.error(msg)
            raise ValueError(msg)
        return __asset_descriptor_manager__.get_mesh(guid=mesh_guid)


class UnityAssetParser:
    def __init__(self, asset_descriptor_manager, logger):
        self._asset_descriptor_manager = asset_descriptor_manager
        global __logger__
        __logger__ = logger
        global __asset_parser__
        __asset_parser__ = self
        global __asset_descriptor_manager__
        __asset_descriptor_manager__ = asset_descriptor_manager

    @staticmethod
    def extract_guid(filepath: Path):
        if filepath.exists():
            meta_filepath = filepath.with_suffix(f'{filepath.suffix}.meta')
            metadata = UnityAssetParser.load_yaml(meta_filepath)
            return metadata['guid']
        return ''

    @staticmethod
    def load_yaml(filepath: Path):
        if filepath.exists():
            return YAML(name='YAML', contents=filepath.read_text()).to_dict()
        return {}

    def create_asset_metadata(self, asset_type, asset_path, filepath):
        return UnityAssetMetadata(
            asset_type=asset_type,
            asset_path=asset_path,
            filepath=filepath,
            guid=self.extract_guid(filepath)
        )

