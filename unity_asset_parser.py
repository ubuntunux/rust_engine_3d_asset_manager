import copy
import re
from pathlib import Path

from . import utilities
from . import yaml_parser
from .asset_descriptor import MODEL_INFO_TEMPLATE, AssetMetadata, AssetTypes, AssetParser
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
        yaml_parser.__logger__ = logger
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
            return metadata.get_child('guid').get_value()
        return ''

    @staticmethod
    def extract_color(value):
        return [eval(value) for key, value in value.items()]

    def process_asset_data(self, asset_descriptor_data, asset_metadata):
        __logger__.debug(f'>>> process_asset_data: {asset_metadata.get_asset_path()}')
        match(asset_metadata.get_asset_type()):
            case AssetTypes.MATERIAL:
                pass
            case AssetTypes.MATERIAL_INSTANCE:
                yaml_data = YAML.load_yaml(asset_metadata.get_filepath())
                parameters = self.process_material_and_parameters(asset_descriptor_data, yaml_data)
                for parameter_type, parameter_value in parameters.items():
                    asset_metadata.set_data(parameter_type, parameter_value)
            case AssetTypes.MESH:
                pass
            case AssetTypes.MODEL:
                yaml_data = YAML.load_yaml(asset_metadata.get_filepath())
                material_instance_asset_paths = self.process_material_instances(yaml_data)
                mesh_asset_path = self.process_mesh(yaml_data)
                asset_metadata.set_data(AssetTypes.MATERIAL_INSTANCE, material_instance_asset_paths)
                asset_metadata.set_data(AssetTypes.MESH, mesh_asset_path)
            case AssetTypes.SCENE:
                yaml_data = YAML.load_yaml(asset_metadata.get_filepath())
                model_infos = self.process_model_infos(yaml_data)
                asset_metadata.set_data(AssetTypes.MODEL, model_infos)
            case AssetTypes.TEXTURE:
                pass
            case _:
                msg = f'Unknown asset type: {asset_metadata.get_asset_type()}'
                __logger__.error(msg)
                raise ValueError(msg)

    @staticmethod
    def process_material_and_parameters(asset_descriptor_data, yaml_data):
        parameters = {}
        material_guid = yaml_data.get_child('Material').get_child('m_Shader').get('guid')
        material_create_info = asset_descriptor_data[AssetTypes.MATERIAL]['material_create_infos'][material_guid]
        parameters[AssetTypes.MATERIAL] = material_create_info['asset_path']

        parameters[AssetTypes.TEXTURE] = {}
        m_TexEnvs = yaml_data.get_child('Material').get_child('m_SavedProperties').get_child('m_TexEnvs').get_children()
        for m_TexEnvGroup in m_TexEnvs:
            m_TexEnv = m_TexEnvGroup.get_node(0)
            if m_TexEnv.get_name() in material_create_info['m_TexEnvs']:
                texture_guid = m_TexEnv.get_child('m_Texture').get('guid')
                texture = __asset_descriptor_manager__.get_asset_metadata(AssetTypes.TEXTURE, guid=texture_guid)
                parameters[AssetTypes.TEXTURE][m_TexEnv.get_name()] = texture.get_asset_path() if texture else ''

        parameters[AssetTypes.COLOR] = {}
        m_Colors = yaml_data.get_child('Material').get_child('m_SavedProperties').get_child('m_Colors').get_children()
        for m_ColorGroup in m_Colors:
            m_Color = m_ColorGroup.get_node(0)
            if m_Color.get_name() in material_create_info['m_Colors']:
                parameters[AssetTypes.COLOR][m_Color.get_name()] = UnityAssetParser.extract_color(m_Color.get_value())

        parameters[AssetTypes.VALUE] = {}
        m_Floats = yaml_data.get_child('Material').get_child('m_SavedProperties').get_child('m_Floats').get_children()
        for m_FloatGroup in m_Floats:
            m_Float = m_FloatGroup.get_node(0)
            if m_Float.get_name() in material_create_info['m_Floats']:
                parameters[AssetTypes.VALUE][m_Float.get_name()] = float(m_Float.get_value())

        return parameters

    @staticmethod
    def process_material_instances(yaml_data):
        material_guid_groups = []
        MeshRenderers = yaml_data.get_children('MeshRenderer')
        PrefabInstances = yaml_data.get_children('PrefabInstance')
        if MeshRenderers:
            for MeshRenderer in MeshRenderers:
                material_guid_groups.append([])
                material_guids = material_guid_groups[-1]
                for material_group in MeshRenderer.get_child('m_Materials').get_children():
                    material = material_group.get_node(0)
                    guid = material.get('guid')
                    if guid is None:
                        __logger__.error(f'process_material_instances - MeshRenderer.m_Materials.guid: {guid}, value: {material}')
                    material_guids.append(guid)
        elif PrefabInstances:
            for PrefabInstance in PrefabInstances:
                for modification_group in PrefabInstance.get_child('m_Modification').get_child('m_Modifications').get_children():
                    if modification_group.find_node('propertyPath').get_value().startswith('m_Materials'):
                        guid = modification_group.find_node('objectReference').get('guid')
                        if guid is None:
                            __logger__.error(f'process_material_instances - PrefabInstance.m_Modification.m_Modifications.objectReference.guid: {guid}, value: {modification.get_child("objectReference")}')
                        material_guid_groups.append([])
                        material_guids = material_guid_groups[-1]
                        material_guids.append(guid)
        else:
            msg = f'Unknown yaml data: {yaml_data}'
            __logger__.error(msg)
            raise ValueError(msg)

        material_path_groups = []
        for material_guids in material_guid_groups:
            material_path_groups.append([])
            material_paths = material_path_groups[-1]
            for guid in material_guids:
                asset_metadata = __asset_descriptor_manager__.get_asset_metadata(AssetTypes.MATERIAL_INSTANCE, guid=guid)
                if asset_metadata:
                    material_paths.append(asset_metadata.get_asset_path())
                else:
                    __logger__.error(f'process_material_instances - guid: {guid}')
        return material_path_groups

    @staticmethod
    def process_mesh(yaml_data):
        MeshFilter = yaml_data.get_child('MeshFilter')
        PrefabInstance = yaml_data.get_child('PrefabInstance')
        if MeshFilter:
            mesh_guid = MeshFilter.get_child('m_Mesh').get('guid')
        elif PrefabInstance:
            mesh_guid = PrefabInstance.get_child('m_SourcePrefab').get('guid')
        else:
            msg = f'Unknown yaml data: {yaml_data}'
            __logger__.error(msg)
            raise ValueError(msg)
        return __asset_descriptor_manager__.get_asset_metadata(AssetTypes.MESH, guid=mesh_guid).get_asset_path()

    @staticmethod
    def process_model_infos(yaml_data):
        model_infos = []
        PrefabInstances = yaml_data.get_children('PrefabInstance')
        for PrefabInstance in PrefabInstances:
            model_info = copy.deepcopy(MODEL_INFO_TEMPLATE)
            model_guid = PrefabInstance.get_child('m_SourcePrefab').get('guid')
            asset_metadata = __asset_descriptor_manager__.get_asset_metadata(AssetTypes.MODEL, guid=model_guid)
            if asset_metadata is None:
                __logger__.debug(f'process_model_infos - invalid guid: {model_guid}')
                continue

            model_info['asset_path'] = asset_metadata.get_asset_path()
            transform_components = {'m_LocalPosition': 'position', 'm_LocalEulerAnglesHint': 'rotation', 'm_LocalScale': 'scale'}
            # unity y-up to blender z-up
            swizzle_map = {'x': 0, 'y': 2, 'z': 1}

            for modification_group in PrefabInstance.get_child('m_Modification').get_child('m_Modifications').get_children():
                target = modification_group.find_node('target').get_value()
                propertyPath = modification_group.find_node('propertyPath').get_value()
                value = modification_group.find_node('value').get_value()
                tokens = propertyPath.split('.')
                if len(tokens) == 2:
                    component_name = transform_components.get(tokens[0], '')
                    swizzle = swizzle_map.get(tokens[1], 0)
                    value = float(value)
                    if component_name:
                        if ('position' == component_name or 'rotation' == component_name) and value == 0.0:
                            continue
                        elif 'scale' == component_name and value == 1.0:
                            continue
                        model_info[component_name][swizzle] = value
            model_infos.append(model_info)
        return model_infos

    def process(self, asset_descriptor_data):
        __logger__.info(f'AssetDescriptor::process')
        root_path = __asset_descriptor_manager__.get_root_path()
        new_asset_metadata_list_by_types = {}
        for asset_type in AssetTypes.get_types():
            asset_metadata_list = []
            new_asset_metadata_list_by_types[asset_type] = asset_metadata_list

            # parsing: asset_path_infos
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
                                mtime=utilities.get_mtime(filepath)
                            )
                            asset_metadata_list.append(asset_metadata)
                            __asset_descriptor_manager__.register_asset_metadata(asset_metadata)
                            __logger__.info(f'register_asset_metadata: {asset_metadata.get_guid()}, {asset_metadata.get_asset_type()}, {asset_metadata.get_asset_path()}')
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
                        __logger__.debug(f'register_asset_metadata: {asset_metadata.get_guid()}, {asset_metadata.get_asset_type()}, {asset_metadata.get_asset_path()}')

        # process_asset_data
        for asset_metadata_list in new_asset_metadata_list_by_types.values():
            for asset_metadata in asset_metadata_list:
                self.process_asset_data(asset_descriptor_data, asset_metadata)

