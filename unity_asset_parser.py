import re
from pathlib import Path

from . import utilities
from .asset_descriptor import AssetMetadata, AssetTypes, AssetParser
from .yaml_parser import YAML

global __logger__
global __asset_descriptor_manager__
global __asset_parser__

re_color = re.compile(r'{(.+?)}')
re_guid = re.compile('guid: ([a-fA-F0-9]+)')

class UnityAssetParser(AssetParser):
    def __init__(self, asset_descriptor_manager, logger):
        global __logger__
        __logger__ = logger
        global __asset_parser__
        __asset_parser__ = self
        global __asset_descriptor_manager__
        __asset_descriptor_manager__ = asset_descriptor_manager
        self._asset_descriptor_data = {}

    @staticmethod
    def extract_guid(filepath: Path):
        if filepath.exists():
            meta_filepath = filepath.with_suffix(f'{filepath.suffix}.meta')
            metadata = YAML.load_yaml(meta_filepath)
            return metadata['guid']
        return ''

    @staticmethod
    def extract_color(value):
        return dict([(key, eval(value)) for key, value in value.items()])

    def process_asset_data(self, asset_descriptor_data, asset_metadata):
        yaml_data = YAML.load_yaml(asset_metadata.get_filepath())
        match(asset_metadata.get_asset_type()):
            case AssetTypes.MATERIAL:
                pass
            case AssetTypes.MATERIAL_INSTANCE:
                parameters = self.process_material_and_parameters(asset_descriptor_data, yaml_data)
                for parameter_type, parameter_value in parameters.items():
                    asset_metadata.set_data(parameter_type, parameter_value)
            case AssetTypes.MESH:
                pass
            case AssetTypes.MODEL:
                material_instance_asset_paths = self.process_material_instances(yaml_data)
                mesh_asset_path = self.process_mesh(yaml_data)
                asset_metadata.set_data(AssetTypes.MATERIAL_INSTANCE, material_instance_asset_paths)
                asset_metadata.set_data(AssetTypes.MESH, mesh_asset_path)
            case AssetTypes.SCENE:
                pass
            case AssetTypes.TEXTURE:
                pass
            case _:
                msg = f'Unknown asset type: {asset_metadata.get_asset_type()}'
                __logger__.error(msg)
                raise ValueError(msg)

    @staticmethod
    def process_material_and_parameters(asset_descriptor_data, yaml_data):
        parameters = {}
        material_guid = yaml_data['Material']['m_Shader']['guid']
        material_create_info = asset_descriptor_data[AssetTypes.MATERIAL]['material_create_infos'][material_guid]
        parameters[AssetTypes.MATERIAL] = material_create_info['asset_path']

        parameters[AssetTypes.TEXTURE] = {}
        m_TexEnvs = yaml_data['Material']['m_SavedProperties'].get('m_TexEnvs', [])
        __logger__.info(f'AssetTypes.TEXTURE: {m_TexEnvs}')
        for m_TexEnv in m_TexEnvs:
            for parameter_name, value in m_TexEnv.items():
                if parameter_name in material_create_info['m_TexEnvs']:
                    texture_guid = value['m_Texture'].get('guid', '0')
                    parameters[AssetTypes.TEXTURE][parameter_name] = __asset_descriptor_manager__.get_asset_metadata(AssetTypes.TEXTURE, guid=texture_guid).get_asset_path()

        parameters[AssetTypes.COLOR] = {}
        m_Colors = yaml_data['Material']['m_SavedProperties'].get('m_Colors', [])
        for m_Color in m_Colors:
            for parameter_name, value in m_Color.items():
                if parameter_name in material_create_info['m_Colors']:
                    color = UnityAssetParser.extract_color(value)
                    parameters[AssetTypes.COLOR][parameter_name] = color

        parameters[AssetTypes.FLOAT] = {}
        m_Floats = yaml_data['Material']['m_SavedProperties'].get('m_Floats', [])
        for m_Float in m_Floats:
            for parameter_name, value in m_Float.items():
                if parameter_name in material_create_info['m_Floats']:
                    parameters[AssetTypes.FLOAT][parameter_name] = float(value)

        return parameters

    @staticmethod
    def process_material_instances(yaml_data):
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

    @staticmethod
    def process_mesh(yaml_data):
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
        new_asset_metadata_list_by_types = {}
        for asset_type in AssetTypes.get_types():
            asset_metadata_list = []
            new_asset_metadata_list_by_types[asset_type] = asset_metadata_list

            descriptor_data = asset_descriptor_data.get(asset_type, {})
            # parsing: asset_path_infos
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
                                mtime=utilities.get_mtime(filepath)
                            )
                            asset_metadata_list.append(asset_metadata)
                            __asset_descriptor_manager__.register_asset_metadata(asset_metadata)
                            __logger__.info(f'register_asset_metadata: {asset_metadata.get_asset_type()}, {asset_metadata.get_asset_path()}')
            # MATERIAL: material_create_infos
            if AssetTypes.MATERIAL == asset_type:
                for (material_guid, material_create_info) in descriptor_data.get('material_create_infos', {}).items():
                    filepath = Path(__asset_descriptor_manager__.get_asset_descriptor_filepath())
                    asset_path = material_create_info['asset_path']
                    asset_metadata = __asset_descriptor_manager__.get_asset_metadata(asset_type=asset_type, asset_path=asset_path)
                    if asset_metadata is None:
                        asset_metadata = AssetMetadata(
                            asset_type=asset_type,
                            asset_path=asset_path,
                            filepath=filepath,
                            guid=material_guid,
                            mtime=utilities.get_mtime(filepath),
                        )
                        asset_metadata_list.append(asset_metadata)
                        __asset_descriptor_manager__.register_asset_metadata(asset_metadata)
                        __logger__.info(f'register_asset_metadata: {asset_metadata.get_asset_type()}, {asset_metadata.get_asset_path()}')

        # process_asset_data
        for (asset_type, asset_metadata_list) in new_asset_metadata_list_by_types.items():
            for asset_metadata in asset_metadata_list:
                self.process_asset_data(asset_descriptor_data, asset_metadata)

