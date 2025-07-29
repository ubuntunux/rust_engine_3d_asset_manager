import re
from pathlib import Path

from . import utilities
from .asset_descriptor import AssetMetadata, AssetTypes, AssetParser
from .yaml_parser import YAML


global __logger__
global __asset_descriptor_manager__
global __asset_parser__

re_guid = re.compile('guid: ([a-fA-F0-9]+)')

class UnityAssetParser(AssetParser):
    def __init__(self, asset_descriptor_manager, logger):
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
            metadata = YAML.load_yaml(meta_filepath)
            return metadata['guid']
        return ''

    @classmethod
    def process_asset_data(cls, asset_metadata):
        match(asset_metadata.get_asset_type()):
            case AssetTypes.MATERIAL_INSTANCE:
                pass
            case AssetTypes.MESH:
                pass
            case AssetTypes.MODEL:
                yaml_data = YAML.load_yaml(asset_metadata.get_filepath())
                material_instances = cls.process_material_instances(yaml_data)
                asset_metadata.set_data(AssetTypes.MATERIAL_INSTANCE, material_instances)
                asset_metadata.set_data(AssetTypes.MATERIAL, cls.process_material(material_instances))
                asset_metadata.set_data(AssetTypes.MESH, cls.process_mesh(yaml_data))
            case AssetTypes.SCENE:
                pass
            case AssetTypes.TEXTURE:
                pass
            case _:
                msg = f'Unknown asset type: {asset_metadata.get_asset_type()}'
                __logger__.error(msg)
                raise ValueError(msg)

    @classmethod
    def process_material(cls, material_instances):
        materials = []
        for (i, material_instance_asset_path) in enumerate(material_instances):
            materials.append('None')
            material_instance = __asset_descriptor_manager__.get_asset_metadata(AssetTypes.MATERIAL_INSTANCE, material_instance_asset_path)
            if material_instance:
                yaml_data = YAML.load_yaml(material_instance.get_filepath())
                if 'Material' in yaml_data:
                    materials[i] = yaml_data['Material']['m_Shader']['guid']
                else:
                    msg = f'Unknown yaml data: {yaml_data}'
                    __logger__.error(msg)
                    raise ValueError(msg)
        return materials

    @classmethod
    def process_material_instances(cls, yaml_data):
        material_guids = []
        if 'MeshRenderer' in yaml_data:
            for material in yaml_data['MeshRenderer']['m_Materials']:
                material_guids.append(material['guid'])
        elif 'PrefabInstance' in yaml_data:
            for modification in yaml_data['PrefabInstance']['m_Modification']['m_Modifications']:
                if modification['propertyPath'].startswith('m_Materials'):
                    material_guids.append(modification['objectReference']['guid'])
        else:
            msg = f'Unknown yaml data: {yaml_data}'
            __logger__.error(msg)
            raise ValueError(msg)
        return [__asset_descriptor_manager__.get_asset_metadata(AssetTypes.MATERIAL_INSTANCE, guid=guid).get_asset_path() for guid in material_guids]

    @classmethod
    def process_mesh(cls, yaml_data):
        if 'MeshFilter' in yaml_data:
            mesh_guid = yaml_data['MeshFilter']['m_Mesh']['guid']
        elif 'PrefabInstance' in yaml_data:
            mesh_guid = yaml_data['PrefabInstance']['m_SourcePrefab']['guid']
        else:
            msg = f'Unknown yaml data: {yaml_data}'
            __logger__.error(msg)
            raise ValueError(msg)
        return __asset_descriptor_manager__.get_asset_metadata(AssetTypes.MESH, guid=mesh_guid).get_asset_path()

    def process(self, asset_descriptor_data):
        __logger__.info(f'AssetDescriptor::process')
        root_path = __asset_descriptor_manager__.get_root_path()
        for asset_type in AssetTypes.get_types():
            descriptor_data = asset_descriptor_data.get(asset_type, {})
            for asset_path_info in descriptor_data.get('asset_path_infos', []):
                asset_directory_path = root_path / asset_path_info.get('import_path', '')
                asset_catalog_name = asset_path_info.get('asset_catalog_name', '')
                for ext in descriptor_data.get('suffixes', []):
                    for filepath in asset_directory_path.rglob(f'*{ext}'):
                        relative_filepath = filepath.relative_to(asset_directory_path)
                        asset_path = Path(asset_catalog_name, relative_filepath.with_suffix('')).as_posix()
                        asset_metadata = __asset_descriptor_manager__.get_asset_metadata(asset_type=asset_type, asset_path=asset_path)
                        if asset_metadata is None:
                            asset_metadata = AssetMetadata(
                                asset_type=asset_type,
                                asset_path=asset_path,
                                filepath=filepath,
                                guid=self.extract_guid(filepath),
                                mtime=utilities.get_mtime(filepath),
                                data=None
                            )
                            self.process_asset_data(asset_metadata)
                            __asset_descriptor_manager__.register_asset_metadata(asset_metadata)
                            __logger__.info(f'process get_asset_metadata: {asset_metadata.get_asset_type()}, {asset_metadata.get_asset_path()}')