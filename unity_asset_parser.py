import re
from .yaml_parser import YAML
from pathlib import Path

global logger
re_guid = re.compile('guid: ([a-fA-F0-9]+)')

class UnityAssetParser:
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
            data = YAML(name='YAML', contents=filepath.read_text()).to_dict()
            return data
        return {}

    @staticmethod
    def get_mesh_guid(filepath: Path):
        prefab_data = UnityAssetParser.load_yaml(filepath)
        logger.info(prefab_data)
        if 'MeshFilter' in prefab_data:
            return prefab_data['MeshFilter']['m_Mesh']['guid']
        elif 'PrefabInstance' in prefab_data:
            return prefab_data['PrefabInstance']['m_SourcePrefab']['guid']
        raise ValueError(f'Unknown prefab data: {filepath}')