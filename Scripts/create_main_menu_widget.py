"""Create the reusable main-menu widget structure. Logic is wired in a later stage."""
import unreal

PATH='/Game/UI/WBP_MainMenu'; W=unreal.WidgetService
assert not unreal.EditorAssetLibrary.does_asset_exist(PATH)
factory=unreal.WidgetBlueprintFactory()
asset=unreal.AssetToolsHelpers.get_asset_tools().create_asset('WBP_MainMenu','/Game/UI',None,factory)
assert asset
for kind,name,parent in [
 ('CanvasPanel','Root',''),('Border','Backdrop','Root'),('VerticalBox','MenuBox','Root'),
 ('TextBlock','Title','MenuBox'),('TextBlock','Subtitle','MenuBox'),
 ('Button','EasyButton','MenuBox'),('TextBlock','EasyText','EasyButton'),
 ('Button','NormalButton','MenuBox'),('TextBlock','NormalText','NormalButton'),
 ('Button','HardButton','MenuBox'),('TextBlock','HardText','HardButton'),
 ('TextBlock','Hint','MenuBox')]:
    r=W.add_component(PATH,kind,name,parent,True,-1);print(kind,name,r.success,r.error_message);assert r.success
assert unreal.BlueprintEditorLibrary.compile_blueprint(unreal.load_asset(PATH));assert unreal.EditorAssetLibrary.save_asset(PATH)
print('MENU_WIDGET_STRUCTURE_CREATED')
