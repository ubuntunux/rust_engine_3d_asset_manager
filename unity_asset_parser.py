import re
from .yaml_parser import YAML
from pathlib import Path

re_guid = re.compile('guid: ([a-fA-F0-9]+)')

class UnityAssetParser:
    logger = None

    @classmethod
    def extract_guid(cls, filepath: Path):
        if filepath.exists():
            meta_filepath = filepath.with_suffix(f'{filepath.suffix}.meta')
            if meta_filepath.exists():
                metadata = YAML(name='meta', contents=meta_filepath.read_text()).to_dict()
                return metadata['guid']
        return ''

    @classmethod
    def load_yaml(cls, filepath: Path):
        if filepath.exists():
            return YAML(name='YAML', contents=filepath.read_text()).to_dict()
        return {}

    @classmethod
    def get_mesh_guid(cls, filepath: Path):
        prefab_data = UnityAssetParser.load_yaml(filepath)
        cls.logger.info(prefab_data)
        if 'MeshFilter' in prefab_data:
            return prefab_data['MeshFilter']['m_Mesh']['guid']
        elif 'PrefabInstance' in prefab_data:
            return prefab_data['PrefabInstance']['m_SourcePrefab']['guid']
        raise ValueError(f'Unknown prefab data: {filepath}')