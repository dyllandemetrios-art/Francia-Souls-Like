"""One-time authoring pass for WBP_MainMenu visual layout."""
import unreal

PATH = "/Game/UI/WBP_MainMenu"
PREFIX = "/Game/UI/WBP_MainMenu.WBP_MainMenu:WidgetTree."

def widget(name):
    value = unreal.find_object(None, PREFIX + name)
    assert value, name
    return value

backdrop = widget("Backdrop")
menu = widget("MenuBox")

# Full-screen dark veil and a centered 620 px menu column.
backdrop.slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(0, 0), maximum=unreal.Vector2D(1, 1)))
backdrop.slot.set_offsets(unreal.Margin(0, 0, 0, 0))
backdrop.slot.set_z_order(0)
backdrop.set_editor_property("brush_color", unreal.LinearColor(0.008, 0.006, 0.012, 0.965))

menu.slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(.5, .5), maximum=unreal.Vector2D(.5, .5)))
menu.slot.set_alignment(unreal.Vector2D(.5, .5))
menu.slot.set_position(unreal.Vector2D(0, 0))
menu.slot.set_size(unreal.Vector2D(620, 610))
menu.slot.set_z_order(1)

texts = {
    "Title": ("THE LAST KNIGHT", 52, unreal.LinearColor(.92, .73, .25, 1)),
    "Subtitle": ("CHOISISSEZ VOTRE SERMENT", 19, unreal.LinearColor(.72, .69, .64, 1)),
    "EasyText": ("ECUYER   —   ENNEMIS AFFAIBLIS", 21, unreal.LinearColor(.88, .88, .86, 1)),
    "NormalText": ("CHEVALIER   —   EXPERIENCE PREVUE", 21, unreal.LinearColor(1, .82, .34, 1)),
    "HardText": ("DERNIER SERMENT   —   ENNEMIS RENFORCES", 21, unreal.LinearColor(1, .47, .34, 1)),
    "Hint": ("Approchez le gardien. Survivez. Terrassez Khaimera.", 16, unreal.LinearColor(.55, .53, .51, 1)),
}
for name, (label, size, color) in texts.items():
    item = widget(name)
    item.set_text(label)
    item.set_editor_property("justification", unreal.TextJustify.CENTER)
    item.set_editor_property("color_and_opacity", unreal.SlateColor(specified_color=color))
    font = item.get_editor_property("font")
    font.size = size
    item.set_editor_property("font", font)

for name in ["EasyButton", "NormalButton", "HardButton"]:
    button = widget(name)
    button.set_editor_property("background_color", unreal.LinearColor(.42, .19, .055, 1))
    button.slot.set_padding(unreal.Margin(0, 12, 0, 0))
    button.slot.set_size(unreal.SlateChildSize(value=1.0, size_rule=unreal.SlateSizeRule.AUTOMATIC))
    label = widget(name.replace("Button", "Text"))
    label.slot.set_padding(unreal.Margin(22, 18, 22, 18))

widget("Title").slot.set_padding(unreal.Margin(0, 0, 0, 12))
widget("Subtitle").slot.set_padding(unreal.Margin(0, 0, 0, 38))
widget("Hint").slot.set_padding(unreal.Margin(0, 30, 0, 0))

# The editor preview does not prepass the new VerticalBox children reliably in
# this engine build. Explicit translations keep the authored layout stable both
# in preview and at runtime.
for name, y in [("Title", 0), ("Subtitle", 58), ("EasyButton", 120),
                ("NormalButton", 188), ("HardButton", 256), ("Hint", 338)]:
    item = widget(name)
    transform = item.get_editor_property("render_transform")
    transform.translation = unreal.Vector2D(0, y)
    item.set_editor_property("render_transform", transform)

assert unreal.BlueprintEditorLibrary.compile_blueprint(unreal.load_asset(PATH))
assert unreal.EditorAssetLibrary.save_asset(PATH)
print("MAIN_MENU_STYLED")
