"""Extract existing skinned weapon geometry as bone-local static props; source mesh untouched."""
import unreal
source=unreal.load_asset('/Game/ParagonKhaimera/Characters/Heroes/Khaimera/Meshes/Khaimera')
for side in ['l','r']:
    path='/Game/Enemies/Khaimera/Props/SM_Khaimera_Axe_'+side.upper()
    assert not unreal.EditorAssetLibrary.does_asset_exist(path)
    dm=unreal.DynamicMesh()
    unreal.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(source,dm,unreal.GeometryScriptCopyMeshFromAssetOptions(),unreal.GeometryScriptMeshReadLOD())
    info=unreal.GeometryScript_BoneWeights.get_bone_info(dm,'weapon_'+side)[2]
    bones={unreal.GeometryScript_BoneWeights.get_bone_info(dm,n)[2].index for n in ['weapon_'+side,'weapon_tail_'+side+'_01','weapon_tail_'+side+'_02']}
    remove=[]
    for i in range(dm.get_num_vertex_i_ds()):
        if dm.is_valid_vertex_id(i):
            _,bw,valid=dm.get_largest_vertex_bone_weight(i)
            if not valid or bw.bone_index not in bones:remove.append(i)
    _,selection=unreal.GeometryScript_MeshSelection.convert_index_array_to_mesh_selection(dm,remove,unreal.GeometryScriptMeshSelectionType.VERTICES)
    dm.delete_selected_triangles_from_mesh(selection)
    dm.remove_unused_vertices()
    unreal.GeometryScript_MeshTransforms.transform_mesh(dm,unreal.MathLibrary.invert_transform(info.world_transform))
    opts=unreal.GeometryScriptCreateNewStaticMeshAssetOptions(enable_collision=True)
    result,outcome=unreal.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,opts)
    assert result,(path,outcome)
    for i,mat in enumerate(source.get_editor_property('materials')):result.set_material(i,mat.material_interface)
    unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).add_simple_collisions(result,unreal.ScriptingCollisionShapeType.BOX)
    unreal.EditorAssetLibrary.save_asset(path)
    print('AXE',side,dm.get_vertex_count(),dm.get_triangle_count(),result.get_bounds())
