"""İmzasız iOS Shortcut plist'lerini üretir (`*.unsigned.plist`).

Kullanım: python shortcuts/build_shortcuts.py

iOS yalnızca imzalı dosya içe aktarır: Mac'te `shortcuts sign -m anyone -i X.unsigned.plist -o X.shortcut`
ya da Cherri'nin kullandığı HubSign servisi (https://hubsign.routinehub.services/sign) ile imzalanır.
Repodaki `.shortcut` dosyaları HubSign ile imzalanmıştır.

GitHub token dosyaya gömülmez; kısayol eklenirken iOS "import question" ile sorar.
"""
import plistlib
import uuid
from pathlib import Path

REPO = "tarjai/ig-to-mail"
DISPATCH_URL = f"https://api.github.com/repos/{REPO}/dispatches"
OUT_DIR = Path(__file__).parent

SHORTCUTS = [
    {"name": "IG Carousel to Mail", "event": "carousel", "color": 3980825855, "glyph": 61459},  # pink, photoStack
    {"name": "IG Video to Mail", "event": "video", "color": 3679049983, "glyph": 59733},  # purple, filmstrip
]

OBJ = "￼"  # Shortcuts metin içindeki değişken yer tutucusu


def text(s: str) -> dict:
    return {"Value": {"string": s}, "WFSerializationType": "WFTextTokenString"}


def text_with_var(prefix: str, ref: dict, suffix: str = "") -> dict:
    return {
        "Value": {
            "string": f"{prefix}{OBJ}{suffix}",
            "attachmentsByRange": {f"{{{len(prefix)}, 1}}": ref},
        },
        "WFSerializationType": "WFTextTokenString",
    }


def output(uid: str, name: str) -> dict:
    return {"Type": "ActionOutput", "OutputUUID": uid, "OutputName": name}


def attachment(ref: dict) -> dict:
    return {"Value": ref, "WFSerializationType": "WFTextTokenAttachment"}


def dict_items(items: list[dict]) -> dict:
    return {"Value": {"WFDictionaryFieldValueItems": items}, "WFSerializationType": "WFDictionaryFieldValue"}


def text_item(key: str, value: dict) -> dict:
    return {"WFItemType": 0, "WFKey": text(key), "WFValue": value}


def dict_item(key: str, items: list[dict]) -> dict:
    return {"WFItemType": 1, "WFKey": text(key), "WFValue": dict_items(items)}


def action(identifier: str, **params) -> dict:
    return {"WFWorkflowActionIdentifier": f"is.workflow.actions.{identifier}", "WFWorkflowActionParameters": params}


def build(event: str, color: int, glyph: int) -> dict:
    token_id, urls_id, item_id, req_id = (str(uuid.uuid4()).upper() for _ in range(4))
    actions = [
        # 0: token — kısayol eklenirken import question ile doldurulur
        action("gettext", UUID=token_id, WFTextActionText="GITHUB_TOKEN"),
        action("detect.link", UUID=urls_id, WFInput=attachment({"Type": "ExtensionInput"})),
        action("getitemfromlist", UUID=item_id, WFItemSpecifier="First Item",
               WFInput=attachment(output(urls_id, "URLs"))),
        action(
            "downloadurl",
            UUID=req_id,
            WFURL=DISPATCH_URL,
            WFHTTPMethod="POST",
            ShowHeaders=True,
            WFHTTPHeaders=dict_items([
                text_item("Authorization", text_with_var("Bearer ", output(token_id, "Text"))),
                text_item("Accept", text("application/vnd.github+json")),
            ]),
            WFHTTPBodyType="JSON",
            WFJSONValues=dict_items([
                text_item("event_type", text(event)),
                dict_item("client_payload", [
                    text_item("url", text_with_var("", output(item_id, "Item from List"))),
                ]),
            ]),
        ),
        # Başarılı istekte GitHub boş yanıt (204) döner; hata varsa mesajı bildirimde görünür
        action("notification",
               WFNotificationActionTitle="ig-to-mail",
               WFNotificationActionBody=text_with_var("İşleme alındı, mail 1-2 dk içinde gelir. ",
                                                      output(req_id, "Contents of URL")),
               WFNotificationActionSound=False),
    ]
    return {
        "WFWorkflowClientVersion": "2607.0.2",
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowIcon": {"WFWorkflowIconStartColor": color, "WFWorkflowIconGlyphNumber": glyph},
        "WFWorkflowTypes": ["ActionExtension"],
        "WFWorkflowInputContentItemClasses": ["WFURLContentItem", "WFStringContentItem"],
        "WFWorkflowOutputContentItemClasses": [],
        "WFWorkflowHasShortcutInputVariables": True,
        "WFWorkflowNoInputBehavior": {"Name": "WFWorkflowNoInputBehaviorGetClipboard", "Parameters": {}},
        "WFQuickActionSurfaces": [],
        "WFWorkflowImportQuestions": [{
            "ActionIndex": 0,
            "Category": "Parameter",
            "ParameterKey": "WFTextActionText",
            "Text": "GitHub fine-grained token (ig-to-mail, Contents: Read and write)",
            "DefaultValue": "",
        }],
        "WFWorkflowActions": actions,
    }


def main() -> None:
    for s in SHORTCUTS:
        out = OUT_DIR / f"{s['name']}.unsigned.plist"
        out.write_bytes(plistlib.dumps(build(s["event"], s["color"], s["glyph"]), fmt=plistlib.FMT_XML))
        print(out)


if __name__ == "__main__":
    main()
