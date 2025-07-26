import re
import yaml
from pathlib import Path

re_guid = re.compile('guid: ([a-fA-F0-9]+)')
re_unity_tag = re.compile(r"(%YAML|%TAG|---).+")

class UnityAssetParser:
    @staticmethod
    def extract_guid(filepath: Path):
        if filepath.exists():
            meta_filepath = filepath.with_suffix(f'{filepath.suffix}.meta')
            if meta_filepath.exists():
                return re_guid.findall(meta_filepath.read_text())[0]
        return ''

    @staticmethod
    def load_yaml(filepath: Path):
        if filepath.exists():
            contents = filepath.read_text()
            contents = '\n'.join([line for line in contents.split('\n') if not re_unity_tag.match(line)])
            return yaml.safe_load(contents)
        return {}

    @staticmethod
    def get_mesh_guid(filepath: Path):
        prefab_data = UnityAssetParser.load_yaml(filepath)
        if 'MeshFilter' in prefab_data:
            return prefab_data['MeshFilter']['m_Mesh']['guid']
        elif 'PrefabInstance' in prefab_data:
            return prefab_data['PrefabInstance']['m_SourcePrefab']['guid']
        raise ValueError(f'Unknown prefab data: {filepath}')